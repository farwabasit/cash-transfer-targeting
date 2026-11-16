import pandas as pd
import streamlit as st

st.title("How It's Built")
st.markdown("An automated pipeline from raw survey files to this app, built so a new survey wave or a new "
            "country can be added without rewriting anything.")

st.subheader("Medallion Architecture - End to End")
st.code(
    "Survey files (.dta, Harvard Dataverse)\n"
    "  -> Python loader in Docker (skips files already loaded, adds new columns)\n"
    "  -> Snowflake RAW\n"
    "  -> dbt bronze (views)  -> dbt silver (clean, 1 row per household)  -> dbt gold (types, effects, spending)\n"
    "  -> Python analysis (ANCOVA, causal forest, budget simulation) -> Snowflake ML\n"
    "  -> Streamlit app\n"
    "GitHub Actions: dbt build + tests on every push and every Monday",
    language=None)

c1, c2, c3, c4 = st.columns(4)
c1.metric("dbt models", "15")
c2.metric("Data tests", "61")
c3.metric("Seeds", "7")
c4.metric("Contracts", "3")

st.subheader("What Each Layer Does")
st.dataframe(pd.DataFrame([
    ["Raw", "4 survey files land as they are (one read straight from a zip), plus lineage columns (file, hash, wave, loaded at). A load log "
            "makes reruns safe: a file is never loaded twice."],
    ["Bronze", "Views on the raw tables. Source tests: IDs not null, Uganda IDs unique per wave."],
    ["Silver", "Kenya: 2,880 rows -> 1,440 households. Uganda: ~100 survey items with 7-day, 4-week and 12-month "
               "recall turned into one monthly total. Matches the Python prototype exactly (2,354 household-waves)."],
    ["Gold", "Both countries in one table, household types A-D, effect and ROI per type, spending per category."],
    ["ML", "Regression per type, causal forest per household, Kenya -> Uganda check, budget simulation. "
           "Written back to Snowflake for the app."],
], columns=["Layer", "What happens"]), hide_index=True, width="stretch")

st.subheader("Layered Data Quality Testing")
st.markdown(
    "- **61 tests** across all layers: not_null, unique, accepted_values, relationships\n"
    "- **Custom tests**: `in_range` (no negative spending, food share between 0 and 1) and "
    "`unique_combination` (checks the grain of every model)\n"
    "- **Data contracts** on the main household tables: column names and types are fixed\n"
    "- **Reconciliation test**: the dbt SQL is compared with the Python prototype household by household\n"
    "- **Source freshness**: warns if no new survey wave has arrived in a year"
)

st.subheader("Design Decisions")
st.dataframe(pd.DataFrame([
    ["Ingestion", "Python loader in Docker", "Survey files, not an API. Hash log = safe reruns; new columns added, not failed"],
    ["Login", "Key-pair service user", "No password in code; least-privilege role only for this project"],
    ["Cost", "X-Small warehouse, 60 s auto-suspend, resource monitor", "Free trial credits last; nothing runs idle"],
    ["Transformation", "dbt (bronze/silver/gold)", "Version control + tests + lineage + contracts"],
    ["Item list", "Seed file, checked against each wave's columns", "Questionnaires change between waves"],
    ["Orchestration", "GitHub Actions (not Airflow)", "8 GB laptop; one pipeline; runs in the cloud for free"],
    ["Model", "Simple types first, causal forest as a check", "Easy to explain to an NGO; small samples"],
    ["App", "Streamlit on the gold + ML schemas", "NGO can upload its own households"],
], columns=["Decision", "My Choice", "Why"]), hide_index=True, width="stretch")

st.subheader("Scalability & Future Improvements")
st.dataframe(pd.DataFrame([
    ["New survey wave", "Add one line to sources.yml", "Same, plus automatic download from Dataverse"],
    ["New country", "One silver model + seed rows", "Shared item mapping per questionnaire"],
    ["Ingestion", "Manual run / Docker", "Scheduled with Airflow when there are many sources"],
    ["Transformation", "Full refresh (small data)", "Incremental models"],
    ["Model", "Retrained by hand", "Retrained on every new wave, tracked with MLflow"],
], columns=["Dimension", "Current", "At 10x Scale"]), hide_index=True, width="stretch")
