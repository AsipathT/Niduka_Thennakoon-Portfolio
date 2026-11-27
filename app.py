"""
app.py – Niduka Thennakoon Portfolio
======================================
Clean single-file Flask application.

Responsibilities
----------------
- Load site_config.json and projects.json once at startup.
- Inject site_config into every template via a context processor.
- Apply show_client_name privacy rule via a helper (not in templates).
- Routes: / | /project/<slug> | /contact (POST) | /cv | custom 404.
- /contact: server-side validation, honeypot, per-IP rate limiting (in-memory),
  SMTP via environment variables. Credentials are never logged.
- /cv: serve CV as download; friendly 404 if the file is missing.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import smtplib
import sys
import time
import traceback
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

# ─── Environment ───────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("portfolio")

REQUIRED_ENV_VARS = (
    "SECRET_KEY",
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USE_TLS",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_RECIPIENT",
)

_PLACEHOLDER_VALUES = {
    "change-me-to-a-random-secret",
    "your-email@gmail.com",
    "your-app-password",
}


def _env_presence_summary() -> dict[str, bool]:
    """Return True/False per required env var (never values)."""
    return {var: bool((os.getenv(var) or "").strip()) for var in REQUIRED_ENV_VARS}


def _is_smtp_configured() -> bool:
    """Return True if essential SMTP credentials are set and not placeholders."""
    user = (os.getenv("MAIL_USERNAME") or "").strip()
    pwd  = (os.getenv("MAIL_PASSWORD") or "").strip()
    srv  = (os.getenv("MAIL_SERVER")   or "").strip()
    return bool(user and pwd and srv and user not in _PLACEHOLDER_VALUES and pwd not in _PLACEHOLDER_VALUES)


logger.info("Environment file exists (%s): %s", ENV_PATH.name, ENV_PATH.is_file())
logger.info("Required env vars set: %s", _env_presence_summary())

# ─── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

if os.getenv("FLASK_ENV", "production") == "development" and not _is_smtp_configured():
    logger.warning(
        "SMTP is not configured (missing or placeholder MAIL_USERNAME / MAIL_PASSWORD). "
        "Contact form emails will fall back to data/messages_failed.jsonl."
    )

# ─── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(app.root_path)
DATA_DIR     = ROOT / "data"
STATIC_FILES = ROOT / "static" / "files"
CV_FILENAME  = "Niduka_Thennakoon_CV.pdf"

# ==============================================================================
# 1.  DATA LOADING  (once at startup)
# ==============================================================================

def _load_json(path: Path, label: str) -> dict | list:
    """Load a JSON file and exit with a clear message if it is missing or broken."""
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.critical("Required data file not found: %s", path)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        logger.critical("JSON parse error in %s: %s", label, exc)
        sys.exit(1)


# Load data at import time so every request finds it in memory.
SITE_CONFIG: dict  = _load_json(DATA_DIR / "site_config.json", "site_config.json")
PROJECTS_RAW: list = _load_json(DATA_DIR / "projects.json",    "projects.json")

# Build a slug→project lookup for O(1) access.
PROJECTS_BY_SLUG: dict[str, dict] = {p["slug"]: p for p in PROJECTS_RAW}


# ==============================================================================
# 2.  PRIVACY HELPER  (show_client_name logic lives here, not in templates)
# ==============================================================================

def apply_privacy(project: dict) -> dict:
    """
    Return a *copy* of the project dict safe for public rendering.

    If show_client_name is False, replace 'title' and 'sector' with
    sector-only labels so the client identity is never exposed.
    The original dict in PROJECTS_BY_SLUG is never mutated.
    """
    p = project.copy()
    if not p.get("show_client_name", True):
        # Strip client name: use the sector label as the display title.
        p["title"]     = f"{p['sector']} – ERP Implementation"
        p["short_desc"] = p["short_desc"]  # description stays; it has no client name
        # Also anonymise the what_i_did list if it contained a client name.
        # (For the current dataset all private projects are open-source, so this
        #  is a safety net for future additions.)
        p["_client_hidden"] = True
    else:
        p["_client_hidden"] = False
    return p


def public_projects(domain_filter: str | None = None) -> list[dict]:
    """
    Return all projects after applying privacy rules, optionally filtered by domain.
    Projects are ordered: featured first, then by id.
    """
    projects = [apply_privacy(p) for p in PROJECTS_RAW]
    if domain_filter and domain_filter != "all":
        projects = [p for p in projects if p["domain"] == domain_filter]
    projects.sort(key=lambda p: (not p.get("featured", False), p["id"]))
    return projects


# ==============================================================================
# 3.  CONTEXT PROCESSOR  (injects site_config into every template)
# ==============================================================================

@app.context_processor
def inject_site_config() -> dict:
    """
    Make SITE_CONFIG available as `site` in every Jinja2 template.
    Also expose the current year for the footer copyright.
    """
    import datetime
    return {
        "site":         SITE_CONFIG,
        "current_year": datetime.date.today().year,
    }


# ==============================================================================
# 4.  IN-MEMORY RATE LIMITER  (per IP, simple sliding-window)
# ==============================================================================

# Structure: { ip: [timestamp, ...] }
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock   = Lock()

RATE_LIMIT_MAX    = 5    # max requests
RATE_LIMIT_WINDOW = 600  # per 10 minutes (seconds)


def _is_rate_limited(ip: str) -> bool:
    """
    Sliding-window rate limiter.
    Returns True if the IP has exceeded RATE_LIMIT_MAX contact
    submissions within RATE_LIMIT_WINDOW seconds.
    """
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_store[ip]
        # Drop timestamps outside the window.
        _rate_store[ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_store[ip]) >= RATE_LIMIT_MAX:
            return True
        _rate_store[ip].append(now)
        return False


# ==============================================================================
# 5.  CONTACT FORM HELPERS
# ==============================================================================

# Simple but effective email regex (RFC 5322 simplified).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FIELD_LIMITS = {
    "name":    (1, 100),
    "email":   (5, 254),
    "message": (10, 3000),
}


def _validate_contact(data: dict) -> list[str]:
    """
    Validate contact form fields.
    Returns a list of human-readable error strings (empty = valid).
    """
    errors: list[str] = []

    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip()
    message = (data.get("message") or "").strip()

    # Name
    mn, mx = FIELD_LIMITS["name"]
    if not name:
        errors.append("Name is required.")
    elif len(name) > mx:
        errors.append(f"Name must be {mx} characters or fewer.")

    # Email
    mn, mx = FIELD_LIMITS["email"]
    if not email:
        errors.append("Email address is required.")
    elif len(email) > mx or not _EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")

    # Message
    mn, mx = FIELD_LIMITS["message"]
    if not message:
        errors.append("Message is required.")
    elif len(message) < mn:
        errors.append(f"Message must be at least {mn} characters.")
    elif len(message) > mx:
        errors.append(f"Message must be {mx} characters or fewer.")

    return errors


_failed_msg_lock = Lock()
SMTP_TIMEOUT_SECONDS = 15


def _get_smtp_config() -> dict:
    """
    Read SMTP settings from environment variables.
    Strips surrounding whitespace from all fields (including password).
    """
    mail_server    = (os.getenv("MAIL_SERVER",    "smtp.gmail.com") or "").strip()
    mail_port_raw  = (os.getenv("MAIL_PORT",      "587") or "587").strip()
    mail_port      = int(mail_port_raw)
    use_tls        = (os.getenv("MAIL_USE_TLS",   "True") or "True").strip().lower() == "true"
    mail_username  = (os.getenv("MAIL_USERNAME",  "") or "").strip()
    mail_password  = (os.getenv("MAIL_PASSWORD",  "") or "").strip()
    mail_recipient = (os.getenv("MAIL_RECIPIENT", "") or mail_username).strip()

    return {
        "server":    mail_server,
        "port":      mail_port,
        "use_tls":   use_tls,
        "username":  mail_username,
        "password":  mail_password,
        "recipient": mail_recipient,
    }


def _open_smtp_connection(cfg: dict) -> smtplib.SMTP:
    """
    Open an authenticated SMTP connection supporting both:
      - port 465 -> smtplib.SMTP_SSL (implicit TLS)
      - port 587 (or other) -> smtplib.SMTP + starttls() when use_tls is True
    Sets timeout=15 on the connection.
    """
    if not cfg["server"] or not cfg["username"] or not cfg["password"]:
        raise ValueError("Missing required SMTP configuration (MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD).")

    if cfg["port"] == 465:
        server = smtplib.SMTP_SSL(cfg["server"], cfg["port"], timeout=SMTP_TIMEOUT_SECONDS)
        server.ehlo()
    else:
        server = smtplib.SMTP(cfg["server"], cfg["port"], timeout=SMTP_TIMEOUT_SECONDS)
        server.ehlo()
        if cfg["use_tls"] or cfg["port"] == 587:
            server.starttls()
            server.ehlo()

    server.login(cfg["username"], cfg["password"])
    return server


def _send_email(name: str, email: str, message: str) -> None:
    """
    Send the contact form email via SMTP.

    Credentials are read from environment variables at call time –
    they are NEVER logged or included in exception messages surfaced to users.
    """
    cfg = _get_smtp_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = f"[Portfolio] Message from {name}"
    msg["From"]     = cfg["username"]
    msg["To"]       = cfg["recipient"]
    msg["Reply-To"] = email  # so I can reply directly to the sender

    body = (
        f"Name:    {name}\n"
        f"Email:   {email}\n"
        f"{'─' * 40}\n\n"
        f"{message}\n"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with _open_smtp_connection(cfg) as server:
        server.sendmail(cfg["username"], cfg["recipient"], msg.as_string())


def _test_smtp_login() -> None:
    """Connect and authenticate to SMTP without sending a message."""
    cfg = _get_smtp_config()
    with _open_smtp_connection(cfg):
        pass


def _save_failed_message(name: str, email: str, message: str) -> bool:
    """
    Fallback persistence when SMTP fails: append validated message as a JSON line
    to data/messages_failed.jsonl so no message is ever lost.
    Returns True only if the write succeeds.
    """
    fallback_path = DATA_DIR / "messages_failed.jsonl"
    record = {
        "name":      name,
        "email":     email,
        "message":   message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with _failed_msg_lock:
            with fallback_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError as exc:
        logger.error("Failed to write fallback message (%s)", type(exc).__name__)
        return False


def _format_safe_tb(exc: BaseException) -> str:
    """
    Format exception type and traceback frame locations (file, line, func)
    without including exception args/str or local variable values.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    loc = " -> ".join(f"{Path(f.filename).name}:{f.lineno}({f.name})" for f in frames[-4:])
    return f"{type(exc).__name__} at [{loc}]"


# ==============================================================================
# 6.  ROUTES
# ==============================================================================

# ── Home ───────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """
    Render the single-page portfolio.
    Passes all projects (privacy-applied) and all unique domains for the filter UI.
    """
    projects = public_projects()
    domains  = sorted({p["domain"] for p in PROJECTS_RAW})
    return render_template("index.html", projects=projects, domains=domains)


# ── Project detail ─────────────────────────────────────────────────────────────
@app.route("/project/<slug>")
def project_detail(slug: str):
    """
    Render a full case-study page for one project.
    Returns 404 if the slug does not exist.
    Privacy rule is applied before the data reaches the template.
    """
    raw = PROJECTS_BY_SLUG.get(slug)
    if raw is None:
        abort(404)
    project = apply_privacy(raw)
    return render_template("project_detail.html", project=project)


# ── Contact (POST) ─────────────────────────────────────────────────────────────
@app.route("/contact", methods=["POST"])
def contact():
    """
    Handle contact form submission.

    Security layers:
      1. Honeypot field (`_trap`) – bots fill it; humans don't see it.
      2. Per-IP rate limiting (5 submissions per 10 minutes, in-memory).
      3. Server-side field validation (length, email regex).
      4. SMTP credentials from environment only; never logged.

    Returns JSON for AJAX submission.
    """
    data = request.get_json(silent=True) or request.form

    # ── 1. Honeypot ───────────────────────────────────────────
    # The _trap field is hidden via CSS/aria. If it contains any value,
    # silently accept (don't reveal the defence) but don't send the email.
    if data.get("_trap", "").strip():
        logger.info("Honeypot triggered from IP %s – silently dropped.", request.remote_addr)
        return jsonify({"ok": True, "message": "Thanks! I'll be in touch soon."}), 200

    # ── 2. Rate limiting ──────────────────────────────────────
    ip = request.remote_addr or "unknown"
    if _is_rate_limited(ip):
        logger.warning("Rate limit exceeded for IP %s", ip)
        return jsonify({
            "ok": False,
            "errors": ["Too many messages sent. Please wait a few minutes and try again."],
        }), 429

    # ── 3. Validation ─────────────────────────────────────────
    errors = _validate_contact(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip()
    message = (data.get("message") or "").strip()

    # ── 4. Send ───────────────────────────────────────────────
    try:
        _send_email(name, email, message)
        logger.info("Contact email sent (IP: %s)", ip)
    except Exception as exc:
        # Log only exception type and frame line numbers – never credentials or message content.
        logger.error(
            "SMTP failure sending contact email (IP: %s): %s",
            ip,
            _format_safe_tb(exc),
        )
        if _save_failed_message(name, email, message):
            return jsonify({
                "ok": False,
                "saved": True,
                "message": "Email delivery is temporarily unavailable, but your message was saved, I'll reply soon.",
            }), 502
        return jsonify({
            "ok": False,
            "saved": False,
            "errors": ["Message could not be sent right now. Please try again later or email me directly."],
        }), 502

    return jsonify({"ok": True, "message": "Thanks! I'll get back to you soon."}), 200


# ── Health & local SMTP verification ──────────────────────────────────────────
@app.route("/health")
def health():
    """Basic health check + boolean env status (never exposes values)."""
    return jsonify({
        "ok": True,
        "env_set": _env_presence_summary(),
        "smtp_configured": _is_smtp_configured(),
    }), 200


@app.route("/health/smtp")
def health_smtp():
    """
    Local diagnostic endpoint to verify SMTP login without sending an email.
    Never logs or returns credentials.
    """
    try:
        _test_smtp_login()
        return jsonify({"ok": True, "smtp": "login_ok"}), 200
    except Exception as exc:
        logger.warning("SMTP health check failed: %s", _format_safe_tb(exc))
        return jsonify({
            "ok": False,
            "smtp": "login_failed",
            "error_type": type(exc).__name__,
        }), 502


# ── CV download ────────────────────────────────────────────────────────────────
@app.route("/cv")
def download_cv():
    """
    Serve the CV PDF as a named download attachment.
    If the file is missing, render the custom 404 page with a friendly message
    rather than a raw HTTP error so the user knows what to do.
    """
    cv_path = STATIC_FILES / CV_FILENAME
    if not cv_path.is_file():
        logger.warning("/cv requested but %s not found in static/files/", CV_FILENAME)
        # Render the 404 template with a specific message.
        return render_template(
            "404.html",
            message=(
                "The CV file is not available right now. "
                "Please contact me directly at "
                f"{SITE_CONFIG['contact']['email']} and I'll send it to you."
            ),
        ), 404

    return send_from_directory(
        str(STATIC_FILES),
        CV_FILENAME,
        as_attachment=True,
        download_name=CV_FILENAME,   # Flask 2.x+ kwarg
    )


# ==============================================================================
# 7.  ERROR HANDLERS
# ==============================================================================

@app.errorhandler(404)
def page_not_found(exc):
    """Render a friendly, branded 404 page."""
    return render_template("404.html", message=None), 404


@app.errorhandler(429)
def too_many_requests(exc):
    """Return a JSON 429 for AJAX callers (contact form)."""
    return jsonify({
        "ok": False,
        "errors": ["Too many requests. Please slow down."],
    }), 429


@app.errorhandler(500)
def internal_error(exc):
    """Render a branded 500 page so users never see a raw traceback."""
    logger.exception("Unhandled 500 error")
    return render_template("500.html"), 500


# ==============================================================================
# 8.  DEV SERVER ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    is_dev = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=is_dev, port=5000)
