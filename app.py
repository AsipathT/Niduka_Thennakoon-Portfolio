"""
app.py – Niduka Thennakoon Portfolio
Entry point for the Flask application.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# ─── Load environment variables ───────────────────────────────────────────────
load_dotenv()

# ─── App factory ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")


# ─── Helper: load project data ────────────────────────────────────────────────
def load_projects():
    """Read projects from data/projects.json and return as a list of dicts."""
    data_path = os.path.join(app.root_path, "data", "projects.json")
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the single-page portfolio."""
    projects = load_projects()
    return render_template("index.html", projects=projects)


@app.route("/contact", methods=["POST"])
def contact():
    """
    Handle contact form submission.
    Validates inputs and sends an email via SMTP using env variables.
    Returns JSON so the frontend can show success/error without a page reload.
    """
    data = request.get_json(silent=True) or request.form

    name    = (data.get("name", "") or "").strip()
    email   = (data.get("email", "") or "").strip()
    message = (data.get("message", "") or "").strip()

    # ── Basic validation ──────────────────────────────────
    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or "@" not in email:
        errors.append("A valid email address is required.")
    if not message:
        errors.append("Message cannot be empty.")
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    # ── Send email ────────────────────────────────────────
    try:
        mail_server    = os.getenv("MAIL_SERVER", "smtp.gmail.com")
        mail_port      = int(os.getenv("MAIL_PORT", 587))
        mail_use_tls   = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
        mail_username  = os.getenv("MAIL_USERNAME", "")
        mail_password  = os.getenv("MAIL_PASSWORD", "")
        mail_recipient = os.getenv("MAIL_RECIPIENT", mail_username)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Portfolio] New message from {name}"
        msg["From"]    = mail_username
        msg["To"]      = mail_recipient

        body = (
            f"Name:    {name}\n"
            f"Email:   {email}\n\n"
            f"Message:\n{message}"
        )
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            if mail_username and mail_password:
                server.login(mail_username, mail_password)
            server.sendmail(mail_username, mail_recipient, msg.as_string())

    except Exception as exc:  # noqa: BLE001
        app.logger.error("Failed to send contact email: %s", exc)
        return jsonify({"ok": False, "errors": ["Failed to send message. Please try again later."]}), 500

    return jsonify({"ok": True, "message": "Thanks! I'll be in touch soon."})


# ─── Dev server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") == "development", port=5000)
