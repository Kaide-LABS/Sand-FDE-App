"""Independent recomputation of acceptance criterion 4 (baby_prd.md): the
stated objective actually improved. Runs the optimizer end-to-end against
the checked-in data/*.csv files (no Postgres/dbt required -- see
tests/_test_support.py) and recomputes variance_before/variance_after in
this file's own code, directly from `mart_reallocation_input`'s equivalent
rows and the transfer list -- not read from `OptimizationResult`'s own
self-reported `variance_before`/`variance_after` fields, per
PHASE_1_SPEC.md Sec.8 criterion 3's explicit requirement.

Run directly: `python -m tests.test_variance_improved`
Or via pytest: `pytest tests/test_variance_improved.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_variance_improved.py -- named
# in Sec.8 criterion 3 but omitted from Sec.1's file list; added here to
# satisfy that acceptance criterion -- see AUTONOMOUS CRITIQUE), Sec.8 criterion 3.
"""

from __future__ import annotations

import sys

from ingestion.config import PHASE_1_CADRES
from optimizer.formulate import build_problem
from optimizer.models import MartReallocationInputRow, TransferProposal, as_cadre
from optimizer.solve import solve
from tests._test_support import build_mart_rows_from_csv


def _run_optimizer() -> tuple[list[MartReallocationInputRow], list[TransferProposal]]:
    mart_rows = build_mart_rows_from_csv()
    problem = build_problem(mart_rows)
    solve_result = solve(problem)
    transfers = [
        TransferProposal(
            cadre=as_cadre(cadre), from_lga=from_lga, to_lga=to_lga, headcount=headcount
        )
        for (from_lga, to_lga, cadre), headcount in solve_result.x_values.items()
    ]
    return mart_rows, transfers


def _population_variance(values: list[float]) -> float:
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def test_variance_improved() -> None:
    mart_rows, transfers = _run_optimizer()
    mart_by_lga = {r.lga: r for r in mart_rows}

    net_change: dict[tuple[str, str], int] = {}
    for t in transfers:
        net_change[(t.from_lga, t.cadre)] = net_change.get((t.from_lga, t.cadre), 0) - t.headcount
        net_change[(t.to_lga, t.cadre)] = net_change.get((t.to_lga, t.cadre), 0) + t.headcount

    ratios_before: list[float] = []
    ratios_after: list[float] = []
    for lga, mart_row in mart_by_lga.items():
        total_net = sum(net_change.get((lga, cadre), 0) for cadre in PHASE_1_CADRES)
        grand_total_after = mart_row.grand_total + total_net
        ratios_before.append(mart_row.grand_total / mart_row.population_proxy)
        ratios_after.append(grand_total_after / mart_row.population_proxy)

    variance_before = _population_variance(ratios_before)
    variance_after = _population_variance(ratios_after)

    assert variance_after < variance_before, (
        f"Variance did not improve: before={variance_before!r}, after={variance_after!r}."
    )


def main() -> int:
    try:
        test_variance_improved()
    except AssertionError as exc:
        print(f"FAIL: test_variance_improved: {exc}")
        return 1
    print("PASS: test_variance_improved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
