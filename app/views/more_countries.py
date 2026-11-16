import altair as alt
import streamlit as st

import data

st.title("Is There One Rule for Who Gains Most?")
st.markdown(
    "We looked at **8 places**: the two cash trials (Kenya and Uganda) and six countries of the **graduation "
    "programme** (Banerjee et al. 2015): Ethiopia, Ghana, Honduras, India, Pakistan and Peru. In each place we split "
    "households into the poorer half and the less poor half and tested if one half gained more."
)
st.warning(
    "**Graduation is a different programme:** families got an asset like livestock, a food stipend for some months "
    "and training. Not unconditional cash. So we compare the pattern of who gains, not the exact numbers.",
    icon=":material/compare_arrows:")

pv = data.query("select * from ML.POORER_VS_LESS_POOR")
pv["clear"] = pv.difference_p_value < 0.05
long = pv.melt(id_vars=["place", "programme", "who_gains_more", "clear"],
               value_vars=["gain_pct_poorer", "gain_pct_less_poor"], var_name="half", value_name="gain")
long["half"] = long.half.map({"gain_pct_poorer": "Poorer half", "gain_pct_less_poor": "Less poor half"})
order = list(pv.sort_values(["programme", "place"]).place)

st.subheader("Poorer Half or Less Poor Half?")
st.caption("Gain in consumption per person vs households without support, after about 1-2 years. "
           "The test in the last column checks if the two halves really differ.")
halves = alt.Scale(domain=["Poorer half", "Less poor half"], range=[data.COUNTRY_COLORS["Kenya"], data.COUNTRY_COLORS["Uganda"]])
tip = [alt.Tooltip("place:N", title="Place"), alt.Tooltip("half:N", title=" "),
       alt.Tooltip("gain:Q", title="Gain", format="+.0%"), alt.Tooltip("who_gains_more:N", title="Who gains more")]
y = alt.Y("place:N", sort=order, title=None, axis=alt.Axis(labelLimit=200))
line = alt.Chart(long).mark_line(color=data.CONTROL_GREY, strokeWidth=2).encode(y=y, x="gain:Q", detail="place:N")
dots = alt.Chart(long).mark_circle(size=120, opacity=1).encode(
    y=y, x=alt.X("gain:Q", axis=alt.Axis(format="%", title="Gain in consumption per person")),
    color=alt.Color("half:N", scale=halves, legend=alt.Legend(title=None, orient="top")), tooltip=tip)
zero = alt.Chart().mark_rule(color=data.CONTROL_GREY, strokeDash=[4, 4]).encode(x=alt.datum(0))
st.altair_chart((zero + line + dots).properties(height=330), width="stretch")

st.dataframe(pv.sort_values(["programme", "place"])[["place", "programme", "n", "gain_pct_poorer", "gain_pct_less_poor",
                                                      "who_gains_more", "difference_p_value"]],
             hide_index=True, width="stretch", column_config={
                 "place": "Place", "programme": "Programme", "n": "Households",
                 "gain_pct_poorer": st.column_config.NumberColumn("Poorer half", format="percent"),
                 "gain_pct_less_poor": st.column_config.NumberColumn("Less poor half", format="percent"),
                 "who_gains_more": "Who gains more",
                 "difference_p_value": st.column_config.NumberColumn("p-value of the difference", format="%.3f")})

st.subheader("All 8 Places Together")
meta = data.query("select * from ML.POOLED_META")
bp = data.query("select * from ML.POOLED_BY_PLACE")
allgap = meta[(meta.subset == "All 8 places") & (meta.measure == "Poorer minus less poor")].iloc[0]
allgain = meta[(meta.subset == "All 8 places") & (meta.measure == "Overall gain")].iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Households", f"{int(allgap.households):,}")
c2.metric("Average gain", f"+{allgain.random:.0%}", help=f"95% range {allgain.ci_low:+.0%} to {allgain.ci_high:+.0%}")
c3.metric("Poorer minus less poor", f"{allgap.random * 100:+.1f} points",
          help=f"95% range {allgap.ci_low * 100:+.1f} to {allgap.ci_high * 100:+.1f} points")
st.markdown(
    "Each place is put on the same scale (gain as a share of its own comparison group's consumption) and the "
    "8 results are combined, giving more weight to the more precise ones (a meta-analysis)."
)
bp["low"], bp["high"] = bp.gap - 1.96 * bp.gap_se, bp.gap + 1.96 * bp.gap_se
forest = bp[["place", "gap", "low", "high"]].copy()
forest.loc[len(forest)] = ["All 8 places", allgap.random, allgap.ci_low, allgap.ci_high]
forest["kind"] = ["Place"] * (len(forest) - 1) + ["Combined"]
order_f = list(bp.sort_values("gap").place) + ["All 8 places"]
tip_f = [alt.Tooltip("place:N", title="Place"), alt.Tooltip("gap:Q", title="Gap", format="+.1%"),
         alt.Tooltip("low:Q", title="Range from", format="+.1%"), alt.Tooltip("high:Q", title="Range to", format="+.1%")]
kinds = alt.Scale(domain=["Place", "Combined"], range=[data.CONTROL_GREY, data.COUNTRY_COLORS["Kenya"]])
yf = alt.Y("place:N", sort=order_f, title=None, axis=alt.Axis(labelLimit=200))
fp = (zero
      + alt.Chart(forest).mark_rule(strokeWidth=2).encode(
          y=yf, x=alt.X("low:Q", axis=alt.Axis(format="%", title="Extra gain for the poorer half (left = less poor gain more)")),
          x2="high:Q", color=alt.Color("kind:N", scale=kinds, legend=None), tooltip=tip_f)
      + alt.Chart(forest).mark_point(filled=True, size=140, opacity=1).encode(
          y=yf, x="gap:Q", shape=alt.Shape("kind:N", scale=alt.Scale(domain=["Place", "Combined"], range=["circle", "diamond"]),
                                           legend=None),
          color=alt.Color("kind:N", scale=kinds, legend=None), tooltip=tip_f))
st.altair_chart(fp.properties(height=330), width="stretch")
st.success(
    f"**On average the poorer and the less poor half gained about the same.** Across {int(allgap.households):,} "
    f"households the gap is {allgap.random * 100:+.1f} points. The 95% range ({allgap.ci_low * 100:+.1f} to "
    f"{allgap.ci_high * 100:+.1f}) rules out big differences either way. The programmes themselves worked: "
    f"+{allgain.random:.0%} on average, more for cash than for graduation.",
    icon=":material/check_circle:")

st.subheader("What It Means")
st.markdown(
    f"- **Only {int(pv.clear.sum())} of {len(pv)} places show a clear difference:** in Uganda the less poor half "
    "gained more. Everywhere else the two halves can't be told apart.\n"
    "- **On average the two halves gain the same:** combined over all 8 places the gap is close to zero.\n"
    "- **So giving to the poorest costs no impact on average:** the poorest gain as much as the less poor. "
    "But a single place (like Uganda) can be different. A rule can't be copied blindly.\n"
    "- **That's why local data matters:** a programme should test its own households. The page *Analyse my own "
    "programme* does exactly that."
)

st.subheader("Did the Graduation Programme Work?")
g = data.query("select * from ML.GRADUATION_EFFECTS where \"GROUP\" = 'ALL'")
g["ci_low_pct"], g["ci_high_pct"] = g.ci_low / g.control_mean, g.ci_high / g.control_mean
waves = alt.Scale(domain=["about 2 years", "about 3 years"], range=[data.COUNTRY_COLORS["Kenya"], data.COUNTRY_COLORS["Uganda"]])
tip_g = [alt.Tooltip("country_name:N", title="Country"), alt.Tooltip("wave:N", title="After"),
         alt.Tooltip("effect_pct:Q", title="Gain", format="+.0%"),
         alt.Tooltip("ci_low_pct:Q", title="Range from", format="+.0%"),
         alt.Tooltip("ci_high_pct:Q", title="Range to", format="+.0%"),
         alt.Tooltip("gain_per_100_total_cost:Q", title="Per $100 total cost", format="$.2f")]
base = alt.Chart(g).encode(y=alt.Y("country_name:N", title=None), yOffset=alt.YOffset("wave:N"),
                           color=alt.Color("wave:N", scale=waves, legend=alt.Legend(title="Measured after", orient="top")))
st.altair_chart((zero + base.mark_rule(strokeWidth=2).encode(
    x=alt.X("ci_low_pct:Q", axis=alt.Axis(format="%", title="Gain in consumption per person (95% range)")),
    x2="ci_high_pct:Q", tooltip=tip_g) + base.mark_circle(size=100, opacity=1).encode(x="effect_pct:Q", tooltip=tip_g)
).properties(height=330), width="stretch")
st.markdown(
    "- **It worked clearly in Ethiopia (+16%), India (+12%) and Pakistan (+10%)** after about 2 years.\n"
    "- **Not in Honduras.** Unclear in Ghana and Peru (Peru turned positive by year 3).\n"
    "- **Expensive per result:** each $100 of total cost gave $0 to $1.80 extra monthly consumption, against $3.85 "
    "(Kenya) and $7.56 (Uganda) for cash. Graduation also builds assets and skills, which this number doesn't count."
)
st.caption("Money in 2014 PPP dollars. Average household size per country from the paper's cost table, because "
           "the file has no size per household. Ghana, Honduras and Peru also had control villages.")
