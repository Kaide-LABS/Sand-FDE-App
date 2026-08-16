"""Loads the five checked-in data/*.csv extractions of the Borno PHC baseline
PDF into Postgres' `raw` schema.

Each CSV carries a header block of `#`-prefixed citation comment lines
(exact page/table/figure number transcribed from -- see the files
themselves) which are stripped before parsing. Every row is validated
against its Pydantic model (ingestion/models.py) with
`model_config = ConfigDict(extra="forbid")`; a row that fails validation
raises immediately rather than being skipped -- these five files are the
confirmed, checked-in ground truth (PHASE_1_SPEC.md Sec.1), so a validation
failure here means the CSV was edited incorrectly, not that a row should be
silently dropped (PHASE_1_SPEC.md Sec.6 step 1).

Idempotent: each table is truncated and fully reloaded on every run, since
these are small, static, one-time extractions, not an incremental feed.

# Implements PHASE_1_SPEC.md Sec.1 (ingestion/load_csv.py), Sec.6 step 1.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from psycopg import Connection
from pydantic import BaseModel, ValidationError

from ingestion import config
from ingestion.db import ensure_raw_schema, get_connection
from ingestion.models import (
    LgaCurrentStaffing,
    LgaFacilityCount,
    LgaFacilityDensity,
    NphcdaMinimumStandard,
    StateStaffingGap,
)


def _strip_citation_comments(path: Path) -> list[str]:
    """Return every line of `path` except leading `#`-prefixed citation
    comment lines, ready to hand to `csv.DictReader`.
    """
    with path.open(encoding="utf-8") as f:
        return [line for line in f if not line.lstrip().startswith("#")]


def load_typed_rows[ModelT: BaseModel](path: Path, model: type[ModelT]) -> list[ModelT]:
    """Parse `path` as CSV (after stripping citation comments) and validate
    every row against `model`. Raises `ValueError` on the first row that
    fails Pydantic validation, naming the file and row number.
    """
    lines = _strip_citation_comments(path)
    reader = csv.DictReader(lines)
    rows: list[ModelT] = []
    for raw_row in reader:
        try:
            rows.append(model.model_validate(raw_row))
        except ValidationError as exc:
            raise ValueError(
                f"{path.name}: row failed validation against {model.__name__}: {raw_row!r}\n{exc}"
            ) from exc
    return rows


def _insert_rows(
    conn: Connection,
    table: str,
    columns: Sequence[str],
    rows: Sequence[BaseModel],
) -> None:
    """Truncate `table` and bulk-insert `rows`, reading each row's field
    values in `columns` order.
    """
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {table}")
        if not rows:
            return
        placeholders = ", ".join(["%s"] * len(columns))
        cols_sql = ", ".join(columns)
        cur.executemany(
            f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})",
            [tuple(getattr(row, c) for c in columns) for row in rows],
        )


def load_all() -> dict[str, int]:
    """Load all five CSVs into `raw.*`, returning a dict of table name ->
    row count loaded, for the caller to log or assert against.
    """
    ensure_raw_schema()

    lga_current_staffing = load_typed_rows(config.LGA_CURRENT_STAFFING_CSV, LgaCurrentStaffing)
    state_staffing_gap = load_typed_rows(config.STATE_STAFFING_GAP_CSV, StateStaffingGap)
    lga_facility_count = load_typed_rows(config.LGA_FACILITY_COUNT_CSV, LgaFacilityCount)
    lga_facility_density = load_typed_rows(config.LGA_FACILITY_DENSITY_CSV, LgaFacilityDensity)
    nphcda_minimum_standard = load_typed_rows(
        config.NPHCDA_MINIMUM_STANDARD_CSV, NphcdaMinimumStandard
    )

    with get_connection() as conn:
        _insert_rows(
            conn,
            "raw.lga_current_staffing",
            list(LgaCurrentStaffing.model_fields.keys()),
            lga_current_staffing,
        )
        _insert_rows(
            conn,
            "raw.state_staffing_gap",
            list(StateStaffingGap.model_fields.keys()),
            state_staffing_gap,
        )
        _insert_rows(
            conn,
            "raw.lga_facility_count",
            list(LgaFacilityCount.model_fields.keys()),
            lga_facility_count,
        )
        _insert_rows(
            conn,
            "raw.lga_facility_density",
            list(LgaFacilityDensity.model_fields.keys()),
            lga_facility_density,
        )
        _insert_rows(
            conn,
            "raw.nphcda_minimum_standard",
            list(NphcdaMinimumStandard.model_fields.keys()),
            nphcda_minimum_standard,
        )

    return {
        "raw.lga_current_staffing": len(lga_current_staffing),
        "raw.state_staffing_gap": len(state_staffing_gap),
        "raw.lga_facility_count": len(lga_facility_count),
        "raw.lga_facility_density": len(lga_facility_density),
        "raw.nphcda_minimum_standard": len(nphcda_minimum_standard),
    }


def main() -> int:
    """CLI entry point: load all five CSVs, printing a per-table row count."""
    counts = load_all()
    for table, count in counts.items():
        print(f"Loaded {count} rows into {table}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
