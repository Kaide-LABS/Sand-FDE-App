"""Renders the optimizer's output (ULTIMATE_PRD.md Sec.4) as a single,
self-contained static HTML report: the transfer table, the before/after
variance (both numbers, so a reviewer can independently recompute --
acceptance criterion 4), the floor-labeling disclosure (acceptance criterion
3's documentation requirement), the 26-covered-LGA list with Guzamala's
exclusion stated explicitly (ULTIMATE_PRD.md Sec.2 finding 9), and the
insecure-ward-flag section explicitly marked **not yet implemented**, with
the reason -- never silently omitted, never a placeholder that reads as
"checked, found nothing" (ULTIMATE_PRD.md Sec.8, PHASE_1_SPEC.md Sec.6 step
8, Sec.7).

Why a static HTML report, not Superset: the same disproportionate-
operational-surface argument
../artifact-one-data-quality/viz/generate_report.py's own "Why a static
HTML report, not Superset" docstring already made applies at least as
strongly here -- the deliverable is one transfer table and one before/after
ratio comparison, not a multi-chart dashboard.

# Implements PHASE_1_SPEC.md Sec.6 step 8, Sec.7 (Failure-Mode Guards).
"""

from __future__ import annotations

import html
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict

from optimizer.solve import SUCCESS_STATUS_LABELS

MARTS_SCHEMA = "dbt_marts"  # dbt: base schema "dbt" + custom schema "marts"
REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "data_snapshots" / "borno_hr_reallocation_report.html"
)

# The 26 LGAs PDF Table 1 lists (ULTIMATE_PRD.md Sec.2 finding 9) -- the
# optimizer's entire universe. Borno State officially has 27 LGAs; Guzamala
# is the one absent from the source document's own Table 1, not a gap this
# pipeline introduced. Named as a fixed, documented list (not derived from a
# live query) so the coverage-disclosure section below can always render
# this exact statement, independent of how many allocation rows a given run
# happens to return -- the report must be able to say explicitly which LGAs
# it expects even in a degenerate run.
COVERED_LGAS: tuple[str, ...] = (
    "ABADAM", "ASKIRA/UBA", "BAMA", "BAYO", "BIU", "CHIBOK", "DAMBOA", "DIKWA",
    "GUBIO", "GWOZA", "HAWUL", "JERE", "KAGA", "KALA/BALGE", "KONDUGA", "KUKAWA",
    "KWAYA KUSAR", "MAFA", "MAGUMERI", "MAIDUGURI", "MARTE", "MOBBAR", "MONGUNO",
    "NGALA", "NGANZAI", "SHANI",
)  # fmt: skip
EXCLUDED_LGA = "GUZAMALA"


class TransferRow(BaseModel):
    """One row of `results.transfer_proposals` for the latest run."""

    model_config = ConfigDict(extra="forbid")

    cadre: str
    from_lga: str
    to_lga: str
    headcount: int


class AllocationRow(BaseModel):
    """One row of `results.lga_allocations` for the latest run."""

    model_config = ConfigDict(extra="forbid")

    lga: str
    population_proxy: float
    grand_total_before: int
    grand_total_after: int
    ratio_before: float
    ratio_after: float


class RunSummary(BaseModel):
    """One row of `results.optimization_runs` for the latest run."""

    model_config = ConfigDict(extra="forbid")

    run_at: datetime
    variance_before: float
    variance_after: float
    solver_status: str


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://borno:borno@localhost:5443/borno_hr_reallocation",
    )


def fetch_latest_run() -> tuple[RunSummary, list[TransferRow], list[AllocationRow]]:
    """Fetch the most recent optimizer run's summary, transfers, and
    allocations. Raises `RuntimeError` if no run has been written yet.
    """
    with psycopg.connect(_database_url(), row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "select run_at, variance_before, variance_after, solver_status "
            "from results.optimization_runs order by run_at desc limit 1"
        )
        run_row = cur.fetchone()
        if run_row is None:
            raise RuntimeError(
                "No rows in results.optimization_runs -- run `python -m optimizer.main` first."
            )
        run_summary = RunSummary.model_validate(run_row)

        cur.execute(
            "select cadre, from_lga, to_lga, headcount from results.transfer_proposals "
            "where run_at = %s order by from_lga, to_lga, cadre",
            (run_summary.run_at,),
        )
        transfers = [TransferRow.model_validate(r) for r in cur.fetchall()]

        cur.execute(
            "select lga, population_proxy, grand_total_before, grand_total_after, "
            "ratio_before, ratio_after from results.lga_allocations where run_at = %s "
            "order by lga",
            (run_summary.run_at,),
        )
        allocations = [AllocationRow.model_validate(r) for r in cur.fetchall()]

    return run_summary, transfers, allocations


def _transfer_table_rows(transfers: list[TransferRow]) -> str:
    if not transfers:
        return '<tr><td colspan="4" class="empty">No transfers proposed this run.</td></tr>'
    return "\n".join(
        f"""
        <tr>
          <td>{html.escape(t.cadre)}</td>
          <td>{html.escape(t.from_lga)}</td>
          <td>{html.escape(t.to_lga)}</td>
          <td class="num">{t.headcount}</td>
        </tr>"""
        for t in transfers
    )


def _allocation_table_rows(allocations: list[AllocationRow]) -> str:
    return "\n".join(
        f"""
        <tr>
          <td>{html.escape(a.lga)}</td>
          <td class="num">{a.grand_total_before}</td>
          <td class="num">{a.grand_total_after}</td>
          <td class="num">{a.population_proxy:,.0f}</td>
          <td class="num">{a.ratio_before:.6f}</td>
          <td class="num">{a.ratio_after:.6f}</td>
        </tr>"""
        for a in allocations
    )


def _coverage_disclosure_html(allocations: list[AllocationRow]) -> str:
    covered = ", ".join(html.escape(lga) for lga in COVERED_LGAS)
    reported = {a.lga for a in allocations}
    missing_from_run = sorted(set(COVERED_LGAS) - reported)
    run_note = ""
    if missing_from_run:
        run_note = (
            '<p class="warn">This run\'s own output is additionally missing: '
            f"{html.escape(', '.join(missing_from_run))} -- investigate before treating "
            "this run's output as complete.</p>"
        )
    return f"""
    <p>This optimizer covers exactly the <strong>26 LGAs</strong> Borno State's own PHC
    Workers Baseline Mapping Exercise report (Table 1, p.21-22) lists: {covered}.</p>
    <p class="callout"><strong>{html.escape(EXCLUDED_LGA)} is explicitly excluded</strong> --
    it is entirely absent from Table 1 in the primary source document itself, not an
    assessment result. Borno State officially has 27 LGAs; the source document's own
    per-LGA current-headcount table lists only 26. {html.escape(EXCLUDED_LGA)} has zero
    current-headcount data in this dataset and cannot be a transfer source or destination
    in this phase -- not because it doesn't need staff (plausibly the opposite, given its
    documented severe conflict exposure), but because the primary source provides no data
    for it. Do not read {html.escape(EXCLUDED_LGA)}'s absence from this report as "assessed,
    found not to need staff."</p>
    {run_note}
    """


def render_html(
    run_summary: RunSummary,
    transfers: list[TransferRow],
    allocations: list[AllocationRow],
) -> str:
    """Render the full static HTML report."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    run_at = run_summary.run_at.strftime("%Y-%m-%d %H:%M UTC")
    improved = run_summary.variance_after < run_summary.variance_before
    solver_succeeded = run_summary.solver_status in SUCCESS_STATUS_LABELS

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Borno State PHC Worker Reallocation -- Transfer Proposal</title>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --border: #2a2f3a; --text: #e8eaed;
    --muted: #9aa4b2; --accent: #3c8ce0; --accent-soft: #1e3350;
    --warn: #e0a83c; --warn-soft: #4a3a1e; --ok: #3ce07a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 2.5rem 1.5rem;
    font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1rem; margin: 0 0 1rem 0; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.04em; font-weight: 600; }}
  .subtitle {{ color: var(--muted); margin-bottom: 0.25rem; font-size: 0.95rem; }}
  .meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 1.75rem; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 1.25rem 1.5rem; margin-bottom: 1.75rem;
  }}
  .panel.unimplemented {{ border-color: var(--warn); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.7rem;
    letter-spacing: 0.03em; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.empty {{ color: var(--muted); text-align: center; padding: 1rem; }}
  tr:hover td {{ background: #1c2028; }}
  p {{ line-height: 1.55; font-size: 0.88rem; color: var(--text); }}
  p.callout {{ background: var(--accent-soft); border-left: 3px solid var(--accent);
    padding: 0.75rem 1rem; border-radius: 4px; }}
  p.warn {{ background: var(--warn-soft); border-left: 3px solid var(--warn);
    padding: 0.75rem 1rem; border-radius: 4px; }}
  .variance-row {{ display: flex; gap: 2rem; align-items: baseline; margin-bottom: 0.75rem; }}
  .variance-value {{ font-size: 1.6rem; font-variant-numeric: tabular-nums; }}
  .variance-label {{ color: var(--muted); font-size: 0.8rem; }}
  .arrow {{ color: var(--muted); font-size: 1.2rem; }}
  .badge {{ display: inline-block; border-radius: 4px; padding: 0.1rem 0.5rem;
    font-size: 0.75rem; font-weight: 600; }}
  .badge.ok {{ background: #1e4a30; color: var(--ok); }}
  .badge.warn {{ background: var(--warn-soft); color: var(--warn); }}
  .footnote {{ color: var(--muted); font-size: 0.78rem; line-height: 1.5; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Borno State PHC Worker Reallocation -- Transfer Proposal</h1>
  <div class="subtitle">A draft offered for review, not a prescription -- Human-in-the-Loop
    (ULTIMATE_PRD.md Sec.9). A human SPHCDB HR Director reviews and executes; this table does
    not.</div>
  <div class="meta">Report generated {html.escape(generated_at)} from optimizer run
    {html.escape(run_at)} &middot;
    <span class="badge {"ok" if solver_succeeded else "warn"}">
      solver status: {html.escape(run_summary.solver_status)}</span></div>

  <div class="panel">
    <h2>Before / after staff-to-population ratio variance</h2>
    <div class="variance-row">
      <div><div class="variance-value">{run_summary.variance_before:.8g}</div>
        <div class="variance-label">before</div></div>
      <div class="arrow">&rarr;</div>
      <div><div class="variance-value">{run_summary.variance_after:.8g}</div>
        <div class="variance-label">after</div></div>
      <div><span class="badge {"ok" if improved else "warn"}">
        {"improved" if improved else "NOT improved"}</span></div>
    </div>
    <p class="footnote">Population variance of `grand_total / population_proxy` across all 26
      covered LGAs, computed independently in optimizer/verify.py from the transfer list itself
      -- not read back from the solver's own objective. The solver's own objective minimizes a
      <em>linear</em> sum-of-absolute-deviations proxy (a genuine linear quantity in the decision
      variables); this variance is the <em>quadratic</em> statistic the acceptance criteria
      actually require, computed post-hoc so a reviewer can reproduce it with a spreadsheet
      (ULTIMATE_PRD.md Sec.4). A reviewer can recompute both numbers directly from the "Full
      allocation" table below. The solver itself is run with a disclosed 2% relative MIP-gap
      tolerance and a time limit (optimizer/solve.py) rather than an unbounded search for exact
      global optimality -- the actual problem size exhibits real solution symmetry (many
      differently-routed transfer sets achieve the identical net effect per LGA), which made
      proving a strict 0%-gap optimum take minutes without converging in testing, while a
      solution proven within 2% of optimal is found in seconds. Every check on this page
      (zero-sum, the per-cadre floor, and variance strictly improving) holds for the solution
      actually returned regardless of this tolerance; "solver status" above states this
      explicitly rather than reading as an unconditional optimality claim.</p>
  </div>

  <div class="panel">
    <h2>Proposed transfers ({len(transfers)})</h2>
    <table>
      <thead><tr><th>Cadre</th><th>From LGA</th><th>To LGA</th><th>Headcount</th></tr></thead>
      <tbody>
        {_transfer_table_rows(transfers)}
      </tbody>
    </table>
    <p class="footnote">Payroll is provably zero-sum: sum every headcount column above by
      cadre-from and by cadre-to and they match exactly -- checkable with a spreadsheet SUM, no
      domain knowledge required (ULTIMATE_PRD.md Sec.4). This is true by construction of the
      optimizer's decision variables, independently re-verified in optimizer/verify.py.</p>
  </div>

  <div class="panel">
    <h2>Full allocation, all 26 covered LGAs</h2>
    <table>
      <thead>
        <tr><th>LGA</th><th>Grand total before</th><th>Grand total after</th>
          <th>Population proxy</th><th>Ratio before</th><th>Ratio after</th></tr>
      </thead>
      <tbody>
        {_allocation_table_rows(allocations)}
      </tbody>
    </table>
    <p class="footnote">Population proxy is <strong>derived from PDF Fig. 1 & Fig. 2, not
      directly reported</strong> (ULTIMATE_PRD.md Sec.3.2) -- no ward- or LGA-level population
      figure appears anywhere in the source document.</p>
  </div>

  <div class="panel">
    <h2>LGA coverage -- which 26, and why not 27</h2>
    {_coverage_disclosure_html(allocations)}
  </div>

  <div class="panel">
    <h2>The per-cadre floor -- what it is and isn't</h2>
    <p class="callout">The floor used here (a transfer cannot reduce an LGA's headcount for a
      given cadre below 1, if that LGA currently has 1 or more of that cadre) is
      <strong>this artifact's own, disclosed, artifact-imposed safety constraint</strong> --
      chosen by the builder to prevent the optimizer from proposing something absurd, like
      eliminating a cadre entirely from an LGA that currently has it. It is
      <strong>not</strong> NPHCDA's minimum staffing standard (PDF Table 6, p.26 -- e.g. 4
      Nurses/Midwives, 6 JCHEWs, 3 CHEWs per facility) and not a Sand-specified requirement.
      Meeting this floor is <strong>not</strong> the same as meeting NPHCDA's minimum standard --
      most LGAs already fall below that aspirational target before any transfer happens, and
      pure reallocation of the existing workforce cannot achieve it (that requires the PDF's
      separate 2,860-worker, five-year recruitment plan, which this artifact does not model).
      The floor applies per cadre independently, never as a combined-total floor across an LGA's
      cadres.</p>
  </div>

  <div class="panel unimplemented">
    <h2>Insecure-ward flag -- not yet implemented</h2>
    <p class="warn">Borno's own baseline report states that 38 wards currently have no
      operational PHC facility, "primarily because of the security situation" (p.12), and that
      these insecure wards are "distributed across several LGAs in the most conflict-affected
      zones" -- but the source document publishes <strong>no per-LGA breakdown</strong> of which
      LGAs those 38 wards fall in. This flag is <strong>not yet implemented</strong>, not
      silently omitted and not a false-negative "no flags found": there is currently no sourced
      mapping from the 38 insecure wards to LGAs to check any proposed transfer against.</p>
    <p>This is deliberately <strong>not</strong> approximated by proxying from facility-coverage
      gaps (e.g. treating Kala Balge, Marte, or Biu -- named in the PDF, p.13, as having "the
      lowest coverage" -- as a stand-in for insecurity). Low facility coverage and ward-level
      insecurity are correlated in the report's own narrative but are not the same measured
      quantity; treating them as interchangeable would silently launder an assumption into a
      fact (ULTIMATE_PRD.md Sec.2 finding 4). Resolving this requires either a supplementary
      section of the underlying State HRH database or direct confirmation from Borno SPHCDB
      (ULTIMATE_PRD.md Sec.8) -- an open architecture question, not a resolved one. Until then,
      any proposed transfer above should be screened by a human reviewer with local knowledge of
      which LGAs are conflict-affected before being treated as more than a decision-support
      draft.</p>
  </div>

  <p class="footnote">
    Source: Borno State Ministry of Health and Human Services / Borno State Primary Healthcare
    Development Board, <em>Report of Baseline Mapping Exercise for Primary Healthcare Workers in
    Borno State</em>, February 2025 (reference/borno_phc_baseline.pdf). Every figure in this
    report traces to that PDF's own Table 1/4/6/Figures 1-2 or the disclosed population-proxy
    derivation in ULTIMATE_PRD.md Sec.3.2 -- no invented, estimated, or LLM-recalled figure
    stands in for a real one anywhere in this pipeline (ULTIMATE_PRD.md Sec.6).
  </p>
</div>
</body>
</html>
"""


def main() -> int:
    """CLI entry point: fetch the latest run and write the static HTML report."""
    run_summary, transfers, allocations = fetch_latest_run()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_html(run_summary, transfers, allocations), encoding="utf-8")
    print(f"Wrote {REPORT_PATH} ({len(transfers)} transfers, {len(allocations)} LGAs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
