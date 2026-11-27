"""cv_absent_check.py – test /cv when file is missing, using monkeypatching"""
import os
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("FLASK_ENV", "development")

import app as portfolio_app
from pathlib import Path

# Monkeypatch STATIC_FILES to a non-existent directory so the PDF is "missing"
real_static = portfolio_app.STATIC_FILES
portfolio_app.STATIC_FILES = Path("nonexistent_dir_xyz")

with portfolio_app.app.test_client() as c:
    r = c.get("/cv")
    body = r.data.decode("utf-8", errors="replace")
    print("\n[PDF absent – monkeypatched]")
    print(f"  Status                      : {r.status_code}")
    print(f"  Is 404                      : {r.status_code == 404}")
    print(f"  Contains friendly message   : {'CV file is not available' in body}")
    print(f"  Contains email fallback     : {'nidukavikumasipath@gmail.com' in body}")
    print(f"  Is HTML (not raw error)     : {'<html' in body.lower() or '<section' in body.lower()}")

# Restore
portfolio_app.STATIC_FILES = real_static
print("\n  (STATIC_FILES restored)\n")
