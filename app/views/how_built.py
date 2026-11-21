from pathlib import Path

import pandas as pd
import streamlit as st

st.title("How It's Built")
st.markdown("An automated pipeline from raw survey files to this app, built so a new survey wave or a new "
            "country can be added without rewriting anything.")

st.image(str(Path(__file__).resolve().parents[1] / "static" / "pipeline.png"), width="stretch")

st.subheader("Medallion Architecture - End to End")
st.code(
    "Survey files (.dta, Harvard Dataverse)\n"
    "  -> Python loader in Docker (skips files already loaded, adds new columns)\n"
    "World Bank API (PPP, exchange rates, CPI for 8 countries)\n"
    "  -> API loader (timeouts, retries, merge on country + indicator + year)\n"
    "  -> Snowflake RAW\n"
    "  -> dbt bronze (views)  -> dbt silver (clean, 1 row per household)  -> dbt gold (types, effects, spending)\n"
    "  -> Python analysis (ANCOVA, causal forest, budget simulation) -> Snowflake ML\n"
    "  -> Streamlit app\n"
    "GitHub Actions: dbt build + tests on every branch (in CI_ schemas) and on main every Monday\n"
    "Airflow (Astro + Cosmos): the same steps as one DAG, 39 tasks (every dbt model and test is a task)",
    language=None)

c1, c2, c3, c4 = st.columns(4)
c1.metric("dbt models", "17")
c2.metric("Data tests", "68")
c3.metric("Seeds", "7")
c4.metric("Contracts", "5")

st.page_link("views/dbt_docs.py", label="Open the data catalogue with the lineage graph (dbt docs)",
             icon=":material/menu_book:")

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
    "- **68 tests** across all layers: not_null, unique, accepted_values, relationships\n"
    "- **Custom tests**: `in_range` (no negative spending, food share between 0 and 1) and "
    "`unique_combination` (checks the grain of every model)\n"
    "- **Data contracts** on all 5 gold tables, the layer the app reads: column names and types are fixed\n"
    "- **Reconciliation test**: the dbt SQL is compared with the Python prototype household by household\n"
    "- **Live check**: the PPP factors pinned for the analysis are compared with the World Bank API on every build "
    "(warns above 2%). Pinned for reproducible results, monitored against the live source\n"
    "- **Source freshness**: warns if no new survey wave has arrived in a year"
)

st.subheader("Design Decisions")
st.dataframe(pd.DataFrame([
    ["Ingestion", "Python loader in Docker", "Survey files, not an API. Hash log = safe reruns; new columns added, not failed"],
    ["Login", "Key-pair service user", "No password in code; least-privilege role only for this project"],
    ["Cost", "X-Small warehouse, 60 s auto-suspend, resource monitor", "Free trial credits last; nothing runs idle"],
    ["Transformation", "dbt (bronze/silver/gold)", "Version control + tests + lineage + contracts"],
    ["Item list", "Seed file joined to the survey answers with FLATTEN (plain SQL, no Jinja)",
     "Questionnaires change between waves. A dbt engineer advised Snowflake SQL over Jinja: no extra database call"],
    ["Contracts", "On the gold layer only", "Gold is what the app depends on (advice from the same dbt engineer)"],
    ["Orchestration", "GitHub Actions for the schedule, Airflow DAG with Cosmos as well",
     "Actions runs in the cloud for free. Airflow shows every dbt model as a task with retries; runs locally in Docker"],
    ["Airflow on 8 GB", "Max 2 tasks at a time, 2 retries, dbt read from the manifest",
     "First run overloaded the laptop and dropped 3 task statuses; this fixed it"],
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
