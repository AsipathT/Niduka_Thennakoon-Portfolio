"""
test_routes.py – Part 2A route and logic tests
================================================
Tests every requirement from Part 2A without a live server.
Run with: venv\\Scripts\\python.exe test_routes.py
"""

import json
import os
import sys
import time

# Ensure the app can load – set a test secret key
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("FLASK_ENV", "development")

from app import app, apply_privacy, public_projects, _is_rate_limited, _validate_contact, SITE_CONFIG, PROJECTS_RAW, PROJECTS_BY_SLUG

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition):
    status = PASS if condition else FAIL
    results.append((status, label))
    print(f"  {status}  {label}")

print("\n" + "=" * 60)
print("  Part 2A Route & Logic Tests")
print("=" * 60)

# ── Data loading ──────────────────────────────────────────────
print("\n[1] Data loading")
check("SITE_CONFIG loaded as dict",         isinstance(SITE_CONFIG, dict))
check("SITE_CONFIG has 'meta' key",         "meta" in SITE_CONFIG)
check("SITE_CONFIG has 'contact' key",      "contact" in SITE_CONFIG)
check("SITE_CONFIG contact has no phone",   "phone" not in SITE_CONFIG.get("contact", {}))
check("PROJECTS_RAW loaded as list",        isinstance(PROJECTS_RAW, list))
check("PROJECTS_RAW has 4 projects",        len(PROJECTS_RAW) == 4)
check("PROJECTS_BY_SLUG has all slugs",     len(PROJECTS_BY_SLUG) == 4)
check("All projects have required keys",    all(
    all(k in p for k in ["id","slug","title","domain","show_client_name","what_i_did"])
    for p in PROJECTS_RAW
))

# ── Privacy helper ────────────────────────────────────────────
print("\n[2] Privacy helper (apply_privacy)")
private_proj = {"id":99,"slug":"test","title":"ACME Corp – HR","short_desc":"desc",
                "sector":"Test Sector","domain":"hr","show_client_name":False,
                "what_i_did":[],"outcome":"","image":"","github":"","live":"",
                "my_role":"Eng","modules":[],"tech":[],"featured":False}
public_proj  = dict(private_proj, show_client_name=True, title="Real Client – HR")

priv_result  = apply_privacy(private_proj)
pub_result   = apply_privacy(public_proj)

check("Private: title does NOT contain client name",
      "ACME Corp" not in priv_result["title"])
check("Private: _client_hidden is True",    priv_result["_client_hidden"] is True)
check("Private: sector label used in title", "Test Sector" in priv_result["title"])
check("Public:  title unchanged",            pub_result["title"] == "Real Client – HR")
check("Public:  _client_hidden is False",    pub_result["_client_hidden"] is False)
check("Original dict NOT mutated",           private_proj["title"] == "ACME Corp – HR")

# ── public_projects ordering ──────────────────────────────────
print("\n[3] public_projects helper")
all_pub = public_projects()
check("Returns list",                        isinstance(all_pub, list))
check("Featured projects come first",
      all(p.get("featured", False) for p in all_pub[:3]))
check("Domain filter 'hr' returns 1 result", len(public_projects("hr")) == 1)
check("Domain filter 'education' returns 1", len(public_projects("education")) == 1)
check("Domain filter 'all' returns all 4",   len(public_projects("all")) == 4)

# ── Validation ────────────────────────────────────────────────
print("\n[4] Contact form validation")
check("Valid data: no errors",
      _validate_contact({"name":"Niduka","email":"a@b.com","message":"Hello there, this is a test!"}) == [])
check("Empty name: error raised",
      any("Name" in e for e in _validate_contact({"name":"","email":"a@b.com","message":"Hi there, test message"})))
check("Bad email (no @): error raised",
      any("email" in e.lower() for e in _validate_contact({"name":"N","email":"notanemail","message":"Hi there, test message"})))
check("Short message (<10 chars): error raised",
      any("Message" in e for e in _validate_contact({"name":"N","email":"a@b.com","message":"Hi"})))
check("Too-long name (>100 chars): error raised",
      any("Name" in e for e in _validate_contact({"name":"A"*101,"email":"a@b.com","message":"Test message here"})))
check("Too-long message (>3000 chars): error raised",
      any("Message" in e for e in _validate_contact({"name":"N","email":"a@b.com","message":"A"*3001})))

# ── Rate limiter ──────────────────────────────────────────────
print("\n[5] Rate limiter")
test_ip = "192.0.2.TEST"
# Reset any existing state for this IP
from app import _rate_store, _rate_lock
with _rate_lock:
    _rate_store[test_ip] = []
not_limited = not _is_rate_limited(test_ip)
# Fill up to limit
from app import RATE_LIMIT_MAX
with _rate_lock:
    _rate_store[test_ip] = [time.monotonic()] * (RATE_LIMIT_MAX - 1)
just_under = not _is_rate_limited(test_ip)  # this call adds the final one
now_limited = _is_rate_limited(test_ip)

check("First request not rate-limited",     not_limited)
check("At limit: last slot accepted",        just_under)
check("Over limit: request blocked",         now_limited)

# ── Flask routes (test client) ────────────────────────────────
print("\n[6] Flask routes")
with app.test_client() as c:

    # GET /
    r = c.get("/")
    check("GET / returns 200",               r.status_code == 200)
    body = r.data.decode("utf-8")
    check("/ contains site config (name)",   "Niduka" in body)

    # GET /project/<valid slug>
    r2 = c.get("/project/saegis-university-erp")
    check("GET /project/saegis-university-erp returns 200", r2.status_code == 200)
    body2 = r2.data.decode("utf-8")
    check("/project page contains sector",   "Higher Education" in body2)
    check("/project page lists modules",     "Student Management" in body2)

    # GET /project/<invalid slug>
    r3 = c.get("/project/does-not-exist")
    check("GET /project/nonexistent returns 404", r3.status_code == 404)

    # GET /cv – PDF missing
    r4 = c.get("/cv")
    # In test env the PDF likely doesn't exist → expect 404 friendly page
    if r4.status_code == 404:
        check("/cv without PDF returns 404 (expected)",  True)
        check("/cv 404 body is HTML (not raw error)",
              b"<" in r4.data)
    else:
        # PDF exists → should be 200 with attachment header
        check("/cv with PDF returns 200",                r4.status_code == 200)
        check("/cv Content-Disposition is attachment",
              "attachment" in r4.headers.get("Content-Disposition",""))

    # POST /contact – honeypot triggered
    r5 = c.post("/contact",
                json={"name":"Bot","email":"bot@x.com",
                      "message":"Spam spam spam","_trap":"gotcha"})
    check("Honeypot fill → 200 (silent accept)", r5.status_code == 200)

    # POST /contact – validation error
    r6 = c.post("/contact", json={"name":"","email":"bad","message":""})
    check("Invalid contact → 400",            r6.status_code == 400)
    j6 = json.loads(r6.data)
    check("Invalid contact → errors list",    isinstance(j6.get("errors"), list))
    check("Invalid contact → ok=False",       j6.get("ok") is False)

    # POST /contact – rate limit (IP will be 127.0.0.1 in test client)
    # Pre-fill the rate store for this IP
    test_client_ip = "127.0.0.1"
    with _rate_lock:
        _rate_store[test_client_ip] = [time.monotonic()] * RATE_LIMIT_MAX
    r7 = c.post("/contact",
                json={"name":"N","email":"a@b.com","message":"Test test test!"})
    check("Rate-limited contact → 429",       r7.status_code == 429)

    # Custom 404 handler
    r8 = c.get("/this-page-does-not-exist-at-all")
    check("Unknown route → 404",              r8.status_code == 404)
    check("404 page is HTML",                 b"<" in r8.data)

# ── Context processor ─────────────────────────────────────────
print("\n[7] Context processor")
with app.test_request_context("/"):
    from app import inject_site_config
    ctx = inject_site_config()
    check("inject_site_config returns dict",          isinstance(ctx, dict))
    check("'site' key present",                       "site" in ctx)
    check("'current_year' key present",               "current_year" in ctx)
    check("site.meta.title contains 'Niduka'",        "Niduka" in ctx["site"]["meta"]["title"])
    check("No phone in site.contact",                 "phone" not in ctx["site"]["contact"])

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for s, _ in results if s == PASS)
failed = sum(1 for s, _ in results if s == FAIL)
print(f"  Results: {passed} passed, {failed} failed out of {len(results)} checks.")
print("=" * 60)

if failed:
    sys.exit(1)
