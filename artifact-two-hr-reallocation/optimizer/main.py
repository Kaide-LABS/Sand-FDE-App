"""Orchestrates the optimizer end-to-end: pull `mart_reallocation_input` ->
formulate the MILP -> solve -> independently verify -> write results to
Postgres (`results` schema) and a dated CSV snapshot, matching
../artifact-one-data-quality's `data_snapshots/` pattern.

# Implements PHASE_1_SPEC.md Sec.6 step 7.
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

from psycopg import Connection

from ingestion.db import get_connection
from optimizer.formulate import build_problem, load_mart_rows
from optimizer.models import OptimizationResult, TransferProposal, as_cadre
from optimizer.solve import SUCCESS_STATUS_LABELS, solve
from optimizer.verify import verify_and_build_allocations

DATA_SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "data_snapshots"

RESULTS_SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS results;

CREATE TABLE IF NOT EXISTS results.optimization_runs (
    run_at TIMESTAMPTZ PRIMARY KEY,
    variance_before DOUBLE PRECISION NOT NULL,
    variance_after DOUBLE PRECISION NOT NULL,
    solver_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results.transfer_proposals (
    run_at TIMESTAMPTZ NOT NULL REFERENCES results.optimization_runs (run_at),
    cadre TEXT NOT NULL,
    from_lga TEXT NOT NULL,
    to_lga TEXT NOT NULL,
    headcount INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS results.lga_allocations (
    run_at TIMESTAMPTZ NOT NULL REFERENCES results.optimization_runs (run_at),
    lga TEXT NOT NULL,
    population_proxy DOUBLE PRECISION NOT NULL,
    grand_total_before INTEGER NOT NULL,
    grand_total_after INTEGER NOT NULL,
    ratio_before DOUBLE PRECISION NOT NULL,
    ratio_after DOUBLE PRECISION NOT NULL
);
"""


def _ensure_results_schema(conn: Connection) -> None:
    conn.execute(RESULTS_SCHEMA_DDL)


def run_optimization() -> OptimizationResult:
    """Run the full pipeline -- load mart data, formulate + solve the MILP,
    independently verify the solution -- and return the final result.
    Performs no writes; see `main()` for the write step.
    """
    with get_connection() as conn:
        mart_rows = load_mart_rows(conn)

    problem = build_problem(mart_rows)
    solve_result = solve(problem)

    transfers = [
        TransferProposal(
            cadre=as_cadre(cadre), from_lga=from_lga, to_lga=to_lga, headcount=headcount
        )
        for (from_lga, to_lga, cadre), headcount in solve_result.x_values.items()
    ]

    allocations, variance_before, variance_after = verify_and_build_allocations(
        mart_rows, transfers
    )

    return OptimizationResult(
        transfers=transfers,
        allocations=allocations,
        variance_before=variance_before,
        variance_after=variance_after,
        solver_status=solve_result.status_label,
    )


def _write_to_postgres(result: OptimizationResult, run_at: datetime) -> None:
    """Persist one full run (its solver status, every transfer, every LGA's
    before/after allocation) to Postgres, tagged with a shared `run_at` so a
    reader can reconstruct exactly one run's worth of rows.
    """
    with get_connection() as conn:
        _ensure_results_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO results.optimization_runs "
                "(run_at, variance_before, variance_after, solver_status) "
                "VALUES (%s, %s, %s, %s)",
                (run_at, result.variance_before, result.variance_after, result.solver_status),
            )
            if result.transfers:
                cur.executemany(
                    "INSERT INTO results.transfer_proposals "
                    "(run_at, cadre, from_lga, to_lga, headcount) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    [
                        (run_at, t.cadre, t.from_lga, t.to_lga, t.headcount)
                        for t in result.transfers
                    ],
                )
            cur.executemany(
                "INSERT INTO results.lga_allocations "
                "(run_at, lga, population_proxy, grand_total_before, grand_total_after, "
                "ratio_before, ratio_after) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        run_at,
                        a.lga,
                        a.population_proxy,
                        a.grand_total_before,
                        a.grand_total_after,
                        a.ratio_before,
                        a.ratio_after,
                    )
                    for a in result.allocations
                ],
            )


def _write_csv_snapshot(result: OptimizationResult, run_at: datetime) -> Path:
    """Write the transfer table to a dated CSV snapshot, matching
    ../artifact-one-data-quality/data_snapshots/'s naming convention.
    """
    DATA_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = run_at.strftime("%Y%m%dT%H%M%SZ")
    path = DATA_SNAPSHOTS_DIR / f"borno_hr_transfer_proposals_{timestamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cadre", "from_lga", "to_lga", "headcount"])
        for t in result.transfers:
            writer.writerow([t.cadre, t.from_lga, t.to_lga, t.headcount])
    return path


def main() -> int:
    """CLI entry point: run the optimizer, write results, print a summary."""
    result = run_optimization()
    run_at = datetime.now(UTC)
    _write_to_postgres(result, run_at)
    csv_path = _write_csv_snapshot(result, run_at)

    print(
        f"Solver status: {result.solver_status}. {len(result.transfers)} transfers "
        f"proposed. Variance {result.variance_before:.6g} -> {result.variance_after:.6g}. "
        f"Wrote {csv_path}."
    )
    if result.solver_status not in SUCCESS_STATUS_LABELS:
        print(
            "WARNING: solver did not report a successful status -- see solver_status "
            "above; the transfer table may be empty or partial.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
