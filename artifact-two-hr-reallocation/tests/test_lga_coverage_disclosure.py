"""Asserts the rendered HTML report explicitly lists all 26 covered LGAs and
explicitly names Guzamala's exclusion as a primary-source data gap, not an
assessment result (ULTIMATE_PRD.md Sec.2 finding 9, Sec.11's Guzamala row).

Calls viz.generate_report.render_html() directly with synthetic run data --
no Postgres/dbt required -- since render_html() takes plain Python objects,
not a database connection (viz.generate_report.fetch_latest_run() is the
only DB-touching function in that module).

Run directly: `python -m tests.test_lga_coverage_disclosure`
Or via pytest: `pytest tests/test_lga_coverage_disclosure.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_lga_coverage_disclosure.py), Sec.8 criterion 4.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime

from viz.generate_report import (
    COVERED_LGAS,
    EXCLUDED_LGA,
    AllocationRow,
    RunSummary,
    render_html,
)

_TAG_RE = re.compile(r"<[^>]+>")


def _visible_text(rendered_html: str) -> str:
    """Strip HTML tags and collapse whitespace, so a substring assertion
    isn't broken by an inline `<strong>`/`<em>` tag landing mid-phrase.
    """
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", rendered_html))


def _synthetic_run() -> tuple[RunSummary, list[AllocationRow]]:
    run_summary = RunSummary(
        run_at=datetime.now(UTC),
        variance_before=1.0,
        variance_after=0.5,
        solver_status="optimal_within_2pct_gap",
    )
    allocations = [
        AllocationRow(
            lga=lga,
            population_proxy=100_000.0,
            grand_total_before=100,
            grand_total_after=100,
            ratio_before=0.001,
            ratio_after=0.001,
        )
        for lga in COVERED_LGAS
    ]
    return run_summary, allocations


def test_all_26_covered_lgas_named_in_report() -> None:
    run_summary, allocations = _synthetic_run()
    rendered = render_html(run_summary, [], allocations)

    assert len(COVERED_LGAS) == 26, "COVERED_LGAS itself must list exactly 26 LGAs."
    missing = [lga for lga in COVERED_LGAS if lga not in rendered]
    assert not missing, f"Report is missing these covered LGAs: {missing}"


def test_guzamala_exclusion_named_explicitly() -> None:
    run_summary, allocations = _synthetic_run()
    rendered = render_html(run_summary, [], allocations)
    visible = _visible_text(rendered)

    assert EXCLUDED_LGA in rendered, f"Report never mentions {EXCLUDED_LGA} at all."
    assert EXCLUDED_LGA not in COVERED_LGAS, f"{EXCLUDED_LGA} must never be in COVERED_LGAS."
    # Not just a bare mention -- must read as an explicit, named exclusion, not
    # silence or an implied "assessed, found fine" (ULTIMATE_PRD.md Sec.11).
    assert "explicitly excluded" in visible
    assert "absent from Table 1" in visible


def main() -> int:
    tests = [test_all_26_covered_lgas_named_in_report, test_guzamala_exclusion_named_explicitly]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL: {test.__name__}: {exc}")
    if failures:
        print(f"\n{failures} of {len(tests)} coverage-disclosure checks failed.")
        return 1
    print(f"\nAll {len(tests)} coverage-disclosure checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
