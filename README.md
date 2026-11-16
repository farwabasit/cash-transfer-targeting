# Cash Transfer Targeting

Which types of poor households gain the most from unconditional cash transfers, and how can a programme with a fixed budget reach more people out of poverty?

> **Status:** in development (final individual project, Data Analyst programme, Hyper Island, Nov 2026).

## The problem
NGOs and funders that give unconditional cash transfers have a fixed budget and more eligible households than they can reach. This project uses open data from randomised GiveDirectly trials in Kenya (2011-12) and Uganda (2019-22) to group households into a few explainable types, measure how much each type gains from cash, and turn that into a targeting tool for programme teams.

## Architecture
```
Dataverse files (.dta) ──► Python loader (Docker) ──► Snowflake RAW
                                                         │
                                         dbt: bronze ► silver ► gold  (tests, contracts)
                                                         │
                               analysis + model (EconML) ► Streamlit targeting tool
Orchestration: GitHub Actions schedule (Airflow DAG with Cosmos for local runs)
```

The pipeline is **designed for new survey waves**: every file is loaded once (tracked by hash in `RAW._LOAD_LOG`), and new columns in a later wave are added to the table instead of breaking the load.

## Repository layout
| Folder | What |
|---|---|
| `ingestion/` | Loader that lands raw survey files in Snowflake, source list, key-pair helper |
| `snowflake/` | One-off setup SQL (warehouse, database, role, service user, cost guard) |
| `transform/` | dbt project (bronze / silver / gold) |
| `prototypes/` | Python prototype of the Uganda consumption aggregate (reference for dbt tests) |

## Data
Not included in the repo. Download into `data/raw/`:
- Kenya: Haushofer & Shapiro, GiveDirectly UCT, Harvard Dataverse doi:10.7910/DVN/M2GAZN (CC0)
- Uganda: IDinsight, GiveDirectly Kiryandongo UCT, Harvard Dataverse doi:10.7910/DVN/XBVYXA (CC0)

## Run it
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python ingestion/load_raw.py --dry-run      # check files, no Snowflake needed
python ingestion/load_raw.py                # load into Snowflake RAW
```
Analysis and app:
```bash
pip install -r requirements-analysis.txt
python analysis/run_analysis.py             # ANCOVA, causal forest, budget simulation -> Snowflake ML schema
pip install -r requirements-app.txt
streamlit run app/streamlit_app.py
```
With Docker:
```bash
docker build -t ct-ingest .
docker run --rm --env-file .env -v "${PWD}/data:/app/data:ro" -v "${PWD}/.secrets:/app/.secrets:ro" ct-ingest
```
