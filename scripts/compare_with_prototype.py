"""Reconciliation test: the dbt model must reproduce the Python prototype household by household.

Needs the prototype outputs in data/processed/ (run prototypes/uganda_consumption_prototype.py).
    python scripts/compare_with_prototype.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))
import load_raw  # noqa: E402

TOL = 0.01  # PPP dollars per person per month

load_raw.load_dotenv(ROOT / ".env")
conn = load_raw.connect()
dbt = pd.read_sql("select household_id, wave, consumption_pc_ppp, food_share "
                  "from SILVER.SLV_UGANDA_HOUSEHOLD_CONSUMPTION", conn)
conn.close()
dbt.columns = [c.lower() for c in dbt.columns]

ok = True
for wave, f in [("baseline_2019", "uganda_consumption_baseline.csv"), ("endline_2022", "uganda_consumption_endline.csv")]:
    proto = pd.read_csv(ROOT / "data" / "processed" / f)
    proto["household_id"] = proto["hhid"].astype(int).astype(str)
    m = proto.merge(dbt[dbt.wave == wave], on="household_id", how="outer", indicator=True)
    only = m["_merge"].value_counts().to_dict()
    both = m[m["_merge"] == "both"]
    diff = (both["pc_ppp"] - both["consumption_pc_ppp"]).abs()
    nan_mismatch = int((both["pc_ppp"].isna() != both["consumption_pc_ppp"].isna()).sum())
    bad = int((diff > TOL).sum()) + nan_mismatch
    print(f"{wave}: matched {len(both)}, only prototype {only.get('left_only', 0)}, only dbt {only.get('right_only', 0)}, "
          f"max diff {np.nanmax(diff):.6f}, households over tolerance {bad}")
    ok &= bad == 0 and only.get("left_only", 0) == 0 and only.get("right_only", 0) == 0

print("PASS: dbt matches the prototype" if ok else "FAIL: dbt and prototype differ")
sys.exit(0 if ok else 1)
