import pandas as pd
import streamlit as st

import data

st.title("The Programme Manager's View: Who Gains Most from Cash?")

st.subheader("Stakeholder Question")
data.question_box(
    "We have a fixed budget and more poor households than we can reach. "
    "Which households should get cash so the money does the most good?")

st.subheader("Who Is This For?")
st.markdown(
    "**Programme managers and funders of cash programmes** (NGOs like GiveDirectly, Rädda Barnen, the Red Cross, "
    "and funders like Sida, Postkodlotteriet and the IKEA Foundation).\n\n"
    "- **Before:** they choose households by need only, and can't say what each $100 achieves for different households.\n"
    "- **With this tool:** they see which household types gain most, what the trade-off with reaching the poorest is, "
    "and can rank their own household list within their budget."
)

st.subheader("Supporting Questions")
st.markdown(
    "- How much does cash raise consumption, and what does each $100 buy?\n"
    "- Which types of households gain the most, and is it the same everywhere?\n"
    "- What do households spend the extra money on?\n"
    "- If we target the households that gain most, what happens to the poorest?"
)

eff = data.effects()
med = data.medians()
overall = eff[eff.household_type == "ALL"].set_index("country")
cols = st.columns(4)
for col, c in zip(cols[:2], ["KEN", "UGA"]):
    r = overall.loc[c]
    col.metric(f"{data.COUNTRY_NAMES[c]} gain", f"+{r.effect_pct:.0%}",
               help=f"Monthly consumption per person, cash vs no cash, controlling for baseline (ANCOVA). "
                    f"95% range ${r.ci_low:.1f} to ${r.ci_high:.1f} per person.")
for col, c in zip(cols[2:], ["KEN", "UGA"]):
    r = overall.loc[c]
    col.metric(f"{data.COUNTRY_NAMES[c]} per $100", f"${r.monthly_gain_per_100:.2f}",
               help="Extra household consumption per month for every $100 transferred (PPP $).")

st.subheader("The Data")
st.markdown(
    f"**{int(med.households.sum()):,} households** from two randomised GiveDirectly trials. "
    "Grain: one row per household, measured before (baseline) and after (endline) the cash."
)
st.dataframe(pd.DataFrame([
    ["Kenya", "2011-2012", "Rural villages", "1,440 households, 1,008 in analysis", "$404 or $1,525", "Haushofer & Shapiro"],
    ["Uganda", "2019-2022", "Kiryandongo refugee settlement", "1,264 households, 1,090 in analysis", "$1,000 (= $2,848 PPP)", "IDinsight"],
], columns=["Country", "Years", "Where", "Households", "Transfer", "Source"]), hide_index=True, width="stretch")
st.caption("Measure: monthly consumption per person in PPP dollars (food, fuel, health, school and more).")

st.subheader("Data Quality Checks")
st.dataframe(pd.DataFrame([
    ["Kenya: 2 rows per household", "1,440", "One row per respondent (wife and husband). Only the wellbeing scores differ, so we keep one row."],
    ["Kenya: pure control has no baseline", "432", "These villages were only surveyed at the end. The file stored 0, we set it to missing and use the untreated households in treated villages as control."],
    ["Uganda: food list changed between surveys", "12 items", "Rice and pineapple added, 'other' groups removed. Fine for cash vs no cash, risky for before vs after."],
    ["Uganda: very high values per person", "4", "One-person households with very high spending. Capped at the top 1%."],
    ["Uganda: control got cash anyway", "~12%", "Compared by the group they were assigned to (intention to treat)."],
], columns=["Check", "Rows", "Likely reason / how handled"]), hide_index=True, width="stretch")

st.subheader("Insights")
st.markdown(
    "- **Cash works in both places:** consumption per person +17% in Kenya and +13% in Uganda.\n"
    "- **Who gains most is opposite in the two countries:** in Kenya the poorer, larger households gain most "
    "(+27%), in Uganda the less poor households do (+21% and +27%).\n"
    "- **Targeting by type pays off in Uganda:** $11.80 extra per month for every $100, against about $2 when "
    "picking at random.\n"
    "- **But it skips the poorest:** only 19% of the households it picks come from the poorest half.\n"
    "- **A model from one country doesn't work in the other:** Kenya's model could not find Uganda's top gainers."
)

st.subheader("Recommendations")
st.markdown(
    "- **Use your own local data:** who benefits depends on the context, so run the pipeline on your own baseline survey.\n"
    "- **Decide the trade-off openly:** more impact per dollar or reaching the poorest first. Show both numbers to the board.\n"
    "- **Use simple types, not single scores:** type rules are easy to explain and a machine learning model agreed with them."
)

with st.expander("Limitations"):
    st.dataframe(pd.DataFrame([
        ["Small groups", "Some types have 70-80 households per arm", "Every result has a 95% range; we don't claim effects when the range crosses 0"],
        ["Different price bases", "Kenya uses the paper's PPP, Uganda current PPP", "Compare households within a country, not across"],
        ["Kenya control group", "Pure control villages have no baseline", "Untreated households in treated villages used as control"],
        ["Short follow-up", "Endline 9 months (Kenya) to ~19 months (Uganda) after cash", "Results are short to medium term only"],
        ["Old data", "Kenya 2011-12", "Behaviour responds slowly; money values adjusted with PPP; Uganda adds recent data"],
    ], columns=["Limitation", "Evidence", "How we handled it"]), hide_index=True, width="stretch")
