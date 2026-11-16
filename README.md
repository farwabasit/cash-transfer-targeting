# Who Can Rise the Most

**Live app: [cash-transfer-targeting.streamlit.app](https://cash-transfer-targeting.streamlit.app)**

Which types of poor households gain the most from unconditional cash transfers? How can a programme with a fixed budget do the most good?

Final individual project, Data Analyst programme, Hyper Island, Stockholm (Nov 2026).

## The problem
NGOs and funders that give cash have a fixed budget and more poor households than they can reach. This project uses open data from randomised GiveDirectly trials in Kenya (2011-12) and Uganda (2019-22) to group households into four simple types. It measures how much each type gains and what each $100 buys. A graduation programme in Pakistan is added as a comparison.

## What I found
- Cash raised consumption per person by about 17% in Kenya and 13% in Uganda.
- In Kenya the poorer, larger households gained most. In Uganda the less poor did. Pakistan looked like Kenya.
- Targeting by type in Uganda gave about 5x more per dollar than random, but reached far fewer of the poorest.
- A model trained on Kenya could not find Uganda's top gainers. Programmes need their own local data.

## Architecture
```
Dataverse files (.dta, also read from inside zips)
  -> Python loader (Docker) -> Snowflake RAW
  -> dbt: bronze -> silver -> gold   (59 tests, data contracts)
  -> Python analysis (ANCOVA, causal forest with EconML, budget simulation) -> Snowflake ML
  -> Streamlit app (read-only Snowflake user)
CI/CD: GitHub Actions runs dbt build + tests on every push and every Monday
```

The pipeline is built for new survey waves. Every file is loaded once (tracked by hash in `RAW._LOAD_LOG`). New columns in a later wave are added to the table instead of breaking the load.

## Repository layout
| Folder | What |
|---|---|
| `ingestion/` | Loader that lands raw survey files in Snowflake, source list, key-pair helper |
| `snowflake/` | Setup SQL: warehouse, database, roles, service users, cost limit |
| `transform/` | dbt project (bronze / silver / gold), seeds and custom tests |
| `analysis/` | Effects per household type, causal forest, budget simulation, Pakistan |
| `app/` | Streamlit app |
| `prototypes/` | First Python version of the Uganda consumption total (the dbt model is checked against it) |
| `scripts/` | Check that dbt matches the prototype |

## Data
Not included in the repo. Download into `data/raw/`:
- Kenya: Haushofer & Shapiro, GiveDirectly UCT, Harvard Dataverse doi:10.7910/DVN/M2GAZN (CC0)
- Uganda: IDinsight, GiveDirectly Kiryandongo UCT, Harvard Dataverse doi:10.7910/DVN/XBVYXA (CC0)
- Pakistan: Banerjee et al. (2015), graduation programme in 6 countries, Harvard Dataverse doi:10.7910/DVN/NHIXNT (CC0)

## Run it
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python ingestion/load_raw.py --dry-run      # check files, no Snowflake needed
python ingestion/load_raw.py                # load into Snowflake RAW
python transform/run_dbt.py build           # dbt models + tests
```
Analysis and app:
```bash
pip install -r requirements-analysis.txt
python analysis/run_analysis.py             # results -> Snowflake ML schema
pip install -r requirements-app.txt
streamlit run app/streamlit_app.py
```
With Docker:
```bash
docker build -t ct-ingest .
docker run --rm --env-file .env -v "${PWD}/data:/app/data:ro" -v "${PWD}/.secrets:/app/.secrets:ro" ct-ingest
```
Secrets (`.env` and the `.secrets/` key folder) stay on your machine and are git-ignored.

## Limitations
- Small groups: some types have 70-80 households per arm. Every result has a 95% range.
- Kenya and Uganda use different PPP bases. Compare households within a country.
- Kenya's control group is the households in treated villages that did not get cash.
- Pakistan is a different programme (asset + food stipend + training). It is a comparison only.
