import altair as alt
import streamlit as st

import data

st.title("Lump Sum or Monthly Payments?")
st.markdown(
    "GiveDirectly asked us which design fits best for different households: **one large lump sum** or **monthly "
    "payments**. The Kenya trial tested exactly this. Households getting $404 were randomly given it either at once "
    "or spread over 9 months. (The larger $1,525 transfers were all monthly. They are left out to keep it fair.)"
)

lm = data.query("select * from ML.LUMP_VS_MONTHLY")
n = lm[(lm.outcome == lm.outcome.iloc[0]) & (lm.group == "All households")].iloc[0]
st.caption(f"{int(n.n_lump)} households got a lump sum, {int(n.n_monthly)} got monthly payments and "
           f"{int(n.n_control)} did not get cash.")

long = []
for _, r in lm.iterrows():
    for design, p, lo, hi in [("Lump sum", r.lump_pct, r.lump_ci_low, r.lump_ci_high),
                              ("Monthly", r.monthly_pct, r.monthly_ci_low, r.monthly_ci_high)]:
        long.append(dict(outcome=r.outcome, group=r.group, design=design, gain=p,
                         low=lo / r.control_mean, high=hi / r.control_mean))
import pandas as pd  # noqa: E402
long = pd.DataFrame(long)

designs = alt.Scale(domain=["Lump sum", "Monthly"], range=[data.COUNTRY_COLORS["Kenya"], data.COUNTRY_COLORS["Uganda"]])
groups = ["All households", "Poorer half", "Less poor half"]
zero = alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(x=alt.datum(0))
for outcome, question in [("Consumption per person per month", "Which Design Raises Spending More?"),
                          ("Household assets", "Which Design Builds More Assets?")]:
    st.subheader(question)
    d = long[long.outcome == outcome]
    tip = [alt.Tooltip("group:N", title="Households"), alt.Tooltip("design:N", title="Design"),
           alt.Tooltip("gain:Q", title="Gain vs no cash", format="+.0%"),
           alt.Tooltip("low:Q", title="Range from", format="+.0%"), alt.Tooltip("high:Q", title="Range to", format="+.0%")]
    base = alt.Chart(d).encode(y=alt.Y("group:N", sort=groups, title=None, axis=alt.Axis(labelLimit=200)),
                               yOffset=alt.YOffset("design:N"),
                               color=alt.Color("design:N", scale=designs, legend=alt.Legend(title=None, orient="top")))
    chart = (zero
             + base.mark_rule(strokeWidth=2).encode(
                 x=alt.X("low:Q", axis=alt.Axis(format="%", title=f"{outcome}: gain vs households without cash")),
                 x2="high:Q", tooltip=tip)
             + base.mark_circle(size=110, opacity=1).encode(x="gain:Q", tooltip=tip))
    st.altair_chart(chart.properties(height=240), width="stretch")

table = lm[["outcome", "group", "lump_pct", "monthly_pct", "lump_minus_monthly", "diff_ci_low", "diff_ci_high", "diff_p_value"]]
st.dataframe(table, hide_index=True, width="stretch", column_config={
    "outcome": "Outcome", "group": "Households",
    "lump_pct": st.column_config.NumberColumn("Lump sum", format="percent"),
    "monthly_pct": st.column_config.NumberColumn("Monthly", format="percent"),
    "lump_minus_monthly": st.column_config.NumberColumn("Lump minus monthly ($)", format="%.1f"),
    "diff_ci_low": st.column_config.NumberColumn("Range from", format="%.1f"),
    "diff_ci_high": st.column_config.NumberColumn("Range to", format="%.1f"),
    "diff_p_value": st.column_config.NumberColumn("p-value", format="%.3f")})

st.subheader("What It Means")
st.markdown(
    "- **For spending both designs work about the same:** +16% with a lump sum and +13% with monthly payments. "
    "The difference is not clear.\n"
    "- **A lump sum builds more assets:** +58% against +33% for monthly payments. That is about $116 more in "
    "assets per household. This difference is clear.\n"
    "- **Poorer households did well with either design:** spending +17% (lump sum) and +25% (monthly). Neither "
    "design was clearly better for them.\n"
    "- **For less poor households the lump sum looks better:** clearly more assets (+$151) and more spending, "
    "although the spending difference is not clear.\n"
    "- **So the choice depends on the goal:** monthly payments are as good for day-to-day needs. A lump sum "
    "helps households invest, for example in a metal roof or livestock."
)
st.caption("Kenya only (2011-12), about 9 months after the transfers started. Assets in PPP $ per household, top 1% "
           "capped. Groups of 80-100 households per design. The ranges are wide.")
