"""same method as analysis/run_analysis.py, in plain numpy so the app needs no extra packages"""
import numpy as np
import pandas as pd

TYPE_LABELS = {"A": "Poorer, smaller household", "B": "Poorer, larger household",
               "C": "Less poor, smaller household", "D": "Less poor, larger household"}


def ancova(d, transfer):
    """effect of support on 'after', controlling for 'before'. robust (HC1) standard errors."""
    y = d.after.to_numpy(float)
    X = np.column_stack([np.ones(len(d)), d.treated.to_numpy(float), d.before.to_numpy(float)])
    n, k = X.shape
    if n <= k or d.treated.nunique() < 2:
        return None
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    V = XtX_inv @ (X.T * e**2) @ X @ XtX_inv * n / (n - k)
    b, se = beta[1], np.sqrt(V[1, 1])
    ctrl = d.loc[d.treated == 0, "after"].mean()
    t = d[d.treated == 1]
    return dict(n=n, n_treatment=len(t), n_control=n - len(t), effect=b, se=se,
                ci_low=b - 1.96 * se, ci_high=b + 1.96 * se, control_mean=ctrl, effect_pct=b / ctrl,
                gain_per_100=100 * b * t.hh_size.mean() / transfer)


def prepare(df):
    """cap the top 1% (like the pipeline) and give every household a type from the file's own medians"""
    d = df.copy()
    for c in ["before", "after"]:
        d[c] = d[c].clip(upper=d[c].quantile(0.99))
    med_c, med_s = d.before.median(), d.hh_size.median()
    poorer, larger = d.before < med_c, d.hh_size >= med_s
    d["type"] = np.select([poorer & ~larger, poorer & larger, ~poorer & ~larger], ["A", "B", "C"], "D")
    return d, med_c, med_s


def effects_by_type(d, transfer):
    rows = []
    for t, g in [("ALL", d)] + sorted(d.groupby("type")):
        r = ancova(g, transfer)
        if r:
            rows.append(dict(type=t, label=TYPE_LABELS.get(t, "All households"), **r))
    return pd.DataFrame(rows)


def budget_rules(d, transfer, share=0.30, seed=42):
    """same budget, different rules; gain measured on the chosen households (needs random assignment)"""
    rng = np.random.default_rng(seed)
    d = d.copy()
    d["random"] = rng.random(len(d))
    d["fold"] = rng.integers(0, 2, len(d))
    d["type_score"] = np.nan
    for f in (0, 1):  # rank types on one half, choose on the other half
        fit = effects_by_type(d[d.fold != f], transfer).query("type != 'ALL'").set_index("type").gain_per_100
        idx = d.fold == f
        d.loc[idx, "type_score"] = d.loc[idx, "type"].map(fit) + d.loc[idx, "random"] * 1e-6
    n = int(round(share * len(d)))
    med = d.before.median()
    picks = {
        "Random (no targeting)": d.nlargest(n, "random"),
        "Poorest first": d.nsmallest(n, "before"),
        "By household type": d.nlargest(n, "type_score"),
    }
    rows = []
    for rule, sel in picks.items():
        r = ancova(sel, transfer)
        if r:
            rows.append(dict(rule=rule, share_poorest_half=(sel.before < med).mean(), **r))
    return pd.DataFrame(rows)
