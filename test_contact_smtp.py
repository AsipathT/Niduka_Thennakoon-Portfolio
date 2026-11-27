"""
test_contact_smtp.py – Verification tests for /contact, SMTP modes, fallback, and /health
"""
import json
import os
import smtplib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["FLASK_DEBUG"] = "1"
os.environ.setdefault("SECRET_KEY", "test-secret")

import app as portfolio_app

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition):
    status = PASS if condition else FAIL
    results.append((status, label))
    print(f"  {status}  {label}")

def reset_rate_limit(ip="127.0.0.1"):
    with portfolio_app._rate_lock:
        portfolio_app._rate_store[ip] = []

VALID_PAYLOAD = {
    "name": "Test User",
    "email": "sender@example.com",
    "message": "Hello Niduka, this is a valid test message.",
}

fallback_file = portfolio_app.DATA_DIR / "messages_failed.jsonl"
had_fallback_before = fallback_file.exists()
before_content = fallback_file.read_text(encoding="utf-8") if had_fallback_before else None

try:
    print("\n[1] Success (Port 587 + STARTTLS + password whitespace stripped)")
    reset_rate_limit()
    mock_smtp_inst = MagicMock()
    mock_smtp_inst.__enter__ = MagicMock(return_value=mock_smtp_inst)
    mock_smtp_inst.__exit__ = MagicMock(return_value=False)

    env_587 = {
        "MAIL_SERVER": "smtp.gmail.com",
        "MAIL_PORT": "587",
        "MAIL_USE_TLS": "True",
        "MAIL_USERNAME": "user@gmail.com",
        "MAIL_PASSWORD": "  secret-pass  ",
        "MAIL_RECIPIENT": "user@gmail.com",
    }
    with patch.dict(os.environ, env_587, clear=False), \
         patch("smtplib.SMTP", return_value=mock_smtp_inst) as mock_smtp_cls:
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
        check("Status 200 on port 587 success", r.status_code == 200 and j.get("ok") is True)
        check("smtplib.SMTP called with timeout=15",
              mock_smtp_cls.call_args.kwargs.get("timeout") == 15)
        check("starttls() called on port 587", mock_smtp_inst.starttls.called)
        check("Password stripped before login()",
              mock_smtp_inst.login.call_args[0][1] == "secret-pass")
        check("sendmail() called", mock_smtp_inst.sendmail.called)

    print("\n[2] Success (Port 465 + SMTP_SSL)")
    reset_rate_limit()
    mock_ssl_inst = MagicMock()
    mock_ssl_inst.__enter__ = MagicMock(return_value=mock_ssl_inst)
    mock_ssl_inst.__exit__ = MagicMock(return_value=False)

    env_465 = dict(env_587, MAIL_PORT="465", MAIL_USE_TLS="False")
    with patch.dict(os.environ, env_465, clear=False), \
         patch("smtplib.SMTP_SSL", return_value=mock_ssl_inst) as mock_ssl_cls:
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
        check("Status 200 on port 465 success", r.status_code == 200 and j.get("ok") is True)
        check("smtplib.SMTP_SSL called with timeout=15",
              mock_ssl_cls.call_args.kwargs.get("timeout") == 15)
        check("login() called on SMTP_SSL", mock_ssl_inst.login.called)

    print("\n[3] Bad Auth (SMTPAuthenticationError -> 502 + fallback saved)")
    reset_rate_limit()
    mock_bad_auth = MagicMock()
    mock_bad_auth.__enter__ = MagicMock(return_value=mock_bad_auth)
    mock_bad_auth.__exit__ = MagicMock(return_value=False)
    mock_bad_auth.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")

    with patch.dict(os.environ, env_587, clear=False), \
         patch("smtplib.SMTP", return_value=mock_bad_auth):
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
        check("Bad auth returns 502", r.status_code == 502)
        check("Bad auth sets saved=True", j.get("saved") is True)
        check("Bad auth tells user saved/reply soon", "saved, I'll reply soon" in j.get("message", ""))
        check("Fallback file exists and contains record",
              fallback_file.exists() and "sender@example.com" in fallback_file.read_text(encoding="utf-8"))

    print("\n[4] Wrong Port / Connection Error -> 502 + fallback saved")
    reset_rate_limit()
    env_wrong_port = dict(env_587, MAIL_PORT="9999", MAIL_USE_TLS="False")
    with patch.dict(os.environ, env_wrong_port, clear=False), \
         patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
        check("Wrong port returns 502", r.status_code == 502)
        check("Wrong port sets saved=True", j.get("saved") is True)
        check("Wrong port tells user saved/reply soon", "saved, I'll reply soon" in j.get("message", ""))

    print("\n[5] Missing Env Vars -> 502 + fallback saved, /health/smtp -> 502")
    reset_rate_limit()
    env_missing = {
        "MAIL_SERVER": "smtp.gmail.com",
        "MAIL_PORT": "587",
        "MAIL_USE_TLS": "True",
        "MAIL_USERNAME": "",
        "MAIL_PASSWORD": "",
        "MAIL_RECIPIENT": "",
    }
    with patch.dict(os.environ, env_missing, clear=False):
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
            rh = c.get("/health")
            jh = rh.get_json()
            rs = c.get("/health/smtp")
            js = rs.get_json()
        check("Missing env vars /contact returns 502", r.status_code == 502)
        check("Missing env vars /contact saved=True", j.get("saved") is True)
        check("/health returns 200 with env_set booleans",
              rh.status_code == 200 and jh["env_set"]["MAIL_USERNAME"] is False)
        check("/health/smtp returns 502 on missing env vars",
              rs.status_code == 502 and js.get("error_type") == "ValueError")

    print("\n[6] Fallback write failure -> 502 without claiming saved")
    reset_rate_limit()
    with patch.dict(os.environ, env_missing, clear=False), \
         patch.object(portfolio_app, "_save_failed_message", return_value=False):
        with portfolio_app.app.test_client() as c:
            r = c.post("/contact", json=VALID_PAYLOAD)
            j = r.get_json()
        check("Fallback failure returns 502", r.status_code == 502)
        check("Fallback failure saved=False", j.get("saved") is False)
        check("Fallback failure does not claim saved", "saved" not in j.get("message", ""))

    print("\n[7] Validation (400), Honeypot (200), Rate Limit (429), /health/smtp OK (200)")
    reset_rate_limit()
    with patch.dict(os.environ, env_587, clear=False), \
         patch("smtplib.SMTP", return_value=mock_smtp_inst):
        with portfolio_app.app.test_client() as c:
            r400 = c.post("/contact", json={"name": "", "email": "bad", "message": "hi"})
            rhoney = c.post("/contact", json=dict(VALID_PAYLOAD, _trap="bot"))
            rs_ok = c.get("/health/smtp")
        check("Validation error returns 400", r400.status_code == 400)
        check("Honeypot returns silent 200", rhoney.status_code == 200)
        check("/health/smtp returns 200 when login succeeds", rs_ok.status_code == 200)

        with portfolio_app._rate_lock:
            portfolio_app._rate_store["127.0.0.1"] = [portfolio_app.time.monotonic()] * portfolio_app.RATE_LIMIT_MAX
        with portfolio_app.app.test_client() as c:
            r429 = c.post("/contact", json=VALID_PAYLOAD)
        check("Rate limit returns 429", r429.status_code == 429)

    print("\n[8] Hardening: /health debug gate, CR/LF rejection, TODO helper, ProxyFix")
    orig_debug = portfolio_app.app.debug
    try:
        # 8a. /health and /health/smtp return 404 when app.debug is False
        portfolio_app.app.debug = False
        with portfolio_app.app.test_client() as c:
            check("/health returns 404 when debug=False", c.get("/health").status_code == 404)
            check("/health/smtp returns 404 when debug=False", c.get("/health/smtp").status_code == 404)

        # 8b. TODO-hiding helper: hidden in production, highlighted in debug
        check("is_todo detects TODO prefix", portfolio_app.is_todo("TODO: add GPA") is True)
        check("is_todo ignores normal text", portfolio_app.is_todo("Core 48") is False)
        check("render_todo hides TODO when debug=False", portfolio_app.render_todo("TODO: add GPA") == "")
        check("render_todo keeps normal text when debug=False", portfolio_app.render_todo("Core 48") == "Core 48")

        portfolio_app.app.debug = True
        highlighted = str(portfolio_app.render_todo("TODO: add GPA"))
        check("render_todo highlights TODO when debug=True",
              "todo-highlight" in highlighted and "TODO: add GPA" in highlighted)
    finally:
        portfolio_app.app.debug = orig_debug

    # 8c. CR/LF injection rejected in name and email (400)
    reset_rate_limit()
    with portfolio_app.app.test_client() as c:
        r_crlf_name = c.post("/contact", json={
            "name": "Niduka\r\nBcc: evil@example.com",
            "email": "sender@example.com",
            "message": "Valid message length here.",
        })
        r_crlf_email = c.post("/contact", json={
            "name": "Niduka",
            "email": "sender@example.com\nBcc: evil@example.com",
            "message": "Valid message length here.",
        })
    check("CR/LF in name returns 400", r_crlf_name.status_code == 400)
    check("CR/LF in email returns 400", r_crlf_email.status_code == 400)

    # 8d. ProxyFix enabled when TRUST_PROXY=true
    from werkzeug.middleware.proxy_fix import ProxyFix
    check("ProxyFix disabled by default (TRUST_PROXY!=true)",
          not isinstance(portfolio_app.app.wsgi_app, ProxyFix))

    # Test ProxyFix behavior via reload with TRUST_PROXY=true
    import importlib
    with patch.dict(os.environ, {"TRUST_PROXY": "true"}, clear=False):
        importlib.reload(portfolio_app)
        check("ProxyFix enabled when TRUST_PROXY=true",
              isinstance(portfolio_app.app.wsgi_app, ProxyFix))
        with portfolio_app.app.test_client() as c:
            with portfolio_app._rate_lock:
                portfolio_app._rate_store["203.0.113.55"] = [portfolio_app.time.monotonic()] * portfolio_app.RATE_LIMIT_MAX
            r_proxy = c.post("/contact", json=VALID_PAYLOAD, headers={"X-Forwarded-For": "203.0.113.55"})
            check("ProxyFix uses X-Forwarded-For IP for rate limiting", r_proxy.status_code == 429)
    # Reload back to default
    importlib.reload(portfolio_app)

finally:
    # Restore fallback file state
    if had_fallback_before and before_content is not None:
        fallback_file.write_text(before_content, encoding="utf-8")
    elif fallback_file.exists():
        fallback_file.unlink()

print("\n" + "=" * 60)
passed = sum(1 for s, _ in results if s == PASS)
failed = sum(1 for s, _ in results if s == FAIL)
print(f"  Results: {passed} passed, {failed} failed out of {len(results)} checks.")
print("=" * 60)
if failed:
    sys.exit(1)
