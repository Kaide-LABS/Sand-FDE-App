"""Guards against ingestion/config.py and warehouse/dbt/seeds/indicator_reference.csv
silently drifting apart.

Both files independently encode the same 24-indicator basket (which
indicators count toward reporting-volume completeness, which subset is used
for the biological-impossibility test, and -- for that subset -- the
population fraction and MSDAT denominator text). Nothing at runtime enforces
they agree: config.py drives ingestion, the CSV seed drives the dbt join. If
someone edits one without mirroring the other, the pipeline still runs, but
produces a wrong join silently (e.g. an indicator ingestion pulls that the
seed doesn't know is impossibility-relevant, or vice versa).

Run directly: `python -m tests.test_indicator_reference_sync`
Or via pytest, if installed: `pytest tests/`
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from ingestion.config import IMPOSSIBILITY_INDICATORS, REPORTING_BASKET_INDICATORS

SEED_CSV_PATH = (
    Path(__file__).resolve().parent.parent
    / "warehouse"
    / "dbt"
    / "seeds"
    / "indicator_reference.csv"
)


def _load_seed_rows() -> list[dict[str, str]]:
    with SEED_CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_seed_basket_membership_matches_config() -> None:
    rows = _load_seed_rows()
    expected_basket_ids = {indicator_id for indicator_id, _ in REPORTING_BASKET_INDICATORS}
    seed_basket_ids = {
        int(row["indicator_id"]) for row in rows if row["in_reporting_basket"] == "true"
    }
    assert seed_basket_ids == expected_basket_ids, (
        "indicator_reference.csv's in_reporting_basket=true rows do not match "
        f"config.py's REPORTING_BASKET_INDICATORS. "
        f"Only in CSV: {sorted(seed_basket_ids - expected_basket_ids)}. "
        f"Only in config.py: {sorted(expected_basket_ids - seed_basket_ids)}."
    )


def test_seed_impossibility_membership_and_fields_match_config() -> None:
    rows = _load_seed_rows()
    expected = {
        indicator_id: (fraction, denom_text)
        for indicator_id, _name, fraction, denom_text in IMPOSSIBILITY_INDICATORS
    }
    seed_impossibility_ids = {
        int(row["indicator_id"]) for row in rows if row["in_impossibility_test"] == "true"
    }
    assert seed_impossibility_ids == set(expected.keys()), (
        "indicator_reference.csv's in_impossibility_test=true rows do not match "
        f"config.py's IMPOSSIBILITY_INDICATORS. "
        f"Only in CSV: {sorted(seed_impossibility_ids - set(expected.keys()))}. "
        f"Only in config.py: {sorted(set(expected.keys()) - seed_impossibility_ids)}."
    )

    for row in rows:
        indicator_id = int(row["indicator_id"])
        if indicator_id not in expected:
            continue
        expected_fraction, expected_denom_text = expected[indicator_id]
        seed_fraction = float(row["population_fraction"])
        assert seed_fraction == expected_fraction, (
            f"indicator {indicator_id}: seed population_fraction={seed_fraction} "
            f"!= config.py's {expected_fraction}"
        )
        seed_denom_text = row["denominator_source_text"]
        assert seed_denom_text == expected_denom_text, (
            f"indicator {indicator_id}: seed denominator_source_text="
            f"{seed_denom_text!r} != config.py's {expected_denom_text!r}"
        )


def test_seed_indicator_names_match_config() -> None:
    rows = _load_seed_rows()
    config_names = {
        indicator_id: name for indicator_id, name in REPORTING_BASKET_INDICATORS
    }
    for row in rows:
        indicator_id = int(row["indicator_id"])
        if indicator_id not in config_names:
            continue
        assert row["indicator_name"] == config_names[indicator_id], (
            f"indicator {indicator_id}: seed name {row['indicator_name']!r} != "
            f"config.py name {config_names[indicator_id]!r}"
        )


def main() -> int:
    tests = [
        test_seed_basket_membership_matches_config,
        test_seed_impossibility_membership_and_fields_match_config,
        test_seed_indicator_names_match_config,
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
        print(f"\n{failures} of {len(tests)} sync checks failed.")
        return 1
    print(f"\nAll {len(tests)} sync checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
