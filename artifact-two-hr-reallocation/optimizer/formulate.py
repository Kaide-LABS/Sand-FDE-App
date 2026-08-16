"""Builds the MILP formulation (ULTIMATE_PRD.md Sec.4) from
`dbt_marts.mart_reallocation_input`.

Decision variables `x[i][j][c]`: integer number of workers of cadre `c`
transferred from LGA `i` to LGA `j` (`i != j`), for the 4 Phase-1 cadres
(`ingestion.config.PHASE_1_CADRES`) over the 26x25 LGA-pair space. Zero-sum
payroll is true by construction of this variable shape -- every unit of
`x[i][j][c]` is exactly -1 for LGA `i` and exactly +1 for LGA `j`; there is
no feasible assignment that is not zero-sum. This is never added as an
explicit `sum(x) == 0` constraint (that would be redundant, and restructuring
the variables into any shape that could violate zero-sum even in principle is
exactly what ULTIMATE_PRD.md Sec.4 rules out) -- optimizer/verify.py still
independently recomputes it from the raw solution, never trusting the
solver's own report alone.

Objective: minimizes the linear L1 deviation of each LGA's post-transfer
staff-to-population ratio from a fixed, MILP-derived `target_ratio`. This is
a linear proxy for variance -- true population variance is quadratic and
`scipy.optimize.milp` cannot take it as an objective. Population variance
itself is computed post-hoc, independently, in optimizer/verify.py.

# Implements PHASE_1_SPEC.md Sec.6 step 4, ULTIMATE_PRD.md Sec.4.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from psycopg import Connection
from psycopg.rows import dict_row
from scipy.optimize import Bounds, LinearConstraint

from ingestion.config import PHASE_1_CADRES
from optimizer.models import MartReallocationInputRow

MARTS_SCHEMA = "dbt_marts"  # dbt: base schema "dbt" (profiles.yml) + custom schema "marts"
EXPECTED_LGA_COUNT = 26  # ULTIMATE_PRD.md Sec.2 finding 9 -- Guzamala is not among them.


def load_mart_rows(conn: Connection) -> list[MartReallocationInputRow]:
    """Read and validate every row of `dbt_marts.mart_reallocation_input`.

    Raises `ValueError` if the row count is not exactly 26. dbt's own
    row-count test (warehouse/dbt/tests/mart_reallocation_input_row_count.sql)
    should already have failed the build before this ever runs; this is a
    second, independent guard in the code path that actually consumes the
    data, per the "never trust one layer's self-report alone" discipline
    this project applies throughout (ULTIMATE_PRD.md Sec.11).
    """
    query = f"""
        select lga, community_health_officer, community_health_extension_worker,
               junior_community_health_extension_worker, nurse_midwife,
               grand_total, population_proxy, ratio
        from {MARTS_SCHEMA}.mart_reallocation_input
        order by lga
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        raw_rows = cur.fetchall()
    rows = [MartReallocationInputRow.model_validate(r) for r in raw_rows]
    if len(rows) != EXPECTED_LGA_COUNT:
        raise ValueError(
            f"mart_reallocation_input has {len(rows)} rows, expected exactly "
            f"{EXPECTED_LGA_COUNT} (one per LGA PDF Table 1 lists -- "
            "ULTIMATE_PRD.md Sec.2 finding 9). Run `dbt run` and `dbt test` "
            "before the optimizer."
        )
    return rows


@dataclass(frozen=True)
class MilpProblem:
    """Everything `scipy.optimize.milp` needs, plus the index bookkeeping
    optimizer/solve.py and optimizer/verify.py need to decode the flat
    solution vector back into `(from_lga, to_lga, cadre)` transfers.

    An internal transport object, not a validated Pydantic boundary schema
    -- optimizer/models.py's boundary models (PHASE_1_SPEC.md Sec.3) are for
    objects that cross into/out of this package; numpy arrays are not a
    Pydantic-friendly shape and this object never leaves the optimizer
    package's own call chain.
    """

    lgas: tuple[str, ...]
    cadres: tuple[str, str, str, str]
    mart_by_lga: dict[str, MartReallocationInputRow]
    target_ratio: float
    x_index: dict[tuple[str, str, str], int]  # (from_lga, to_lga, cadre) -> flat vector index
    d_index: dict[str, int]  # lga -> flat vector index
    n_vars: int
    c: npt.NDArray[np.float64]
    integrality: npt.NDArray[np.float64]
    bounds: Bounds
    constraint: LinearConstraint


def _floor_bound(current_value: int) -> int:
    """The per-cadre floor upper bound on outbound transfers from one LGA:
    `max(current[k][c] - 1, 0)` (ULTIMATE_PRD.md Sec.4). Applied
    independently per (LGA, cadre) pair -- never a combined-total floor
    across a facility's/LGA's cadres.
    """
    return max(current_value - 1, 0)


def build_problem(mart_rows: list[MartReallocationInputRow]) -> MilpProblem:
    """Build the MILP per ULTIMATE_PRD.md Sec.4 from the given mart rows."""
    lgas = tuple(sorted(r.lga for r in mart_rows))
    cadres = PHASE_1_CADRES
    mart_by_lga = {r.lga: r for r in mart_rows}

    # --- Variable indexing -----------------------------------------------
    x_index: dict[tuple[str, str, str], int] = {}
    idx = 0
    for i in lgas:
        for j in lgas:
            if i == j:
                continue
            for cadre in cadres:
                x_index[(i, j, cadre)] = idx
                idx += 1

    d_index: dict[str, int] = {}
    for k in lgas:
        d_index[k] = idx
        idx += 1
    n_vars = idx

    # --- Objective: minimize sum(d) ----------------------------------------
    c_vec = np.zeros(n_vars, dtype=np.float64)
    for k in lgas:
        c_vec[d_index[k]] = 1.0

    # --- Integrality: x integer, d continuous -------------------------------
    integrality = np.zeros(n_vars, dtype=np.float64)
    for pos in x_index.values():
        integrality[pos] = 1.0

    # --- Bounds --------------------------------------------------------------
    # Per-(lga, cadre) floor upper bound on total outbound transfers.
    floor_bound: dict[tuple[str, str], int] = {
        (k, cadre): _floor_bound(getattr(mart_by_lga[k], cadre)) for k in lgas for cadre in cadres
    }

    lb = np.zeros(n_vars, dtype=np.float64)
    ub = np.full(n_vars, np.inf, dtype=np.float64)
    for (i, _j, cadre), pos in x_index.items():
        # A single x[i][j][c] can never exceed LGA i's total outbound
        # allowance for cadre c, since all x are non-negative and the
        # aggregate floor constraint below bounds their sum -- so applying
        # the same bound per-variable here is a valid tightening (it cannot
        # exclude any solution the aggregate constraint would otherwise
        # allow), not a second, independent restriction.
        ub[pos] = floor_bound[(i, cadre)]
    bounds = Bounds(lb=lb, ub=ub)

    # --- Fixed constant: target_ratio ----------------------------------------
    total_grand_total = sum(r.grand_total for r in mart_rows)
    total_population = sum(r.population_proxy for r in mart_rows)
    target_ratio = total_grand_total / total_population

    # --- Linear constraints ----------------------------------------------------
    rows: list[npt.NDArray[np.float64]] = []
    row_lb: list[float] = []
    row_ub: list[float] = []

    # (a) Per-cadre floor: sum_j x[k][j][c] <= max(current[k][c]-1, 0).
    for k in lgas:
        for cadre in cadres:
            row = np.zeros(n_vars, dtype=np.float64)
            for j in lgas:
                if j == k:
                    continue
                row[x_index[(k, j, cadre)]] = 1.0
            rows.append(row)
            row_lb.append(-np.inf)
            row_ub.append(float(floor_bound[(k, cadre)]))

    # (b) Deviation-from-target linearization: d[k] >= |ratio[k] - target_ratio|,
    # split into its two linear halves (ratio[k] is linear in x since
    # population_proxy[k] is a fixed constant per LGA -- ULTIMATE_PRD.md Sec.4).
    for k in lgas:
        pop = mart_by_lga[k].population_proxy
        grand_total = mart_by_lga[k].grand_total
        base_ratio = grand_total / pop  # LGA k's ratio before any transfer

        # Row A: d[k] - net[k]/pop[k] >= base_ratio - target_ratio
        row_a = np.zeros(n_vars, dtype=np.float64)
        row_a[d_index[k]] = 1.0
        for cadre in cadres:
            for j in lgas:
                if j != k:
                    row_a[x_index[(k, j, cadre)]] += 1.0 / pop  # outbound reduces ratio[k]
            for i in lgas:
                if i != k:
                    row_a[x_index[(i, k, cadre)]] -= 1.0 / pop  # inbound raises ratio[k]
        rows.append(row_a)
        row_lb.append(base_ratio - target_ratio)
        row_ub.append(np.inf)

        # Row B: d[k] + net[k]/pop[k] >= target_ratio - base_ratio
        row_b = np.zeros(n_vars, dtype=np.float64)
        row_b[d_index[k]] = 1.0
        for cadre in cadres:
            for j in lgas:
                if j != k:
                    row_b[x_index[(k, j, cadre)]] -= 1.0 / pop
            for i in lgas:
                if i != k:
                    row_b[x_index[(i, k, cadre)]] += 1.0 / pop
        rows.append(row_b)
        row_lb.append(target_ratio - base_ratio)
        row_ub.append(np.inf)

    constraint = LinearConstraint(
        np.vstack(rows),
        lb=np.array(row_lb, dtype=np.float64),
        ub=np.array(row_ub, dtype=np.float64),
    )

    return MilpProblem(
        lgas=lgas,
        cadres=cadres,
        mart_by_lga=mart_by_lga,
        target_ratio=target_ratio,
        x_index=x_index,
        d_index=d_index,
        n_vars=n_vars,
        c=c_vec,
        integrality=integrality,
        bounds=bounds,
        constraint=constraint,
    )
