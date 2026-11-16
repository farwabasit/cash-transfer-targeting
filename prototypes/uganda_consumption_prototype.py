"""Prototype: monthly per-capita consumption aggregate for the GiveDirectly
Uganda (Kiryandongo) RCT, baseline 2019 and endline 2022.

Usage: python -I uganda_consumption_prototype.py <data_dir> <ppp_2019> <ppp_2022>
"""
import os
import sys

import numpy as np
import pandas as pd

D, PPP19, PPP22 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
M7, M4W, M12 = 30.4 / 7, 30.4 / 28, 1 / 12  # recall period -> month

# Comparable basket: items asked in BOTH rounds with the same recall period.
NONFOOD_7D = ["cons_tobacco", "cons_fuel", "cons_airtime", "cons_transport"]
NONFOOD_4W = ["cons_film", "cons_media", "cons_lottery", "cons_nightlife",
              "cons_sports", "cons_toiletries", "cons_services", "cons_water"]
NONFOOD_12M = ["cons_health_transport", "cons_health_drugs", "cons_health_consult",
               "cons_health_other", "cons_clothing", "cons_edu_fees",
               "cons_edu_uniform", "cons_edc_stationary", "cons_edc_other"]
# Excluded on purpose: savings groups & rent (baseline only -> schema drift),
# taxes/fines/fees (not consumption), social/dowry, migration, maintenance (lumpy).
FAFH_7D = ["fafh_school_val", "fafh_school2_val", "fafh_snack_val",
           "fafh_meals_val", "fafh_beverages_val", "fafh_alcohol_val"]


def clean(s):
    s = pd.to_numeric(s, errors="coerce")
    return s.where(s >= 0)  # negative codes (DK / refused) -> missing


def food_items(df):
    items = sorted(c.replace("cons_quant_", "") for c in df.columns
                   if c.startswith("cons_quant_"))
    total = pd.Series(0.0, index=df.index)
    report = {}
    for it in items:
        q = clean(df.get(f"cons_quant_{it}"))
        p = clean(df.get(f"price_unit_{it}")) if f"price_unit_{it}" in df else None
        tv = clean(df.get(f"totalval_{it}")) if f"totalval_{it}" in df else None
        v = pd.Series(np.nan, index=df.index)
        if tv is not None:
            v = v.fillna(tv)
        if p is not None:
            v = v.fillna(q * p)
        consumed = q.fillna(0) > 0
        report[it] = (int(consumed.sum()), int((consumed & v.isna()).sum()))
        total = total + v.fillna(0)
    for c in [c for c in df.columns if c.startswith("total_val_") and c.endswith("_oth")
              or c in ("total_val_leaf", "total_val_oil", "total_val_sweet",
                       "total_val_spices", "total_val_proc_food", "total_val_beverages")]:
        total = total + clean(df[c]).fillna(0)
    return total, report


def aggregate(path, ppp, label):
    df = pd.read_stata(path, convert_categoricals=False)
    food_home, rep = food_items(df)
    fafh = sum(clean(df[c]).fillna(0) for c in FAFH_7D if c in df)
    nf7 = sum(clean(df[c]).fillna(0) for c in NONFOOD_7D if c in df)
    nf4 = sum(clean(df[c]).fillna(0) for c in NONFOOD_4W if c in df)
    nf12 = sum(clean(df[c]).fillna(0) for c in NONFOOD_12M if c in df)
    missing_cols = [c for c in FAFH_7D + NONFOOD_7D + NONFOOD_4W + NONFOOD_12M if c not in df]

    out = pd.DataFrame({
        "hhid": df["hhid_rand"], "treat": df["treat"], "round": label,
        "hh_size": clean(df["hh_size"]),
        "food_m": (food_home + fafh) * M7,
        "nonfood_m": nf7 * M7 + nf4 * M4W + nf12 * M12,
    })
    if "BL_only" in df:  # endline file keeps attrited baseline rows
        out = out[df["BL_only"] == 0]
    out["total_m"] = out.food_m + out.nonfood_m
    # winsorise top 1% (standard practice for survey consumption)
    cap = out.total_m.quantile(0.99)
    out["total_m_w"] = out.total_m.clip(upper=cap)
    out["pc_ugx"] = out.total_m_w / out.hh_size
    out["pc_ppp"] = out.pc_ugx / ppp
    out["food_share"] = out.food_m / out.total_m
    gaps = {k: v for k, v in rep.items() if v[1] > 0}
    return out, gaps, missing_cols


bl, gaps_bl, miss_bl = aggregate(os.path.join(D, "XBVYXA__baseline_anonymized.tab"), PPP19, "baseline_2019")
el, gaps_el, miss_el = aggregate(os.path.join(D, "XBVYXA__endline_anonymized.tab"), PPP22, "endline_2022")

for name, d, gaps, miss in [("BASELINE 2019", bl, gaps_bl, miss_bl), ("ENDLINE 2022", el, gaps_el, miss_el)]:
    print(f"\n=== {name}: {len(d)} households")
    print("  columns absent in this round:", miss or "none")
    print("  food items consumed but with no value:", gaps or "none")
    print("  zero total consumption:", int((d.total_m == 0).sum()), "| missing hh_size:", int(d.hh_size.isna().sum()))
    print(d[["hh_size", "pc_ugx", "pc_ppp", "food_share"]].describe(percentiles=[.1, .5, .9]).round(2).to_string())
    print("  median per-capita PPP $ by arm:", d.groupby("treat").pc_ppp.median().round(2).to_dict())

m = el.merge(bl[["hhid", "pc_ppp"]], on="hhid", suffixes=("", "_bl"))
print(f"\nPanel matched: {len(m)} of {len(el)} endline households")
diff = m.groupby("treat").pc_ppp.mean()
print("Endline mean pc PPP $/month by arm:", diff.round(2).to_dict(),
      "| raw difference:", round(diff.get(1, np.nan) - diff.get(0, np.nan), 2))
bl.to_csv("uganda_consumption_baseline.csv", index=False)
el.to_csv("uganda_consumption_endline.csv", index=False)
