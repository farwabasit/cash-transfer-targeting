"""Run dbt with the project's .env loaded, from any folder.

    python transform/run_dbt.py debug
    python transform/run_dbt.py build
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

env = ROOT / ".env"
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
if key and not Path(key).is_absolute():
    os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"] = str(ROOT / key)

from dbt.cli.main import dbtRunner  # noqa: E402

args = sys.argv[1:] or ["debug"]
res = dbtRunner().invoke(args + ["--project-dir", str(HERE), "--profiles-dir", str(HERE)])
sys.exit(0 if res.success else 1)
