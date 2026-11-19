import altair as alt
import streamlit as st

import data

st.title("Who Gains Most?")

country = st.segmented_control("Country", ["Kenya", "Uganda"], default="Uganda")
code = {v: k for k, v in data.COUNTRY_NAMES.items()}[country]
color = data.COUNTRY_COLORS[country]

types = data.household_types()
med = data.medians().set_index("country").loc[code]
st.markdown(
    f"Types use {country}'s own medians: **${med.median_consumption_pc_bl:.0f}** per person per month "
    f"and **{med.median_hh_size_bl:.0f}** people per household (at baseline)."
)
st.dataframe(types[["household_type", "label", "rule"]].rename(
    columns={"household_type": "Type", "label": "Household type", "rule": "Who belongs here"}),
    hide_index=True, width="stretch")

eff = data.effects()
e = eff[eff.country == code].copy()
e["order"] = e.household_type.map({"ALL": 0, "A": 1, "B": 2, "C": 3, "D": 4})
e["name"] = e.apply(lambda r: "All" if r.household_type == "ALL" else f"{r.household_type}: {r.label}", axis=1)

st.subheader("Which type gains most?")
base = alt.Chart(e).encode(y=alt.Y("name:N", sort=alt.SortField("order"), title=None, axis=alt.Axis(labelLimit=260)))
tooltip = [alt.Tooltip("name:N", title="Type"), alt.Tooltip("effect_pct:Q", title="Gain", format="+.0%"),
           alt.Tooltip("ci_low_pct:Q", title="Range from", format="+.0%"),
           alt.Tooltip("ci_high_pct:Q", title="Range to", format="+.0%"),
           alt.Tooltip("monthly_gain_per_100:Q", title="Per $100 given", format="$.2f"),
           alt.Tooltip("n:Q", title="Households")]
rules = base.mark_rule(strokeWidth=2, color=color).encode(
    x=alt.X("ci_low_pct:Q", axis=alt.Axis(format="%", title="Gain in consumption per person vs control")),
    x2="ci_high_pct:Q", tooltip=tooltip)
dots = base.mark_circle(size=120, color=color, opacity=1).encode(x="effect_pct:Q", tooltip=tooltip)
zero = alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(x=alt.datum(0))
st.altair_chart((zero + rules + dots).properties(height=260), width="stretch")
data.how_to_read("Each row is one household type. The dot is how much more households with cash consumed than "
                 "similar households without cash. The line is the 95% range. If the line crosses the dashed 0 line "
                 "we can't be sure that type gained. A dot further right means a bigger gain.")

show = e.sort_values("order")[["name", "n", "effect_pct", "ci_low_pct", "ci_high_pct", "monthly_gain_per_100", "p_value"]]
st.dataframe(show, hide_index=True, width="stretch", column_config={
    "name": "Type", "n": "Households",
    "effect_pct": st.column_config.NumberColumn("Gain", format="percent"),
    "ci_low_pct": st.column_config.NumberColumn("Range from", format="percent"),
    "ci_high_pct": st.column_config.NumberColumn("Range to", format="percent"),
    "monthly_gain_per_100": st.column_config.NumberColumn("Per $100 given", format="$%.2f"),
    "p_value": st.column_config.NumberColumn("p-value", format="%.3f"),
})

st.subheader("Does a Machine Learning Model Agree?")
tc = data.type_check()
tc = tc[tc.country == code].merge(types[["household_type", "label"]], on="household_type")
tc["name"] = tc.household_type + ": " + tc.label
st.markdown(
    "A causal forest predicted each household's gain **without knowing the types**. "
    "If a type holds more of the model's top 25% gainers than its share of households, the model agrees "
    "that this type gains more."
)
long = tc.melt(id_vars=["name"], value_vars=["share_of_households", "share_of_top25"],
               var_name="measure", value_name="share")
long["measure"] = long.measure.map({"share_of_households": "Share of all households",
                                    "share_of_top25": "Share of model's top 25% gainers"})
chart = alt.Chart(long).mark_bar(cornerRadiusEnd=4, height=14).encode(
    y=alt.Y("name:N", title=None, axis=alt.Axis(labelLimit=260)),
    yOffset=alt.YOffset("measure:N"),
    x=alt.X("share:Q", axis=alt.Axis(format="%", title=None)),
    color=alt.Color("measure:N", scale=alt.Scale(range=[data.CONTROL_GREY, color]),
                    legend=alt.Legend(title=None, orient="top", labelLimit=300)),
    tooltip=[alt.Tooltip("name:N", title="Type"), alt.Tooltip("measure:N", title=" "),
             alt.Tooltip("share:Q", format=".0%", title="Share")],
).properties(height=260)
st.altair_chart(chart, width="stretch")
data.how_to_read("Grey bar = the type's share of all households. Coloured bar = its share of the model's top 25% "
                 "gainers. If the coloured bar is longer than the grey one the model also thinks this type gains more.")
