"""queries for the app. reads the GOLD and ML schemas in snowflake, cached for an hour."""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))
import load_raw  # noqa: E402

COUNTRY_NAMES = {"KEN": "Kenya", "UGA": "Uganda"}
COUNTRY_COLORS = {"Kenya": "#2a78d6", "Uganda": "#1baf7a"}
CONTROL_GREY = "#9a9893"


def currency_inputs(key):
    """lets an NGO work in its own currency. returns (currency label, local units per PPP $)"""
    mode = st.radio("Money in my file is in", ["PPP dollars", "Local currency"], horizontal=True, key=f"{key}_mode",
                    help="PPP dollars make prices comparable between countries. If your data is in SEK, KES, UGX "
                         "etc, pick local currency and give the conversion rate.")
    if mode == "PPP dollars":
        return "PPP $", 1.0
    c1, c2 = st.columns(2)
    code = c1.text_input("Currency", value="KES", max_chars=5, key=f"{key}_cur").strip().upper() or "LCU"
    rate = c2.number_input(f"{code} per PPP dollar", min_value=0.0001, value=45.0, step=1.0, key=f"{key}_rate",
                           help="The World Bank publishes this as 'PPP conversion factor, private consumption' "
                                "(PA.NUS.PRVT.PP) for every country and year.")
    return code, float(rate)


def how_to_read(text):
    # short plain-words guide under each chart (Pritha: make it more understandable)
    st.caption(f":material/lightbulb: **How to read this:** {text}")


def question_box(text):
    # the yellow "stakeholder question" box from my Apollo deck
    st.markdown(
        f"<div style='background:#f1d96b;color:#1e2b3c;border-radius:14px;padding:18px 22px;"
        f"font-size:1.25rem;line-height:1.45;margin:6px 0 18px 0'>{text}</div>",
        unsafe_allow_html=True)


def _set_env():
    # streamlit cloud: secrets in [snowflake], locally: .env
    try:
        for k, v in st.secrets.get("snowflake", {}).items():
            os.environ.setdefault(k, str(v))
    except Exception:
        pass
    load_raw.load_dotenv(ROOT / ".env")


@st.cache_data(ttl=3600, show_spinner="Loading from Snowflake...")
def query(sql: str) -> pd.DataFrame:
    _set_env()
    conn = load_raw.connect()
    try:
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()
    df.columns = [c.lower() for c in df.columns]
    if "country" in df:
        df["country_name"] = df.country.map(COUNTRY_NAMES).fillna(df.country)
    return df


def effects():
    df = query("select * from ML.EFFECTS_ANCOVA")
    types = household_types()[["household_type", "label"]]
    df = df.merge(types, on="household_type", how="left")
    df["label"] = df.label.fillna("All households")
    for c in ["ci_low", "ci_high"]:
        df[c + "_pct"] = df[c] / df.control_mean
    return df


def household_types():
    return query("select * from SEEDS.HOUSEHOLD_TYPES order by household_type")


def medians():
    return query("""select country, any_value(median_consumption_pc_bl) as median_consumption_pc_bl,
                           any_value(median_hh_size_bl) as median_hh_size_bl, count(*) as households
                    from GOLD.GLD_HOUSEHOLD_OUTCOMES where in_analysis group by country""")


def spending():
    return query("select * from GOLD.GLD_SPENDING_BY_TYPE")


def budget():
    return query("select * from ML.BUDGET_SIMULATION")


def type_check():
    return query("select * from ML.TYPE_CHECK")


def transfer_check():
    return query("select * from ML.TRANSFER_CHECK")


def transfer_amounts():
    return query("select * from SEEDS.TRANSFER_AMOUNTS")


def example_programme():
    # real Uganda trial households in the format the "own programme" page expects
    return query("""
        select household_id, treated, round(consumption_pc_bl, 4) as consumption_before,
               round(consumption_pc_el, 4) as consumption_after, hh_size_bl as hh_size
        from GOLD.GLD_HOUSEHOLD_OUTCOMES
        where country = 'UGA' and in_analysis and household_type is not null and consumption_pc_el_w is not null
        order by household_id""").drop(columns="country_name", errors="ignore")


def sample_households(n_per_country=25):
    # real households from the trials (baseline values only), as an example upload file
    return query(f"""
        select household_id, country, round(consumption_pc_bl_w, 2) as consumption_pc, hh_size_bl as hh_size
        from GOLD.GLD_HOUSEHOLD_OUTCOMES
        where in_analysis and household_type is not null
        qualify row_number() over (partition by country order by hash(household_id)) <= {n_per_country}
        order by country, household_id""").drop(columns="country_name", errors="ignore")
