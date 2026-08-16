"""Direct coverage of `optimizer/verify.py` itself.

Every other acceptance test in this suite (test_zero_sum.py,
test_floor_constraint.py, test_variance_improved.py) deliberately does NOT
call `optimizer.verify.verify_and_build_allocations` -- each reimplements
the same zero-sum/floor/variance checks independently, by design (see those
files' own docstrings), so a bug shared between `optimizer/formulate.py` and
`optimizer/verify.py` can't hide behind both checks making the same mistake.

That discipline left a real gap: nothing in the suite ever calls the actual
shipped `optimizer.verify.verify_and_build_allocations` function, so a bug
introduced in `verify.py` itself -- the module ULTIMATE_PRD.md Sec.11 and
PHASE_1_SPEC.md Sec.6 step 6 both name as this artifact's own
never-trust-the-solver-alone safety layer -- would ship with 0% test
coverage and no test would ever catch it.

This file closes that gap the same way the rest of this project handles
"never trust one layer alone": it calls the real `verify_and_build_allocations`
AND independently recomputes the same three quantities in its own code,
then asserts both agree. Found via PHASE_1_SPEC.md Sec.8's own review
process (coverage measured with `pytest --cov=optimizer`, not assumed).

Run directly: `python -m tests.test_verify_module`
Or via pytest: `pytest tests/test_verify_module.py`
"""

from __future__ import annotations

import sys

from ingestion.config import PHASE_1_CADRES
from optimizer.formulate import build_problem
from optimizer.models import MartReallocationInputRow, TransferProposal, as_cadre
from optimizer.solve import solve
from optimizer.verify import verify_and_build_allocations
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


def _independent_population_variance(values: list[float]) -> float:
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def test_verify_module_does_not_raise_on_the_real_solution() -> None:
    """The shipped `verify_and_build_allocations` must accept the real
    optimizer output without raising -- if it ever raises here, either
    `formulate.py`'s constraints are wrong or `verify.py` itself has a bug;
    either way this is the one test that would actually catch it.
    """
    mart_rows, transfers = _run_optimizer()
    # No exception == zero-sum and floor both held, per verify.py's own contract.
    verify_and_build_allocations(mart_rows, transfers)


def test_verify_module_allocations_cover_all_26_lgas() -> None:
    mart_rows, transfers = _run_optimizer()
    allocations, _, _ = verify_and_build_allocations(mart_rows, transfers)
    assert {a.lga for a in allocations} == {r.lga for r in mart_rows}
    assert len(allocations) == 26


def test_verify_module_agrees_with_independent_recomputation() -> None:
    """Cross-check `verify.py`'s own before/after allocations and variance
    against a second, independent recomputation written directly in this
    test file (deliberately not sharing code with `verify.py`), so the two
    would have to be wrong in exactly the same way to both agree and both be
    incorrect.
    """
    mart_rows, transfers = _run_optimizer()
    allocations, variance_before, variance_after = verify_and_build_allocations(
        mart_rows, transfers
    )

    mart_by_lga = {r.lga: r for r in mart_rows}
    net_change: dict[tuple[str, str], int] = {}
    for t in transfers:
        net_change[(t.from_lga, t.cadre)] = net_change.get((t.from_lga, t.cadre), 0) - t.headcount
        net_change[(t.to_lga, t.cadre)] = net_change.get((t.to_lga, t.cadre), 0) + t.headcount

    expected_after_by_lga: dict[str, int] = {}
    ratios_before: list[float] = []
    ratios_after: list[float] = []
    for lga, mart_row in mart_by_lga.items():
        total_net = sum(net_change.get((lga, cadre), 0) for cadre in PHASE_1_CADRES)
        after = mart_row.grand_total + total_net
        expected_after_by_lga[lga] = after
        ratios_before.append(mart_row.grand_total / mart_row.population_proxy)
        ratios_after.append(after / mart_row.population_proxy)

    expected_variance_before = _independent_population_variance(ratios_before)
    expected_variance_after = _independent_population_variance(ratios_after)

    assert variance_before == expected_variance_before
    assert variance_after == expected_variance_after
    for allocation in allocations:
        assert allocation.grand_total_after == expected_after_by_lga[allocation.lga]


def test_verify_module_raises_on_a_genuine_floor_violation() -> None:
    """Unlike the zero-sum guard (structurally unreachable given
    `TransferProposal`'s paired from/to shape -- every transfer contributes
    its headcount to exactly one "out" and one "in", so `total_out` and
    `total_in` can never disagree, matching ULTIMATE_PRD.md Sec.4's own
    "cannot fail for an arithmetic reason" disclosure), the per-cadre floor
    guard IS genuinely reachable: nothing in the `TransferProposal` type
    itself prevents constructing a transfer that drains an LGA/cadre below
    1. `optimizer/formulate.py`'s MILP bounds are what prevent the solver
    from proposing one -- a hand-built transfer list bypasses that entirely,
    which is exactly what this test does, to prove `verify.py`'s floor
    guard actually raises on a real violation rather than being an
    untested, possibly-inert branch.
    """
    mart_rows = build_mart_rows_from_csv()
    cadre = PHASE_1_CADRES[0]
    source = next(r for r in mart_rows if getattr(r, cadre) >= 1)
    destination = next(r for r in mart_rows if r.lga != source.lga)

    draining_transfer = TransferProposal(
        cadre=as_cadre(cadre),
        from_lga=source.lga,
        to_lga=destination.lga,
        headcount=int(getattr(source, cadre)),  # drains this LGA/cadre to exactly 0
    )

    try:
        verify_and_build_allocations(mart_rows, [draining_transfer])
    except ValueError as exc:
        assert "Floor violation" in str(exc)
    else:
        raise AssertionError(
            "verify_and_build_allocations did not raise for a transfer that drains "
            f"{source.lga}/{cadre} from {getattr(source, cadre)} to 0 -- the floor "
            "guard should have fired."
        )


def main() -> int:
    tests = [
        test_verify_module_does_not_raise_on_the_real_solution,
        test_verify_module_allocations_cover_all_26_lgas,
        test_verify_module_agrees_with_independent_recomputation,
        test_verify_module_raises_on_a_genuine_floor_violation,
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
        print(f"\n{failures} of {len(tests)} verify-module checks failed.")
        return 1
    print(f"\nAll {len(tests)} verify-module checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
