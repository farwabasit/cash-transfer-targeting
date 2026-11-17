"""The whole pipeline as one Airflow DAG:

    load raw survey files -> dbt (every model and its tests as tasks, via Cosmos) -> python analysis

Runs locally with the Astro CLI (astro dev start). The repo is mounted at /usr/local/airflow/project,
dbt and the analysis each have their own virtual environment in the image (see airflow/Dockerfile).
GitHub Actions stays the scheduler for the real pipeline. This DAG shows the same steps in Airflow.
"""
from datetime import datetime, timedelta
from pathlib import Path

from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode

try:  # airflow 3
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.sdk import dag
except ImportError:  # airflow 2
    from airflow.decorators import dag
    from airflow.operators.bash import BashOperator

PROJECT = Path("/usr/local/airflow/project")
DBT = "/usr/local/airflow/dbt_venv/bin/dbt"
PY = "/usr/local/airflow/analysis_venv/bin/python"

profile = ProfileConfig(
    profile_name="cash_transfer",
    target_name="dev",
    profiles_yml_filepath=PROJECT / "transform" / "profiles.yml",
)


@dag(
    dag_id="cash_transfer_pipeline",
    schedule="0 6 * * 1",           # mondays, same as the github actions run
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,             # fits in the 3 GB docker gets on my laptop
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},  # a busy laptop can drop a task's status
    tags=["cash-transfer", "dbt", "snowflake"],
    doc_md=__doc__,
)
def cash_transfer_pipeline():
    load_raw = BashOperator(
        task_id="load_raw_files",
        bash_command=f"cd {PROJECT} && {PY} ingestion/load_raw.py",
    )

    dbt = DbtTaskGroup(
        group_id="dbt",
        # read the dbt graph from the manifest (fast). refresh it with: python transform/run_dbt.py parse
        project_config=ProjectConfig(PROJECT / "transform", manifest_path=PROJECT / "transform" / "target" / "manifest.json"),
        profile_config=profile,
        execution_config=ExecutionConfig(dbt_executable_path=DBT),
        render_config=RenderConfig(load_method=LoadMode.DBT_MANIFEST, emit_datasets=False),
        operator_args={"install_deps": False},
    )

    analysis = BashOperator(
        task_id="run_analysis",
        bash_command=f"cd {PROJECT} && {PY} analysis/run_analysis.py",
    )

    load_raw >> dbt >> analysis


cash_transfer_pipeline()
