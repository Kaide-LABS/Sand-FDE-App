"""Postgres connection helper shared by ingestion and the optimizer.

Connection settings come entirely from environment variables so the same
code runs unmodified against the docker-compose Postgres service or a
locally-installed one. No secrets are hard-coded -- these are the same class
of fixed, non-secret local-development credentials
../artifact-one-data-quality/ingestion/db.py already documents in plaintext
for local-only use.

`raw` schema DDL only, matching PHASE_1_SPEC.md Sec.5: `stg`/`marts` schemas
are created by dbt's own model materialization, not here.

# Implements PHASE_1_SPEC.md Sec.1 (ingestion/db.py), Sec.5.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection


def database_url() -> str:
    """Return the Postgres connection string, defaulting to the local
    docker-compose service's own fixed, non-secret credentials.
    """
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://borno:borno@localhost:5443/borno_hr_reallocation",
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Yield a psycopg connection, committing on success and rolling back on
    any exception raised inside the `with` block.
    """
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

CREATE TABLE IF NOT EXISTS raw.lga_current_staffing (
    lga TEXT PRIMARY KEY,
    community_health_officer INTEGER NOT NULL,
    community_health_extension_worker INTEGER NOT NULL,
    junior_community_health_extension_worker INTEGER NOT NULL,
    health_information_management INTEGER NOT NULL,
    medical_doctor INTEGER NOT NULL,
    medical_laboratory_scientist INTEGER NOT NULL,
    nurse_midwife INTEGER NOT NULL,
    pharmacist INTEGER NOT NULL,
    total_core_health_workers INTEGER NOT NULL,
    total_support_health_workers INTEGER NOT NULL,
    grand_total INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.state_staffing_gap (
    phc_personnel TEXT PRIMARY KEY,
    minimum_no_per_phc INTEGER NOT NULL,
    total_required_across_state INTEGER NOT NULL,
    total_available_across_state INTEGER NOT NULL,
    gap_across_state INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.lga_facility_count (
    lga TEXT PRIMARY KEY,
    facility_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.lga_facility_density (
    lga TEXT PRIMARY KEY,
    density_per_10k_population DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.nphcda_minimum_standard (
    minimum_standard TEXT PRIMARY KEY,
    minimum_no_per_phc INTEGER NOT NULL
);
"""


def ensure_raw_schema() -> None:
    """Create the `raw` schema and its five tables if they do not already exist."""
    with get_connection() as conn:
        conn.execute(RAW_SCHEMA_DDL)
