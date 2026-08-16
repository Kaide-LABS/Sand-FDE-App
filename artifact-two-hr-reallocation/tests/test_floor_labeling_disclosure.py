"""Asserts the rendered HTML report explicitly labels the per-cadre staffing
floor as an artifact-imposed safety constraint chosen by the builder -- not
the PDF's own NPHCDA minimum standard (Table 6) and not a claim that any LGA
meeting the floor meets that actual minimum standard (baby_prd.md's
confirmed acceptance criterion, PHASE_1_SPEC.md Sec.8 criterion 5).

Calls viz.generate_report.render_html() directly with synthetic run data --
no Postgres/dbt required.

Run directly: `python -m tests.test_floor_labeling_disclosure`
Or via pytest: `pytest tests/test_floor_labeling_disclosure.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_floor_labeling_disclosure.py
# -- named in Sec.8 criterion 5 but omitted from Sec.1's file list; added
# here to satisfy that acceptance criterion -- see AUTONOMOUS CRITIQUE),
# Sec.8 criterion 5.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime

from viz.generate_report import COVERED_LGAS, AllocationRow, RunSummary, render_html

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


def test_floor_labeled_as_artifact_imposed_constraint() -> None:
    run_summary, allocations = _synthetic_run()
    visible = _visible_text(render_html(run_summary, [], allocations))

    assert "artifact-imposed safety constraint" in visible


def test_floor_explicitly_distinguished_from_nphcda_standard() -> None:
    run_summary, allocations = _synthetic_run()
    visible = _visible_text(render_html(run_summary, [], allocations))

    assert "not NPHCDA's minimum staffing standard" in visible
    assert "not the same as meeting NPHCDA's minimum standard" in visible


def test_floor_explicitly_distinguished_from_table6_aspirational_target() -> None:
    run_summary, allocations = _synthetic_run()
    visible = _visible_text(render_html(run_summary, [], allocations))

    assert "Table 6" in visible
    assert "aspirational target" in visible


def main() -> int:
    tests = [
        test_floor_labeled_as_artifact_imposed_constraint,
        test_floor_explicitly_distinguished_from_nphcda_standard,
        test_floor_explicitly_distinguished_from_table6_aspirational_target,
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
        print(f"\n{failures} of {len(tests)} floor-labeling-disclosure checks failed.")
        return 1
    print(f"\nAll {len(tests)} floor-labeling-disclosure checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
