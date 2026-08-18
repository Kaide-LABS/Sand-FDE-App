"""Renders the ranked LGA data-toxicity audit list as a single, self-contained
static HTML file.

Why a static HTML report instead of standing up Superset: Superset needs its
own metadata database, an admin bootstrap step, and manual chart/dashboard
authoring through its UI (or a scripted equivalent) before it can show
anything -- multiple extra moving parts to reproduce a single ranked table and
one bar chart. This generator produces the identical output for every stranger
who runs it, with one command, no additional service to operate, and nothing
to click through to configure. See README.md for the full trade-off
discussion; this was a deliberate choice, not a shortcut taken for lack of
time.
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

MARTS_SCHEMA = "dbt_marts"  # dbt: base schema "dbt" + custom schema "marts"
REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "data_snapshots" / "toxicity_audit_report.html"
)


class ToxicityAuditRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: int
    lga_name: str
    grid3_population_estimate: float | None
    latest_year: int | None
    completeness_fraction: float | None
    prior_year_completeness_fraction: float | None
    reporting_attrition_flag: bool | None
    impossible_incident_count: int
    extreme_impossible_incident_count: int
    distinct_indicators_affected: int
    max_reported_coverage_pct: float | None
    biological_impossibility_flag: bool
    toxicity_score: int
    toxicity_reasons: str | None


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://katsina:katsina@localhost:5442/katsina_data_quality",
    )


def fetch_audit_rows() -> list[ToxicityAuditRow]:
    query = f"""
        select
            location_id, lga_name, grid3_population_estimate, latest_year,
            completeness_fraction, prior_year_completeness_fraction,
            reporting_attrition_flag, impossible_incident_count,
            extreme_impossible_incident_count, distinct_indicators_affected,
            max_reported_coverage_pct, biological_impossibility_flag,
            toxicity_score, toxicity_reasons
        from {MARTS_SCHEMA}.lga_data_toxicity_audit
        order by toxicity_score desc, lga_name asc
    """
    with psycopg.connect(_database_url(), row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return [ToxicityAuditRow.model_validate(row) for row in rows]


def _bar_width_pct(score: int, max_score: int) -> float:
    if max_score <= 0:
        return 0.0
    return round((score / max_score) * 100, 1)


def render_html(rows: list[ToxicityAuditRow]) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    max_score = max((r.toxicity_score for r in rows), default=0)
    flagged_count = sum(1 for r in rows if r.toxicity_score > 0)

    bar_rows = "\n".join(
        f"""
        <div class="bar-row">
          <div class="bar-label">{html.escape(r.lga_name)}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{_bar_width_pct(r.toxicity_score, max_score)}%"></div>
          </div>
          <div class="bar-value">{r.toxicity_score}</div>
        </div>"""
        for r in rows
    )

    table_rows = "\n".join(
        f"""
        <tr>
          <td>{i + 1}</td>
          <td>{html.escape(r.lga_name)}</td>
          <td class="num">{r.toxicity_score}</td>
          <td>{"yes" if r.reporting_attrition_flag else "no"}</td>
          <td>{"yes" if r.biological_impossibility_flag else "no"}</td>
          <td class="num">{r.impossible_incident_count}</td>
          <td class="num">{"" if r.completeness_fraction is None else f"{r.completeness_fraction * 100:.1f}%"}</td>
          <td class="num">{"" if r.grid3_population_estimate is None else f"{r.grid3_population_estimate:,.0f}"}</td>
          <td class="reasons">{html.escape(r.toxicity_reasons or "")}</td>
        </tr>"""
        for i, r in enumerate(rows)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Katsina LGA Data-Toxicity Audit</title>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --border: #2a2f3a; --text: #e8eaed;
    --muted: #9aa4b2; --accent: #e0763c; --accent-soft: #4a3226;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 2.5rem 1.5rem;
    font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 0.25rem; font-size: 0.95rem; }}
  .meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 1.75rem; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 1.25rem 1.5rem; margin-bottom: 1.75rem;
  }}
  .panel h2 {{ font-size: 1rem; margin: 0 0 1rem 0; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.04em; font-weight: 600; }}
  .bar-row {{ display: grid; grid-template-columns: 120px 1fr 32px; align-items: center; gap: 0.75rem;
    margin-bottom: 0.4rem; font-size: 0.82rem; }}
  .bar-label {{ color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bar-track {{ background: #23262f; border-radius: 4px; height: 12px; overflow: hidden; }}
  .bar-fill {{ background: var(--accent); height: 100%; border-radius: 4px; }}
  .bar-value {{ text-align: right; color: var(--muted); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.7rem;
    letter-spacing: 0.03em; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.reasons {{ color: var(--muted); max-width: 320px; }}
  tr:hover td {{ background: #1c2028; }}
  .footnote {{ color: var(--muted); font-size: 0.78rem; line-height: 1.5; }}
  .badge {{ display: inline-block; background: var(--accent-soft); color: var(--accent);
    border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.75rem; font-weight: 600; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Katsina State LGA Data-Toxicity Audit</h1>
  <div class="subtitle">Ranked by how little the underlying MSDAT reporting for each LGA can be
    trusted -- not a health-outcomes dashboard.</div>
  <div class="meta">Generated {html.escape(generated_at)} &middot;
    <span class="badge">{flagged_count} / {len(rows)} LGAs flagged</span></div>

  <div class="panel">
    <h2>Toxicity score by LGA</h2>
    {bar_rows}
  </div>

  <div class="panel">
    <h2>Full audit list</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>LGA</th><th>Score</th><th>Attrition?</th><th>Impossible?</th>
          <th>Impossible incidents</th><th>Latest completeness</th>
          <th>GRID3 population</th><th>Why</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <p class="footnote">
    toxicity_score = 3 &times; reporting_attrition_flag + impossible_incident_count
    + 2 &times; extreme_impossible_incident_count. Reporting-volume attrition and
    biological-impossibility thresholds, and their sourcing (Gombe State DHIS2 study;
    GRID3/WorldPop population baselines; MSDAT's own indicator-denominator metadata),
    are documented in warehouse/dbt/models/marts/ and README.md. This report reflects
    whatever MSDAT and GRID3 returned at the moment the pipeline was last run.
  </p>
</div>
</body>
</html>
"""


def main() -> int:
    rows = fetch_audit_rows()
    if not rows:
        print("No rows in the toxicity audit mart -- run `dbt run` first.", file=sys.stderr)
        return 1
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_html(rows), encoding="utf-8")
    print(f"Wrote {REPORT_PATH} ({len(rows)} LGAs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
