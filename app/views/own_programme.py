import altair as alt
import pandas as pd
import streamlit as st

import data
import method

st.title("Analyse My Own Programme")
st.markdown(
    "Our trials showed that who gains most depends on the place. So the best answer for your programme comes "
    "from **your own data**. Upload your monitoring data and get your own household types, gains, "
    "return per 100 given and budget trade-off. Same method as the Kenya and Uganda analysis."
)
st.info(
    "**What you need:** households that got support and a comparison group that did not, measured before "
    "and after. Best if the comparison group was chosen at random (a lottery or a phased roll-out). Without "
    "that the numbers mix the effect of support with everything else that changed.",
    icon=":material/info:")

REQUIRED = ["household_id", "treated", "consumption_before", "consumption_after", "hh_size"]
with st.expander("File format"):
    st.markdown(
        "A CSV with one row per household:\n"
        "- `household_id`: your own ID\n"
        "- `treated`: 1 if the household got support, 0 if not (yes/no also works)\n"
        "- `consumption_before`: monthly consumption per person before the support\n"
        "- `consumption_after`: monthly consumption per person at follow-up\n"
        "- `hh_size`: number of people in the household before the support"
    )
    st.download_button("Download an example file (real Uganda trial households)",
                       data.example_programme().to_csv(index=False), "example_programme.csv", "text/csv")

up = st.file_uploader("Monitoring data (CSV)", type="csv", key="own_upload")
use_example = st.toggle("Use the example file instead", value=up is None, key="own_example")
if up is not None and not use_example:
    try:
        raw = pd.read_csv(up)
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        st.stop()
else:
    raw = data.example_programme()

raw.columns = [c.strip().lower() for c in raw.columns]
missing = [c for c in REQUIRED if c not in raw.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

df = pd.DataFrame({
    "household_id": raw.household_id,
    "treated": raw.treated.astype(str).str.strip().str.lower().map(
        {"1": 1, "1.0": 1, "yes": 1, "true": 1, "0": 0, "0.0": 0, "no": 0, "false": 0}),
    "before": pd.to_numeric(raw.consumption_before, errors="coerce"),
    "after": pd.to_numeric(raw.consumption_after, errors="coerce"),
    "hh_size": pd.to_numeric(raw.hh_size, errors="coerce"),
})
bad = df.isna().any(axis=1) | (df.hh_size < 1) | (df.before < 0) | (df.after < 0)
if bad.sum():
    st.warning(f"{int(bad.sum())} rows skipped (missing values, unknown treated value or negative numbers).")
df = df[~bad]
if df.treated.nunique() < 2 or len(df) < 60:
    st.error("Need at least 60 households with both groups (treated = 1 and treated = 0).")
    st.stop()

cur, rate = data.currency_inputs("own")
default_transfer = 2848.0 if use_example else 1000.0
transfer_in = st.number_input(f"Support per household ({cur})", min_value=1.0,
                              value=round(default_transfer * rate, 0), step=50.0,
                              help="Average value of the support (or cost per household) for treated households.")
for c in ["before", "after"]:
    df[c] = df[c] / rate
transfer = transfer_in / rate

d, med_c, med_s = method.prepare(df)
st.caption(f"{len(d):,} households ({int(d.treated.sum()):,} with support). Types use your file's medians: "
           f"{med_c * rate:,.0f} {cur} per person per month and {med_s:.0f} people per household.")

eff = method.effects_by_type(d, transfer)
eff["name"] = eff.apply(lambda r: "All" if r.type == "ALL" else f"{r.type}: {r.label}", axis=1)
eff["ci_low_pct"], eff["ci_high_pct"] = eff.ci_low / eff.control_mean, eff.ci_high / eff.control_mean
eff["gain_per_100_local"] = eff.gain_per_100 * rate  # per 100 local units given, in local units
eff["small"] = eff[["n_treatment", "n_control"]].min(axis=1) < 30

st.subheader("Who Gains Most in My Programme?")
order = {"ALL": 0, "A": 1, "B": 2, "C": 3, "D": 4}
eff["order"] = eff.type.map(order)
base = alt.Chart(eff).encode(y=alt.Y("name:N", sort=alt.SortField("order"), title=None, axis=alt.Axis(labelLimit=260)))
tip = [alt.Tooltip("name:N", title="Type"), alt.Tooltip("effect_pct:Q", title="Gain", format="+.0%"),
       alt.Tooltip("ci_low_pct:Q", title="Range from", format="+.0%"),
       alt.Tooltip("ci_high_pct:Q", title="Range to", format="+.0%"), alt.Tooltip("n:Q", title="Households")]
color = data.COUNTRY_COLORS["Kenya"]
chart = (alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(x=alt.datum(0))
         + base.mark_rule(strokeWidth=2, color=color).encode(
             x=alt.X("ci_low_pct:Q", axis=alt.Axis(format="%", title="Gain in consumption per person")),
             x2="ci_high_pct:Q", tooltip=tip)
         + base.mark_circle(size=120, color=color, opacity=1).encode(x="effect_pct:Q", tooltip=tip))
st.altair_chart(chart.properties(height=260), width="stretch")
data.how_to_read("Each row is one household type in your file. The dot is how much more households with support "
                 "consumed than those without. The line is the 95% range. If the line crosses the dashed 0 line "
                 "we can't be sure that type gained.")

st.dataframe(eff.sort_values("order")[["name", "n_treatment", "n_control", "effect_pct", "ci_low_pct",
                                       "ci_high_pct", "gain_per_100_local", "small"]],
             hide_index=True, width="stretch", column_config={
                 "name": "Type", "n_treatment": "With support", "n_control": "Without",
                 "effect_pct": st.column_config.NumberColumn("Gain", format="percent"),
                 "ci_low_pct": st.column_config.NumberColumn("Range from", format="percent"),
                 "ci_high_pct": st.column_config.NumberColumn("Range to", format="percent"),
                 "gain_per_100_local": st.column_config.NumberColumn(f"Monthly gain per 100 {cur} given", format="%.2f"),
                 "small": st.column_config.CheckboxColumn("Small group", help="Fewer than 30 households in one of the groups.")})

st.subheader("Which Rule Gives the Most per 100 Given?")
b = method.budget_rules(d, transfer)
b["gain_per_100_local"] = b.gain_per_100 * rate
tip_b = [alt.Tooltip("rule:N", title="Rule"),
         alt.Tooltip("gain_per_100_local:Q", title=f"Gain per 100 {cur}", format=".2f"),
         alt.Tooltip("share_poorest_half:Q", title="Poorest half reached", format=".0%")]
bb = alt.Chart(b).encode(
    x=alt.X("share_poorest_half:Q", scale=alt.Scale(domain=[0, 1.05]),
            axis=alt.Axis(format="%", title="Share of chosen households from the poorest half")),
    y=alt.Y("gain_per_100_local:Q", title=f"Monthly gain per 100 {cur} given"), tooltip=tip_b)
labels = (bb.transform_filter("datum.share_poorest_half <= 0.75").mark_text(align="left", dx=10, fontSize=13).encode(text="rule:N")
          + bb.transform_filter("datum.share_poorest_half > 0.75").mark_text(align="right", dx=-10, fontSize=13).encode(text="rule:N"))
st.altair_chart((alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(y=alt.datum(0))
                 + bb.mark_circle(size=160, color=color, opacity=1) + labels).properties(height=340), width="stretch")
data.how_to_read("Each dot is one way of choosing who gets support. Higher up = more gain for every 100 given. "
                 "Further right = more of the chosen households come from the poorest half. Compare the dots to "
                 "see what you gain and what you give up with each rule.")
st.caption("Budget for 30% of the households in the file. The type rule is learned on one half of the data and "
           "tested on the other half. That way it is not judged on the data it learned from.")

out = d.merge(eff[["type", "effect", "label"]].rename(columns={"effect": "type_gain_pc"}), on="type", how="left")
out["type_gain_pc"] = out.type_gain_pc * rate
st.download_button("Download my households with their type", out.to_csv(index=False), "my_programme_types.csv", "text/csv")
