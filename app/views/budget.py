import altair as alt
import streamlit as st

import data

st.title("Which Rule Gives the Most per Dollar?")
st.markdown(
    "Imagine the budget covers **30% of the eligible households**. Which rule should decide who gets cash? "
    "Each rule picks its 30% and we measure the real gain for those households (treatment vs control, "
    "which works because the trials were randomised). Rules that use estimates were learned on one part "
    "of the data and tested on another."
)

country = st.segmented_control("Country", ["Kenya", "Uganda"], default="Uganda")
code = {v: k for k, v in data.COUNTRY_NAMES.items()}[country]
b = data.budget()
b = b[b.country == code].copy()

tooltip = [alt.Tooltip("rule:N", title="Rule"),
           alt.Tooltip("monthly_gain_per_100:Q", title="Gain per $100", format="$.2f"),
           alt.Tooltip("share_poorest_half:Q", title="Poorest half reached", format=".0%"),
           alt.Tooltip("effect_pct:Q", title="Gain", format="+.0%"),
           alt.Tooltip("p_value:Q", title="p-value", format=".3f")]
base = alt.Chart(b).encode(
    x=alt.X("share_poorest_half:Q", scale=alt.Scale(domain=[0, 1.05]),
            axis=alt.Axis(format="%", title="Share of chosen households from the poorest half")),
    y=alt.Y("monthly_gain_per_100:Q", title="Extra monthly consumption per $100 given"),
    tooltip=tooltip)
pts = base.mark_circle(size=160, color=data.COUNTRY_COLORS[country], opacity=1)
# labels go left of points near the right edge so they don't get cut off
labels = (base.transform_filter("datum.share_poorest_half <= 0.75").mark_text(align="left", dx=10, fontSize=13).encode(text="rule:N")
          + base.transform_filter("datum.share_poorest_half > 0.75").mark_text(align="right", dx=-10, fontSize=13).encode(text="rule:N"))
zero = alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(y=alt.datum(0))
st.altair_chart((zero + pts + labels).properties(height=380), width="stretch")

st.dataframe(b[["rule", "monthly_gain_per_100", "effect_pct", "ci_low", "ci_high", "share_poorest_half", "n"]],
             hide_index=True, width="stretch", column_config={
                 "rule": "Rule",
                 "monthly_gain_per_100": st.column_config.NumberColumn("Per $100 given", format="$%.2f"),
                 "effect_pct": st.column_config.NumberColumn("Gain", format="percent"),
                 "ci_low": st.column_config.NumberColumn("Range from ($/person)", format="%.1f"),
                 "ci_high": st.column_config.NumberColumn("Range to ($/person)", format="%.1f"),
                 "share_poorest_half": st.column_config.NumberColumn("Poorest half reached", format="percent"),
                 "n": "Households"})

if code == "UGA":
    st.warning(
        "In Uganda, choosing by household type gives about 5x more impact per dollar than choosing at random, "
        "but only about 1 in 5 chosen households come from the poorest half. More impact or reaching the "
        "poorest: that is a values choice for the programme."
    )
else:
    st.success("In Kenya there is no trade-off: giving to the poorest first also gives the most impact per dollar.")

with st.expander("Does a model from one country work in another?"):
    tr = data.transfer_check()
    st.markdown(
        "We trained the model on Kenya and used it to rank Uganda households. The households it expected to "
        "gain most did **not** gain more:"
    )
    st.dataframe(tr[["group", "effect_pct", "monthly_gain_per_100", "n"]], hide_index=True,
                 width="stretch", column_config={
                     "group": "Kenya model's prediction for Uganda",
                     "effect_pct": st.column_config.NumberColumn("Real gain", format="percent"),
                     "monthly_gain_per_100": st.column_config.NumberColumn("Per $100", format="$%.2f"),
                     "n": "Households"})
    st.markdown("So who benefits most depends on the context. Each programme needs its own local data.")
