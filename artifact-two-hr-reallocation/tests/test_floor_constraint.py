"""Independent recomputation of acceptance criterion 3 (baby_prd.md): no
LGA drops below the per-cadre floor. Runs the optimizer end-to-end against
the checked-in data/*.csv files (no Postgres/dbt required -- see
tests/_test_support.py) and then recomputes, in this file's own code (not
by calling optimizer/verify.py, which already does its own internal floor
check), whether every (LGA, cadre) pair that started with >=1 worker still
has >=1 worker after every proposed transfer.

The floor applies per cadre independently, never as a combined-total floor
across an LGA's cadres (ULTIMATE_PRD.md Sec.4) -- this test checks each of
the 4 Phase-1 cadres separately for every LGA, exactly as
PHASE_1_SPEC.md Sec.8 criterion 2 specifies.

Run directly: `python -m tests.test_floor_constraint`
Or via pytest: `pytest tests/test_floor_constraint.py`

# Implements PHASE_1_SPEC.md Sec.1 (tests/test_floor_constraint.py), Sec.8 criterion 2.
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


def test_floor_constraint_holds_per_cadre_per_lga() -> None:
    mart_rows, transfers = _run_optimizer()
    mart_by_lga = {r.lga: r for r in mart_rows}

    outbound: dict[tuple[str, str], int] = {}
    for t in transfers:
        key = (t.from_lga, t.cadre)
        outbound[key] = outbound.get(key, 0) + t.headcount

    violations: list[str] = []
    for lga, mart_row in mart_by_lga.items():
        for cadre in PHASE_1_CADRES:
            current_value = getattr(mart_row, cadre)
            outbound_value = outbound.get((lga, cadre), 0)
            after_value = current_value - outbound_value
            if current_value >= 1 and after_value < 1:
                violations.append(
                    f"{lga}/{cadre}: started at {current_value}, {outbound_value} sent "
                    f"out, ends at {after_value}"
                )

    assert not violations, "Floor violations found:\n" + "\n".join(violations)


def main() -> int:
    try:
        test_floor_constraint_holds_per_cadre_per_lga()
    except AssertionError as exc:
        print(f"FAIL: test_floor_constraint_holds_per_cadre_per_lga: {exc}")
        return 1
    print("PASS: test_floor_constraint_holds_per_cadre_per_lga")
    return 0


if __name__ == "__main__":
    sys.exit(main())
