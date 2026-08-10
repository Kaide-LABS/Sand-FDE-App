"""Katsina LGA data-toxicity audit -- on-demand DAG.

`schedule=None`: this DAG is triggered by hand (CLI `airflow dags trigger` or
the web UI's "Trigger DAG" button). It is not a continuously-running scheduled
service -- that is a deliberate scope boundary (see README.md), not an
oversight.

Task order: fetch_msdat and fetch_grid3 run in parallel (independent data
sources), both must finish before dbt_seed, which loads the small reference
tables the dbt models join against, followed by dbt_run (builds every
staging/intermediate/mart model), dbt_test (runs the two constraint tests --
severity=warn, so a "failing" test here means "toxic LGAs were found", which
is the pipeline doing its job, not an error -- see warehouse/dbt/tests/), and
finally generate_report (renders the ranked audit list to a static HTML file).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

PROJECT_ROOT = "/opt/airflow/project"
DBT_DIR = f"{PROJECT_ROOT}/warehouse/dbt"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DBT_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "PGHOST": "postgres",
    "PGPORT": "5432",
    "PGUSER": "katsina",
    "PGPASSWORD": "katsina",
    "PGDATABASE": "katsina_data_quality",
    "DATABASE_URL": "postgresql://katsina:katsina@postgres:5432/katsina_data_quality",
}


def _run_fetch_msdat() -> None:
    from ingestion.fetch_msdat import main as fetch_msdat_main

    exit_code = fetch_msdat_main()
    if exit_code != 0:
        raise RuntimeError(f"ingestion.fetch_msdat exited with code {exit_code}")


def _run_fetch_grid3() -> None:
    from ingestion.fetch_grid3 import main as fetch_grid3_main

    exit_code = fetch_grid3_main()
    if exit_code != 0:
        raise RuntimeError(f"ingestion.fetch_grid3 exited with code {exit_code}")


with DAG(
    dag_id="katsina_data_toxicity_audit",
    description="Deterministic LGA data-toxicity audit for Katsina State (on demand only).",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["katsina", "data-quality", "on-demand"],
) as dag:
    fetch_msdat = PythonOperator(
        task_id="fetch_msdat",
        python_callable=_run_fetch_msdat,
    )

    fetch_grid3 = PythonOperator(
        task_id="fetch_grid3",
        python_callable=_run_fetch_grid3,
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_DIR} && dbt seed --profiles-dir {DBT_DIR}",
        env=DBT_ENV,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir {DBT_DIR}",
        env=DBT_ENV,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir {DBT_DIR}",
        env=DBT_ENV,
    )

    generate_report = BashOperator(
        task_id="generate_report",
        bash_command=f"cd {PROJECT_ROOT} && python -m viz.generate_report",
        env=DBT_ENV,
    )

    [fetch_msdat, fetch_grid3] >> dbt_seed >> dbt_run >> dbt_test >> generate_report
