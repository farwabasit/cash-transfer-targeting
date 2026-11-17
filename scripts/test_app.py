"""Smoke test for the app: every .py file must parse and every page must render its title
through the real navigation (so links between pages work too).

    python scripts/test_app.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

bad = []
code = [APP.rglob("*.py"), (ROOT / "analysis").glob("*.py"), (ROOT / "ingestion").glob("*.py"),
        (ROOT / "airflow" / "dags").glob("*.py"), (ROOT / "scripts").glob("*.py")]
for f in [p for group in code for p in group]:
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        bad.append(f"{f.relative_to(ROOT)}: {e}")
if bad:
    print("SYNTAX ERRORS\n" + "\n".join(bad))
    sys.exit(1)

from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=180)
at.run()
ok = True
for page in sorted(p.relative_to(APP).as_posix() for p in (APP / "views").glob("*.py")):
    at.switch_page(page)
    at.run()
    if at.exception or not len(at.title):
        ok = False
        print(f"FAIL {page}: {at.exception}")
    else:
        print(f"ok   {page}: {at.title[0].value}")
print("ALL PAGES OK" if ok else "SOME PAGES FAILED")
sys.exit(0 if ok else 1)
