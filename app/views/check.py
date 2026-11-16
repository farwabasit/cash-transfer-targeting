import pandas as pd
import streamlit as st

import data

st.title("Check My Households")
st.markdown(
    "Upload your own list of households from a baseline survey. The tool gives each household a type, "
    "the expected gain from cash (based on the trial results for that type) and picks households "
    "within your budget."
)

REQUIRED = ["household_id", "country", "consumption_pc_ppp", "hh_size"]
with st.expander("File format"):
    st.markdown(
        "A CSV with one row per household and these columns:\n"
        "- `household_id`: your own ID\n"
        "- `country`: `KEN` or `UGA` (the context the results come from)\n"
        "- `consumption_pc_ppp`: monthly consumption per person in PPP dollars\n"
        "- `hh_size`: number of people in the household"
    )
    st.download_button("Download an example file (real trial households)",
                       data.sample_households().to_csv(index=False), "example_households.csv", "text/csv")

up = st.file_uploader("Household file (CSV)", type="csv")
use_example = st.toggle("Use the example file instead", value=up is None)

if up is not None and not use_example:
    try:
        hh = pd.read_csv(up)
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        st.stop()
else:
    hh = data.sample_households()

hh.columns = [c.strip().lower() for c in hh.columns]
missing = [c for c in REQUIRED if c not in hh.columns]
if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()
hh["country"] = hh.country.astype(str).str.upper().str.strip()
for c in ["consumption_pc_ppp", "hh_size"]:
    hh[c] = pd.to_numeric(hh[c], errors="coerce")
bad = hh[~hh.country.isin(data.COUNTRY_NAMES) | hh.consumption_pc_ppp.isna() | (hh.hh_size < 1) | hh.hh_size.isna()]
if len(bad):
    st.warning(f"{len(bad)} rows skipped (unknown country, missing consumption or household size below 1).")
    hh = hh.drop(bad.index)
if hh.empty:
    st.error("No usable rows.")
    st.stop()

countries = sorted(hh.country.unique())
c1, c2, c3 = st.columns(3)
with c1:
    code = st.selectbox("Context", countries, format_func=data.COUNTRY_NAMES.get,
                        help="Results from the two countries use different price bases, so one at a time.")
amounts = data.transfer_amounts()
default_transfer = float(amounts[amounts.country == code].amount_ppp.min())
with c2:
    transfer = st.number_input("Transfer per household (PPP $)", min_value=50.0, value=default_transfer, step=50.0)
with c3:
    budget = st.number_input("Budget (PPP $)", min_value=0.0, value=float(transfer * 10), step=1000.0,
                             help="Default: enough for 10 households.")
priority = st.radio("Who should come first?", ["Most impact per dollar", "Poorest first"], horizontal=True)

hh = hh[hh.country == code].copy()
med = data.medians().set_index("country").loc[code]
eff = data.effects()
eff = eff[(eff.country == code) & (eff.household_type != "ALL")].set_index("household_type")

poorer = hh.consumption_pc_ppp < med.median_consumption_pc_bl
larger = hh.hh_size >= med.median_hh_size_bl
hh["type"] = "A"
hh.loc[poorer & larger, "type"] = "B"
hh.loc[~poorer & ~larger, "type"] = "C"
hh.loc[~poorer & larger, "type"] = "D"
hh["type_label"] = hh.type.map(eff.label)
hh["gain_pc"] = hh.type.map(eff.effect_pc)
hh["gain_household"] = hh.gain_pc * hh.hh_size
hh["gain_per_100"] = 100 * hh.gain_household / transfer
hh["uncertain"] = hh.type.map(eff.ci_low <= 0)

if priority == "Most impact per dollar":
    hh = hh.sort_values(["gain_per_100", "consumption_pc_ppp"], ascending=[False, True])
else:
    hh = hh.sort_values("consumption_pc_ppp")
n_funded = int(min(len(hh), budget // transfer))
hh["selected"] = False
hh.iloc[:n_funded, hh.columns.get_loc("selected")] = True
hh["rank"] = range(1, len(hh) + 1)

sel = hh[hh.selected]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Households funded", f"{len(sel)} of {len(hh)}")
m2.metric("Cost", f"${len(sel) * transfer:,.0f}")
m3.metric("Extra consumption", f"${sel.gain_household.sum():,.0f}/mo",
          help="Sum over funded households of the type's average gain x household size.")
m4.metric("From the poorest half", f"{(sel.consumption_pc_ppp < med.median_consumption_pc_bl).mean():.0%}" if len(sel) else "-")

st.dataframe(hh[["rank", "selected", "household_id", "consumption_pc_ppp", "hh_size", "type", "type_label",
                 "gain_household", "gain_per_100", "uncertain"]],
             hide_index=True, width="stretch", column_config={
                 "rank": "Rank", "selected": "Funded", "household_id": "Household",
                 "consumption_pc_ppp": st.column_config.NumberColumn("Consumption / person", format="$%.0f"),
                 "hh_size": "People", "type": "Type", "type_label": "Household type",
                 "gain_household": st.column_config.NumberColumn("Expected gain / month", format="$%.1f"),
                 "gain_per_100": st.column_config.NumberColumn("Per $100", format="$%.2f"),
                 "uncertain": st.column_config.CheckboxColumn("Uncertain", help="The trial's range for this type includes zero.")})
st.download_button("Download the ranked list", hh.to_csv(index=False), f"ranked_households_{code}.csv", "text/csv")
st.caption(
    "Expected gains are averages for each type from the trials, not a promise for a single household. "
    "Types marked uncertain had a range that includes zero. The trials also showed that results from one "
    "country don't carry over to another, so use the context closest to your programme, and ideally your own data."
)
