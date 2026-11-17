FROM astrocrpublic.azurecr.io/runtime:3.4-1

# dbt in its own virtual environment so its packages can't clash with airflow's
RUN python -m venv dbt_venv && dbt_venv/bin/pip install --no-cache-dir \
    dbt-core==1.12.7 dbt-snowflake==1.12.5

# loader + analysis in another one (same versions as requirements-ingest.txt / requirements-analysis.txt)
RUN python -m venv analysis_venv && analysis_venv/bin/pip install --no-cache-dir \
    pandas==3.1.1 "snowflake-connector-python[pandas]==5.2.0" cryptography==50.0.2 pyyaml==6.0.3 \
    statsmodels==0.15.0 econml==0.17.0 scikit-learn==1.9.1
