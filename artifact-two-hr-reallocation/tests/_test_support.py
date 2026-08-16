"""Shared test-only helper: builds a full `MartReallocationInputRow` list
directly from the checked-in `data/*.csv` files, without touching
Postgres/dbt, so tests/test_zero_sum.py, tests/test_floor_constraint.py, and
tests/test_variance_improved.py can each independently run the optimizer
end-to-end and recompute its acceptance criteria without needing a live
database. Not a test module itself -- deliberately not prefixed `test_`, so
pytest does not try to collect it.

Not part of PHASE_1_SPEC.md Sec.1's file list; added as a test-support
helper to avoid duplicating this CSV-to-mart-row derivation across four
different test files (see AUTONOMOUS CRITIQUE).
"""

from __future__ import annotations

from ingestion import config
from ingestion.load_csv import load_typed_rows
from ingestion.models import LgaCurrentStaffing, LgaFacilityCount, LgaFacilityDensity
from optimizer.models import MartReallocationInputRow


def build_mart_rows_from_csv() -> list[MartReallocationInputRow]:
    """Replicate warehouse/dbt/models/marts/mart_reallocation_input.sql's
    join and population-proxy derivation in pure Python, reading straight
    from data/*.csv -- the same checked-in ground truth the dbt model
    itself reads from (via raw.*), just without requiring Postgres/dbt to
    be running for the test suite.
    """
    staffing = {
        r.lga: r for r in load_typed_rows(config.LGA_CURRENT_STAFFING_CSV, LgaCurrentStaffing)
    }
    facility_counts = {
        r.lga: r for r in load_typed_rows(config.LGA_FACILITY_COUNT_CSV, LgaFacilityCount)
    }
    densities = {
        r.lga: r for r in load_typed_rows(config.LGA_FACILITY_DENSITY_CSV, LgaFacilityDensity)
    }

    rows: list[MartReallocationInputRow] = []
    for lga, staffing_row in staffing.items():
        facility_row = facility_counts.get(lga)
        density_row = densities.get(lga)
        if facility_row is None or density_row is None:
            continue
        if density_row.density_per_10k_population <= 0:
            continue
        population_proxy = (
            facility_row.facility_count / density_row.density_per_10k_population * 10000
        )
        rows.append(
            MartReallocationInputRow(
                lga=lga,
                community_health_officer=staffing_row.community_health_officer,
                community_health_extension_worker=staffing_row.community_health_extension_worker,
                junior_community_health_extension_worker=(
                    staffing_row.junior_community_health_extension_worker
                ),
                nurse_midwife=staffing_row.nurse_midwife,
                grand_total=staffing_row.grand_total,
                population_proxy=population_proxy,
                ratio=staffing_row.grand_total / population_proxy,
            )
        )
    return rows
