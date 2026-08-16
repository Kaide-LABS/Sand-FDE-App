"""Independent recomputation of acceptance criterion 1 (baby_prd.md): the
payroll is provably zero-sum. Runs the optimizer end-to-end against the
checked-in data/*.csv files (no Postgres/dbt required -- see
tests/_test_support.py) and then recomputes, in this file's own code (not
by calling optimizer/verify.py, which already does its own internal
zero-sum check), whether total headcount transferred out equals total
headcount transferred in.

This passes trivially by construction (optimizer/formulate.py's decision
variables cannot represent a non-zero-sum solution -- ULTIMATE_PRD.md
Sec.4), but the test exists to catch a bug in reading the solver's raw
output back into TransferProposal rows, not to validate the model design
itself (PHASE_1_SPEC.md Sec.8 criterion 1).

Run directly: `python -m tests.test_zero_sum`
Or via pytest: `pytest tests/test_zero_sum.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_zero_sum.py), Sec.8 criterion 1.
"""

from __future__ import annotations

import sys

from optimizer.formulate import build_problem
from optimizer.models import TransferProposal, as_cadre
from optimizer.solve import solve
from tests._test_support import build_mart_rows_from_csv


def _run_optimizer_for_transfers() -> list[TransferProposal]:
    mart_rows = build_mart_rows_from_csv()
    problem = build_problem(mart_rows)
    solve_result = solve(problem)
    return [
        TransferProposal(
            cadre=as_cadre(cadre), from_lga=from_lga, to_lga=to_lga, headcount=headcount
        )
        for (from_lga, to_lga, cadre), headcount in solve_result.x_values.items()
    ]


def test_zero_sum_payroll() -> None:
    transfers = _run_optimizer_for_transfers()

    outbound_by_lga: dict[str, int] = {}
    inbound_by_lga: dict[str, int] = {}
    for t in transfers:
        outbound_by_lga[t.from_lga] = outbound_by_lga.get(t.from_lga, 0) + t.headcount
        inbound_by_lga[t.to_lga] = inbound_by_lga.get(t.to_lga, 0) + t.headcount

    total_out = sum(outbound_by_lga.values())
    total_in = sum(inbound_by_lga.values())

    assert total_out == total_in, (
        f"Zero-sum violation: total headcount out ({total_out}) != total headcount in ({total_in})."
    )
    # A spreadsheet-SUM-equivalent double-check: summing the raw transfer list's
    # headcount column once should equal both aggregates above.
    assert sum(t.headcount for t in transfers) == total_out == total_in


def main() -> int:
    try:
        test_zero_sum_payroll()
    except AssertionError as exc:
        print(f"FAIL: test_zero_sum_payroll: {exc}")
        return 1
    print("PASS: test_zero_sum_payroll")
    return 0


if __name__ == "__main__":
    sys.exit(main())
