import altair as alt
import streamlit as st

import data

st.title("Does It Look the Same in Pakistan?")
st.warning(
    "**Different programme:** Pakistan was part of the 6-country graduation programme (Banerjee et al. 2015). "
    "Families got an asset like livestock, a food stipend for some months and training. Not unconditional cash. "
    "So we compare the pattern of who gains, not the exact numbers.",
    icon=":material/compare_arrows:")

st.markdown(
    "**1,299 households** in a randomised trial, measured before and about 2 and 3 years after. "
    "The data has no household size per household. We use **two types**: the poorer half and the less poor "
    "half of baseline consumption per person."
)

eff = data.query("select * from ML.PAKISTAN_EFFECTS")
eff["name"] = eff.group.map({"ALL": "All households", "poorer": "Poorer half", "less_poor": "Less poor half"})
eff["order"] = eff.group.map({"ALL": 0, "poorer": 1, "less_poor": 2})
eff["ci_low_pct"], eff["ci_high_pct"] = eff.ci_low / eff.control_mean, eff.ci_high / eff.control_mean

st.subheader("Who Gains Most and Does It Last?")
st.caption("Dot = estimated gain in consumption per person, line = 95% range. If the line crosses 0 we can't be sure.")
colors = alt.Scale(domain=["about 2 years", "about 3 years"], range=[data.COUNTRY_COLORS["Kenya"], data.COUNTRY_COLORS["Uganda"]])
tip = [alt.Tooltip("name:N", title="Group"), alt.Tooltip("wave:N", title="After"),
       alt.Tooltip("effect_pct:Q", title="Gain", format="+.0%"),
       alt.Tooltip("ci_low_pct:Q", title="Range from", format="+.0%"),
       alt.Tooltip("ci_high_pct:Q", title="Range to", format="+.0%"),
       alt.Tooltip("n:Q", title="Households")]
base = alt.Chart(eff).encode(
    y=alt.Y("name:N", sort=alt.SortField("order"), title=None, axis=alt.Axis(labelLimit=200)),
    yOffset=alt.YOffset("wave:N"),
    color=alt.Color("wave:N", scale=colors, legend=alt.Legend(title="Measured after", orient="top")))
chart = (alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(x=alt.datum(0))
         + base.mark_rule(strokeWidth=2).encode(
             x=alt.X("ci_low_pct:Q", axis=alt.Axis(format="%", title="Gain in consumption per person vs no support")),
             x2="ci_high_pct:Q", tooltip=tip)
         + base.mark_circle(size=110, opacity=1).encode(x="effect_pct:Q", tooltip=tip))
st.altair_chart(chart.properties(height=280), width="stretch")

st.dataframe(eff.sort_values(["wave", "order"])[["wave", "name", "n", "effect_pct", "ci_low_pct", "ci_high_pct",
                                                 "gain_per_100_transfer", "gain_per_100_total_cost", "p_value"]],
             hide_index=True, width="stretch", column_config={
                 "wave": "After", "name": "Group", "n": "Households",
                 "effect_pct": st.column_config.NumberColumn("Gain", format="percent"),
                 "ci_low_pct": st.column_config.NumberColumn("Range from", format="percent"),
                 "ci_high_pct": st.column_config.NumberColumn("Range to", format="percent"),
                 "gain_per_100_transfer": st.column_config.NumberColumn("Per $100 transferred", format="$%.2f"),
                 "gain_per_100_total_cost": st.column_config.NumberColumn("Per $100 total cost", format="$%.2f"),
                 "p_value": st.column_config.NumberColumn("p-value", format="%.3f")})

st.subheader("What It Means")
st.markdown(
    "- **Pakistan looks like Kenya, not Uganda:** after about 2 years the poorer half gained +18% and the less "
    "poor half +4% (not clear).\n"
    "- **The gain faded by year 3:** +5% overall with a range that includes zero.\n"
    "- **More expensive per result:** the programme cost $5,150 per household including staff and training. "
    "Each $100 of total cost gave about $1 extra monthly consumption, against $3.85 (Kenya) and $7.56 (Uganda) "
    "for cash. Graduation also builds assets and skills, which this number doesn't count.\n"
    "- **Same lesson:** who gains most depends on the place. Two of three places say the poorest first, one says not."
)
st.caption("Money in 2014 PPP dollars. Average household size 6.29 (year 2) and 6.58 (year 3) from the paper's cost "
           "table, because the file has no size per household.")
