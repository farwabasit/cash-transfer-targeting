"""Build the dbt docs as one html file and put it where the app serves it.

    python scripts/build_docs.py

Runs `dbt docs generate --static`, removes local folder paths from the file and copies it
to app/static/dbt_docs.html (opened from the app at /app/static/dbt_docs.html).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "transform" / "target" / "static_index.html"
out = ROOT / "app" / "static" / "dbt_docs.html"

if "--skip-generate" not in sys.argv:
    subprocess.run([sys.executable, str(ROOT / "transform" / "run_dbt.py"), "docs", "generate", "--static"], check=True)

html = src.read_text(encoding="utf-8")
# the path is stored json-escaped (C:\\Users\\...) inside the file
for p in {str(ROOT / "transform"), str(ROOT)}:
    html = html.replace(json.dumps(p)[1:-1], "transform").replace(p, "transform")
leftover = str(Path.home().name)
if leftover.lower() in html.lower():
    raise SystemExit(f"local user name still in the docs file, not writing {out}")

out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
