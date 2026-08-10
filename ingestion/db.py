"""Postgres connection helper shared by the ingestion scripts.

Connection settings come entirely from environment variables so the same code
runs unmodified against the docker-compose Postgres service or against a
locally-installed one. No secrets are hard-coded.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://katsina:katsina@localhost:5442/katsina_data_quality",
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    conn = psycopg.connect(database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


RAW_SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.msdat_indicator_values (
    record_id BIGINT NOT NULL,
    indicator_id INTEGER NOT NULL,
    indicator_name TEXT NOT NULL,
    datasource_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    lga_name TEXT NOT NULL,
    period TEXT NOT NULL,
    year INTEGER NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    msdat_updated_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (record_id, fetched_at)
);

CREATE TABLE IF NOT EXISTS raw.grid3_lga_population (
    state TEXT NOT NULL,
    lga_name TEXT NOT NULL,
    population_mean DOUBLE PRECISION NOT NULL,
    population_q025 DOUBLE PRECISION NOT NULL,
    population_q975 DOUBLE PRECISION NOT NULL,
    source_label TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (lga_name, fetched_at)
);
"""


def ensure_raw_schema() -> None:
    with get_connection() as conn:
        conn.execute(RAW_SCHEMA_DDL)
