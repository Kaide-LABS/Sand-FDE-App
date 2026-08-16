"""Asserts the checked-in data/*.csv files' own internal sums and row counts
match the documented expected values (ingestion/config.py) -- catches an
accidental future edit to data/*.csv silently breaking agreement with the
PDF's own totals (ULTIMATE_PRD.md Sec.2 finding 9, Sec.3.1).

This does not re-derive the expected values from the PDF -- the CSVs are
the confirmed, checked-in ground truth (PHASE_1_SPEC.md Sec.1); it only
guards against a *future* edit silently drifting from what was checked in.

Run directly: `python -m tests.test_csv_sums`
Or via pytest: `pytest tests/test_csv_sums.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_csv_sums.py).
"""

from __future__ import annotations

import sys

from ingestion import config
from ingestion.load_csv import load_typed_rows
from ingestion.models import LgaCurrentStaffing, LgaFacilityCount, StateStaffingGap


def test_lga_current_staffing_grand_total_sum() -> None:
    rows = load_typed_rows(config.LGA_CURRENT_STAFFING_CSV, LgaCurrentStaffing)
    assert len(rows) == config.EXPECTED_LGA_ROW_COUNT, (
        f"data/lga_current_staffing.csv has {len(rows)} rows, expected "
        f"{config.EXPECTED_LGA_ROW_COUNT}."
    )
    total = sum(r.grand_total for r in rows)
    assert total == config.EXPECTED_GRAND_TOTAL_SUM, (
        f"data/lga_current_staffing.csv's grand_total column sums to {total}, "
        f"expected {config.EXPECTED_GRAND_TOTAL_SUM}."
    )


def test_state_staffing_gap_sum() -> None:
    rows = load_typed_rows(config.STATE_STAFFING_GAP_CSV, StateStaffingGap)
    total = sum(r.gap_across_state for r in rows)
    assert total == config.EXPECTED_GAP_ACROSS_STATE_SUM, (
        f"data/state_staffing_gap.csv's gap_across_state column sums to {total}, "
        f"expected {config.EXPECTED_GAP_ACROSS_STATE_SUM}."
    )


def test_lga_facility_count_sum_and_row_count() -> None:
    rows = load_typed_rows(config.LGA_FACILITY_COUNT_CSV, LgaFacilityCount)
    assert len(rows) == config.EXPECTED_LGA_ROW_COUNT, (
        f"data/lga_facility_count.csv has {len(rows)} rows, expected "
        f"{config.EXPECTED_LGA_ROW_COUNT}."
    )
    total = sum(r.facility_count for r in rows)
    assert total == config.EXPECTED_FACILITY_COUNT_SUM, (
        f"data/lga_facility_count.csv's facility_count column sums to {total}, "
        f"expected {config.EXPECTED_FACILITY_COUNT_SUM}."
    )


def main() -> int:
    tests = [
        test_lga_current_staffing_grand_total_sum,
        test_state_staffing_gap_sum,
        test_lga_facility_count_sum_and_row_count,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL: {test.__name__}: {exc}")
    if failures:
        print(f"\n{failures} of {len(tests)} CSV sum checks failed.")
        return 1
    print(f"\nAll {len(tests)} CSV sum checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
