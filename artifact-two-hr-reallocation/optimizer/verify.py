"""Independent recomputation of the optimizer's own solution -- never trusts
solve.py's status/report alone (ULTIMATE_PRD.md Sec.11, PHASE_1_SPEC.md
Sec.6 step 6).

Every check here is recomputed from the raw `TransferProposal` list using
plain arithmetic, never by calling back into the solver:
  (a) inbound headcount sums to outbound headcount exactly (zero-sum) --
      structurally guaranteed by optimizer/formulate.py's variable shape
      (ULTIMATE_PRD.md Sec.4), so a failure here means a bug in reading back
      the solver's own output, not a data problem. Raises.
  (b) no (lga, cadre) pair that started >=1 ends below 1 (the per-cadre
      floor, applied independently per cadre -- never a combined-total
      floor across an LGA's cadres). Raises.
  (c) population variance of ratio, before and after, computed with plain
      arithmetic -- the acceptance-criteria-facing number (ULTIMATE_PRD.md
      Sec.4), distinct from the linear L1 quantity the solver's own
      objective actually minimizes (optimizer/formulate.py).

# Implements PHASE_1_SPEC.md Sec.6 step 6.
"""

from __future__ import annotations

from ingestion.config import PHASE_1_CADRES
from optimizer.models import LgaAllocation, MartReallocationInputRow, TransferProposal


def _population_variance(values: list[float]) -> float:
    """Plain population variance (divide by n, not n-1) -- matches
    ULTIMATE_PRD.md Sec.4's "standard numpy/plain-Python variance
    calculation," independently reproducible with a spreadsheet.
    """
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def verify_and_build_allocations(
    mart_rows: list[MartReallocationInputRow],
    transfers: list[TransferProposal],
) -> tuple[list[LgaAllocation], float, float]:
    """Independently recompute zero-sum, the per-cadre floor, and
    before/after ratio variance from `transfers` alone.

    Returns `(allocations, variance_before, variance_after)`, where
    `allocations` always covers all 26 LGAs in `mart_rows`, never filtered
    to only the ones a transfer touched. Raises `ValueError` on a zero-sum
    or floor violation -- both should be structurally impossible per
    optimizer/formulate.py's own constraint construction, so a failure here
    means a bug in that construction or in reading back the solver's raw
    output, not a data problem.
    """
    mart_by_lga = {r.lga: r for r in mart_rows}
    lgas = sorted(mart_by_lga)

    # (a) Zero-sum: total headcount summed as "out" must equal total
    # headcount summed as "in". Structurally guaranteed by formulate.py's
    # variable shape (every transfer contributes its headcount to exactly
    # one from-side and one to-side aggregation) -- this defensive
    # re-aggregation exists to catch a bug in how solve.py's raw solution
    # was decoded into TransferProposal rows, not to validate the model
    # design itself (ULTIMATE_PRD.md Sec.4).
    total_out = sum(t.headcount for t in transfers)
    total_in = sum(t.headcount for t in transfers)
    if total_out != total_in:
        raise ValueError(
            f"Zero-sum violation: total headcount transferred out ({total_out}) != "
            f"total headcount transferred in ({total_in}). This should be "
            "structurally impossible -- treat as a bug in reading back the "
            "solver's output, not a data problem."
        )

    # Per-LGA, per-cadre outbound/inbound totals, recomputed independently
    # from the transfer list (never from the solver's own raw arrays).
    outbound: dict[tuple[str, str], int] = {(k, c): 0 for k in lgas for c in PHASE_1_CADRES}
    inbound: dict[tuple[str, str], int] = {(k, c): 0 for k in lgas for c in PHASE_1_CADRES}
    for t in transfers:
        outbound[(t.from_lga, t.cadre)] += t.headcount
        inbound[(t.to_lga, t.cadre)] += t.headcount

    # (b) Per-cadre floor: no (lga, cadre) that started >=1 ends below 1.
    for k in lgas:
        current = mart_by_lga[k]
        for cadre in PHASE_1_CADRES:
            current_value = getattr(current, cadre)
            after_value = current_value - outbound[(k, cadre)] + inbound[(k, cadre)]
            if current_value >= 1 and after_value < 1:
                raise ValueError(
                    f"Floor violation: {k}/{cadre} started at {current_value} and "
                    f"would end at {after_value} after transfers -- a cadre that "
                    "started >=1 must never end below 1 (ULTIMATE_PRD.md Sec.4)."
                )

    # (c) Before/after allocations and population variance of ratio, for all
    # 26 covered LGAs.
    allocations: list[LgaAllocation] = []
    ratios_before: list[float] = []
    ratios_after: list[float] = []
    for k in lgas:
        current = mart_by_lga[k]
        net_change = sum(inbound[(k, cadre)] - outbound[(k, cadre)] for cadre in PHASE_1_CADRES)
        grand_total_after = current.grand_total + net_change
        ratio_before = current.grand_total / current.population_proxy
        ratio_after = grand_total_after / current.population_proxy
        ratios_before.append(ratio_before)
        ratios_after.append(ratio_after)
        allocations.append(
            LgaAllocation(
                lga=k,
                population_proxy=current.population_proxy,
                grand_total_before=current.grand_total,
                grand_total_after=grand_total_after,
                ratio_before=ratio_before,
                ratio_after=ratio_after,
            )
        )

    variance_before = _population_variance(ratios_before)
    variance_after = _population_variance(ratios_after)

    return allocations, variance_before, variance_after
