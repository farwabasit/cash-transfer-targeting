"""Analysis step, reads GOLD from snowflake and writes results to the ML schema.

1. ANCOVA effect per country and household type
2. causal forest (EconML) per household -> do the high gainers fall in my types?
3. train on kenya, predict uganda -> does it carry over to another country?
4. budget simulation: who to give cash to with a fixed budget

    python analysis/run_analysis.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))
import load_raw  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 42
BUDGET_SHARE = 0.30          # budget covers 30% of eligible households
POVERTY_LINE = 65.40         # $2.15/day x 30.4, see seeds/poverty_lines.csv

COMMON = ["rel_consumption", "rel_hh_size", "has_children"]
EXTRA = {
    "KEN": ["children_bl", "married_bl", "respondent_age_bl", "respondent_education_years_bl"],
    "UGA": ["female_head_bl", "head_education_level_bl"],
}


def load(conn):
    sql = """
    select o.household_id, o.country, o.treated, o.household_type, o.hh_size_bl,
           o.consumption_pc_bl_w, o.consumption_pc_el_w, o.median_consumption_pc_bl,
           o.median_hh_size_bl, o.transfer_ppp,
           k.children_bl, k.married_bl, k.respondent_age_bl, k.respondent_education_years_bl,
           coalesce(k.has_children_bl, u.has_children_bl) as has_children,
           u.female_head_bl, u.head_education_level_bl
    from GOLD.GLD_HOUSEHOLD_OUTCOMES o
    left join SILVER.SLV_KENYA_HOUSEHOLDS k on o.country = 'KEN' and k.household_id = o.household_id
    left join SILVER.SLV_UGANDA_HOUSEHOLDS u on o.country = 'UGA' and u.household_id = o.household_id
    where o.in_analysis and o.household_type is not null and o.consumption_pc_el_w is not null
    """
    df = pd.read_sql(sql, conn)
    df.columns = [c.lower() for c in df.columns]
    df["rel_consumption"] = df.consumption_pc_bl_w / df.median_consumption_pc_bl
    df["rel_hh_size"] = df.hh_size_bl / df.median_hh_size_bl
    for c in ["has_children", "married_bl", "female_head_bl"]:
        df[c] = df[c].astype(float)
    return df


def ancova(d):
    """effect of treatment on endline consumption, controlling for baseline (robust SE)"""
    X = sm.add_constant(d[["treated", "consumption_pc_bl_w"]].astype(float))
    m = sm.OLS(d.consumption_pc_el_w.astype(float), X).fit(cov_type="HC1")
    b, se = m.params["treated"], m.bse["treated"]
    ctrl = d.loc[d.treated == 0, "consumption_pc_el_w"].mean()
    t = d[d.treated == 1]
    per100 = 100 * b * t.hh_size_bl.mean() / t.transfer_ppp.mean()
    gap = lambda x: np.maximum(0, (POVERTY_LINE - x) / POVERTY_LINE).mean()
    return dict(n=len(d), n_treatment=int(d.treated.sum()), effect_pc=b, se=se,
                ci_low=b - 1.96 * se, ci_high=b + 1.96 * se, p_value=m.pvalues["treated"],
                control_mean=ctrl, effect_pct=b / ctrl, monthly_gain_per_100=per100,
                poverty_gap_reduction=gap(d.loc[d.treated == 0, "consumption_pc_el_w"])
                - gap(d.loc[d.treated == 1, "consumption_pc_el_w"]))


def effects_by_type(df):
    rows = []
    for country, g in df.groupby("country"):
        rows.append(dict(country=country, household_type="ALL", **ancova(g)))
        for t, gt in g.groupby("household_type"):
            rows.append(dict(country=country, household_type=t, **ancova(gt)))
    return pd.DataFrame(rows)


def forest():
    from econml.dml import CausalForestDML
    return CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, min_samples_leaf=10, random_state=SEED),
        model_t=DummyClassifier(strategy="prior"),   # randomised, so treatment can't be predicted
        discrete_treatment=True, n_estimators=400, min_samples_leaf=20,
        max_depth=6, random_state=SEED)


def crossfit_cate(g, features, folds=5):
    """predict each household's gain with a model that never saw that household"""
    cate = np.zeros(len(g))
    X, y, T = g[features].fillna(g[features].median()).values, g.consumption_pc_el_w.values, g.treated.values
    W = g[["consumption_pc_bl_w"]].values
    for tr, te in KFold(folds, shuffle=True, random_state=SEED).split(X):
        est = forest().fit(y[tr], T[tr], X=X[tr], W=W[tr])
        cate[te] = est.effect(X[te])
    return cate


def household_cate(df):
    out = []
    for country, g in df.groupby("country"):
        g = g.copy()
        feats = COMMON + EXTRA[country]
        g["cate_pc"] = crossfit_cate(g, feats)
        g["cate_rank_pct"] = g.cate_pc.rank(pct=True)
        out.append(g[["household_id", "country", "household_type", "treated", "cate_pc", "cate_rank_pct"]])
    return pd.concat(out)


def type_check(cate):
    """E check: are the model's top 25% gainers concentrated in some types?"""
    rows = []
    for country, g in cate.groupby("country"):
        top = g[g.cate_rank_pct > 0.75]
        for t, gt in g.groupby("household_type"):
            share_all, share_top = len(gt) / len(g), (top.household_type == t).mean()
            rows.append(dict(country=country, household_type=t, mean_cate_pc=gt.cate_pc.mean(),
                             share_of_households=share_all, share_of_top25=share_top,
                             lift=share_top / share_all))
    return pd.DataFrame(rows)


def transfer_check(df):
    """train on kenya (common relative features only), rank uganda, check real gains by predicted group"""
    ken, uga = df[df.country == "KEN"], df[df.country == "UGA"].copy()
    est = forest().fit(ken.consumption_pc_el_w.values, ken.treated.values,
                       X=ken[COMMON].values, W=ken[["consumption_pc_bl_w"]].values)
    uga["pred"] = est.effect(uga[COMMON].values)
    uga["pred_group"] = pd.qcut(uga.pred.rank(method="first"), 2, labels=["low predicted gain", "high predicted gain"])
    rows = [dict(trained_on="KEN", tested_on="UGA", group=str(k), **ancova(g)) for k, g in uga.groupby("pred_group")]
    return pd.DataFrame(rows)


def pick(g, score, share, ascending=False):
    n = int(round(share * len(g)))
    return g.sort_values(score, ascending=ascending).head(n)


def budget_simulation(df, cate):
    """same budget, different rules. the gain is measured on the chosen households,
    treatment vs control (valid because assignment was random). rules that need
    estimates are cross-fitted so they're not judged on the data they learned from."""
    df = df.merge(cate[["household_id", "country", "cate_pc"]], on=["household_id", "country"])
    rng = np.random.default_rng(SEED)
    rows = []
    for country, g in df.groupby("country"):
        g = g.copy()
        g["random"] = rng.random(len(g))
        poorest_half = g.rel_consumption < 1
        # type rule: rank types on one half of the data, select on the other half
        g["fold"] = rng.integers(0, 2, len(g))
        g["type_score"] = np.nan
        for f in (0, 1):
            fit = effects_by_type(g[g.fold != f]).query("household_type != 'ALL'")
            score = fit.set_index("household_type").monthly_gain_per_100
            idx = g.fold == f
            g.loc[idx, "type_score"] = g.loc[idx, "household_type"].map(score) + g.loc[idx, "random"] * 1e-6
        rules = {
            "Random (no targeting)": pick(g, "random", BUDGET_SHARE),
            "Poorest first": pick(g, "rel_consumption", BUDGET_SHARE, ascending=True),
            "By household type": pick(g, "type_score", BUDGET_SHARE),
            "By model (predicted gain)": pick(g, "cate_pc", BUDGET_SHARE),
        }
        for rule, sel in rules.items():
            r = ancova(sel)
            rows.append(dict(country=country, rule=rule, budget_share=BUDGET_SHARE,
                             share_poorest_half=poorest_half[sel.index].mean(), **r))
    return pd.DataFrame(rows)


PAK_HH_SIZE = {"end": 6.29, "fup": 6.58}   # average household size, Banerjee et al. (2015) cost table
PAK_COST = {"direct_transfer": 2048.15, "total_cost": 5150.14}


def pakistan(conn):
    """graduation programme in pakistan: effect at ~2 years (end) and ~3 years (fup), all and by poverty half"""
    df = pd.read_sql("select * from GOLD.GLD_PAKISTAN_OUTCOMES", conn)
    df.columns = [c.lower() for c in df.columns]
    rows = []
    for wave in ["end", "fup"]:
        d = df[df[f"consumption_pc_{wave}_w"].notna()]
        for group, g in [("ALL", d)] + sorted(d.groupby("poverty_group")):
            X = sm.add_constant(g[["treated", "consumption_pc_bl_w"]].astype(float))
            m = sm.OLS(g[f"consumption_pc_{wave}_w"].astype(float), X).fit(cov_type="HC1")
            b, se = m.params["treated"], m.bse["treated"]
            ctrl = g.loc[g.treated == 0, f"consumption_pc_{wave}_w"].mean()
            rows.append(dict(
                wave={"end": "about 2 years", "fup": "about 3 years"}[wave], group=group, n=len(g),
                n_treatment=int(g.treated.sum()), effect_pc=b, se=se, ci_low=b - 1.96 * se, ci_high=b + 1.96 * se,
                p_value=m.pvalues["treated"], control_mean=ctrl, effect_pct=b / ctrl,
                gain_per_100_transfer=100 * b * PAK_HH_SIZE[wave] / PAK_COST["direct_transfer"],
                gain_per_100_total_cost=100 * b * PAK_HH_SIZE[wave] / PAK_COST["total_cost"]))
    return pd.DataFrame(rows)


def write(conn, tables):
    from snowflake.connector.pandas_tools import write_pandas
    conn.cursor().execute("create schema if not exists ML")
    for name, df in tables.items():
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]
        df["RUN_AT"] = pd.Timestamp.now("UTC").tz_localize(None)
        write_pandas(conn, df, name, schema="ML", auto_create_table=True, overwrite=True,
                     quote_identifiers=True, use_logical_type=True)
        print(f"ML.{name}: {len(df)} rows")


def main():
    load_raw.load_dotenv(ROOT / ".env")
    conn = load_raw.connect()
    df = load(conn)
    print(df.groupby(["country", "treated"]).size().unstack())

    eff = effects_by_type(df)
    cate = household_cate(df)
    tables = {
        "EFFECTS_ANCOVA": eff,
        "HOUSEHOLD_CATE": cate,
        "TYPE_CHECK": type_check(cate),
        "TRANSFER_CHECK": transfer_check(df),
        "BUDGET_SIMULATION": budget_simulation(df, cate),
        "PAKISTAN_EFFECTS": pakistan(conn),
    }
    pd.set_option("display.width", 220)
    for k, v in tables.items():
        if k != "HOUSEHOLD_CATE":
            print(f"\n{k}\n", v.round(3).to_string(index=False))
    write(conn, tables)
    conn.close()


if __name__ == "__main__":
    main()
