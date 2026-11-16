import altair as alt
import streamlit as st

import data

st.title("Where Did the Money Go?")
st.markdown("Extra spending per person per month at endline: households that got cash minus households that didn't.")

c1, c2 = st.columns([1, 2])
with c1:
    country = st.segmented_control("Country", ["Kenya", "Uganda"], default="Uganda")
types = data.household_types()
options = {"ALL": "All households"} | dict(zip(types.household_type, types.household_type + ": " + types.label))
with c2:
    t = st.selectbox("Household type", list(options), format_func=options.get)

code = {v: k for k, v in data.COUNTRY_NAMES.items()}[country]
sp = data.spending()
sp = sp[(sp.country == code) & (sp.household_type == t)].copy()
NAMES = {"food": "Food", "transport_communication": "Transport & phone", "energy_water": "Energy & water",
         "alcohol_tobacco": "Alcohol & tobacco", "personal_care": "Personal care", "recreation": "Recreation",
         "health": "Health", "clothing": "Clothing", "education": "Education", "social": "Social (weddings, funerals)"}
sp["group"] = sp.spend_group.map(NAMES).fillna(sp.spend_group)

chart = alt.Chart(sp).mark_bar(cornerRadiusEnd=4, height=18, color=data.COUNTRY_COLORS[country]).encode(
    y=alt.Y("group:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
    x=alt.X("extra_spend_pc_ppp:Q", title="Extra $ per person per month (PPP)"),
    tooltip=[alt.Tooltip("group:N", title="Spending"),
             alt.Tooltip("extra_spend_pc_ppp:Q", title="Extra per person", format="$.2f"),
             alt.Tooltip("mean_spend_treatment:Q", title="Got cash", format="$.2f"),
             alt.Tooltip("mean_spend_control:Q", title="No cash", format="$.2f")],
)
zero = alt.Chart().mark_rule(color=data.CONTROL_GREY).encode(x=alt.datum(0))
st.altair_chart((zero + chart).properties(height=max(200, 34 * len(sp))), width="stretch")

st.dataframe(sp.sort_values("extra_spend_pc_ppp", ascending=False)[
    ["group", "mean_spend_control", "mean_spend_treatment", "extra_spend_pc_ppp"]],
    hide_index=True, width="stretch", column_config={
        "group": "Spending",
        "mean_spend_control": st.column_config.NumberColumn("No cash", format="$%.2f"),
        "mean_spend_treatment": st.column_config.NumberColumn("Got cash", format="$%.2f"),
        "extra_spend_pc_ppp": st.column_config.NumberColumn("Difference", format="$%.2f")})

notes = {
    "KEN": "Most of the extra money went to food. Spending on alcohol and tobacco went slightly down, not up.",
    "UGA": "Food first, then transport/phone and energy/water. Very little went to alcohol. Education is "
           "close to zero because the endline (early 2022) came right after Uganda's long COVID school closures.",
}
st.info(notes[code])
