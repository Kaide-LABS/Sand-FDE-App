"""Borno State PHC Worker Reallocation Optimizer -- on-demand DAG.

`schedule=None`: this DAG is triggered by hand (CLI `airflow dags trigger` or
the web UI's "Trigger DAG" button). The ingestion is a one-time PDF
extraction, not a live pull, and the optimizer runs once against a static
dataset -- there is nothing for a schedule to re-run against
(ULTIMATE_PRD.md Sec.7). Matches
../artifact-one-data-quality/airflow/dags/katsina_data_toxicity_dag.py's own
on-demand pattern exactly.

Task order: load_csv (ingestion/load_csv.py, loads the five checked-in
data/*.csv files into raw.*) -> dbt_seed (a structural no-op in this
project -- warehouse/dbt/seeds/ is deliberately empty, PHASE_1_SPEC.md
Sec.1: these CSVs need the citation-comment stripping load_csv.py does,
which a plain dbt seed load does not do -- kept in the task chain only to
mirror the sibling project's DAG shape) -> dbt_run (builds every
staging/marts model) -> dbt_test (runs the schema tests plus the population-
proxy reconciliation and row-count singular tests) -> optimize (runs the
MILP formulate/solve/verify pipeline, optimizer/main.py) -> generate_report
(renders the static HTML transfer proposal, viz/generate_report.py).

# Implements PHASE_1_SPEC.md Sec.1 (airflow/dags/), Sec.6.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

PROJECT_ROOT = "/opt/airflow/project"
DBT_DIR = f"{PROJECT_ROOT}/warehouse/dbt"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DBT_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "PGHOST": "postgres",
    "PGPORT": "5432",
    "PGUSER": "borno",
    "PGPASSWORD": "borno",
    "PGDATABASE": "borno_hr_reallocation",
    # Container-local scratch paths -- see warehouse/dbt/dbt_project.yml for
    # why these can't just live under the bind-mounted project directory.
    "DBT_TARGET_PATH": "/tmp/dbt_target",
    "DBT_LOG_PATH": "/tmp/dbt_logs",
    "DATABASE_URL": "postgresql://borno:borno@postgres:5432/borno_hr_reallocation",
}


def _run_load_csv() -> None:
    from ingestion.load_csv import main as load_csv_main

    exit_code = load_csv_main()
    if exit_code != 0:
        raise RuntimeError(f"ingestion.load_csv exited with code {exit_code}")


def _run_optimizer() -> None:
    from optimizer.main import main as optimizer_main

    exit_code = optimizer_main()
    if exit_code != 0:
        raise RuntimeError(f"optimizer.main exited with code {exit_code}")


def _run_generate_report() -> None:
    from viz.generate_report import main as generate_report_main

    exit_code = generate_report_main()
    if exit_code != 0:
        raise RuntimeError(f"viz.generate_report exited with code {exit_code}")


with DAG(
    dag_id="borno_hr_reallocation",
    description="Deterministic MILP-based PHC worker reallocation optimizer for Borno State (on demand only).",
    schedule=None,
    start_date=datetime(2026, 1, 1),  # noqa: DTZ001 -- Airflow's own convention: a DAG's
    # start_date is a naive scheduling anchor (this DAG has schedule=None and is only ever
    # triggered by hand), not a real timestamp instant -- matches
    # ../artifact-one-data-quality/airflow/dags/katsina_data_toxicity_dag.py exactly.
    catchup=False,
    tags=["borno", "hr-reallocation", "on-demand"],
) as dag:
    load_csv = PythonOperator(
        task_id="load_csv",
        python_callable=_run_load_csv,
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

    optimize = PythonOperator(
        task_id="optimize",
        python_callable=_run_optimizer,
    )

    generate_report = PythonOperator(
        task_id="generate_report",
        python_callable=_run_generate_report,
    )

    load_csv >> dbt_seed >> dbt_run >> dbt_test >> optimize >> generate_report
