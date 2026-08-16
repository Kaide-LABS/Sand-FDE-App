# PHASE_1_SPEC.md — Borno State PHC Worker Reallocation Optimizer

Built from `ULTIMATE_PRD.md` (the modernised PRD) — read that first, especially §2's
MODERNIZATION CHANGELOG and §4's optimizer formulation, before touching any file below. This spec
does not repeat the PRD's reasoning; it turns it into files, functions, and tests.

## §0 Phase Plan Header

**Phase 1 of 1.** The confirmed scope (`.claude/loopr/baby_prd.md`) is narrow enough — a transfer
table plus a reported before/after variance, both statically generated from a one-time PDF
extraction — that splitting it into multiple phases would add coordination overhead without
engineering benefit. This is a disclosed architectural call, not a default: if genuine rework
pushes scope past what's listed here, a real `PHASE_2_SPEC.md` gets drafted rather than silently
expanding this one.

---

## §1 Files Added or Modified

```
pyproject.toml
.gitignore                                    (project-specific — mirrors artifact-one-data-quality's split)
docker-compose.yml
docker/Dockerfile.pipeline
docker/Dockerfile.airflow
ingestion/
  __init__.py
  models.py                                   Pydantic models for all 5 checked-in CSVs
  config.py                                   Cadre lists, citations, the Phase-1 4-cadre scope constant
  load_csv.py                                 Loads data/*.csv -> Postgres raw schema
  db.py                                        Postgres connection + raw-schema DDL
warehouse/dbt/
  dbt_project.yml
  profiles.yml
  models/staging/
    stg_lga_current_staffing.sql              from raw.lga_current_staffing
    stg_state_staffing_gap.sql                 from raw.state_staffing_gap
    stg_lga_population_proxy.sql                derives population per LGA (PRD Sec.3.2) + reconciliation test
  models/marts/
    mart_reallocation_input.sql                one row per LGA: grand_total, 4-cadre headcounts, population proxy, ratio
    _marts.yml                                  schema tests
  seeds/                                        (none — data/ CSVs are loaded via ingestion/load_csv.py, not dbt seed,
                                                  since they need the citation-comment stripping load_csv.py does)
optimizer/
  __init__.py
  models.py                                    Pydantic: TransferProposal, OptimizationResult, LgaAllocation
  formulate.py                                  Builds the MILP (PRD Sec.4) from mart_reallocation_input
  solve.py                                       Calls scipy.optimize.milp; returns raw solution
  verify.py                                      Independent recomputation: zero-sum, floor, variance -- never
                                                  trusts the solver's own status/report alone (PRD Sec.11)
  main.py                                         Orchestrates: pull mart data -> formulate -> solve -> verify ->
                                                  write results to Postgres + CSV
viz/
  generate_report.py                            Static HTML report: transfer table, before/after variance,
                                                  covered-LGA disclosure, insecure-ward-flag status disclosure,
                                                  floor-labeling disclosure
airflow/dags/
  borno_hr_reallocation_dag.py                  On-demand DAG (schedule=None): load_csv -> dbt seed/run/test ->
                                                  optimizer.main -> generate_report
tests/
  test_csv_sums.py                              Asserts the checked-in CSVs' own internal sums match the
                                                  documented expected values (3,915 / 2,860 / 329 / 26 rows each)
                                                  -- catches an accidental future edit to data/*.csv silently
                                                  breaking agreement with the PDF's own totals
  test_zero_sum.py                              Independent recomputation of acceptance criterion 1
  test_floor_constraint.py                      Independent recomputation of acceptance criterion 3
  test_lga_coverage_disclosure.py               Asserts the rendered report explicitly lists all 26 covered
                                                  LGAs and explicitly names Guzamala's exclusion
data/*.csv                                      Already created and verified (see ULTIMATE_PRD.md Sec.2
                                                  finding 9, Sec.3.1) — do not regenerate or re-extract from the
                                                  PDF; these five files are the confirmed, checked-in ground truth.
reference/borno_phc_baseline.pdf                Already checked in.
```

---

## §2 Dependencies (exact pinned versions)

```toml
[project]
dependencies = [
    "pydantic>=2.6",
    "psycopg[binary]>=3.1",
    "scipy>=1.18,<2.0",       # scipy.optimize.milp (HiGHS-backed), verified current at 1.18.0
    "dbt-postgres>=1.7,<1.8", # matches artifact-one-data-quality's pin -- disclosed consistency
                               # choice, not staleness (ULTIMATE_PRD.md Sec.7)
]
[project.optional-dependencies]
dev = ["mypy>=1.9", "ruff>=0.4", "pytest>=8.0"]
```

No `requests` (no live API — the PDF is a one-time, checked-in extraction). No `ortools` in Phase
1 (PRD §4: documented fallback only, not used). No PostGIS, no `geopandas`, no spatial library of
any kind (PRD §3.3 — nothing in this artifact's confirmed scope is a geometry).

---

## §3 Pydantic Schemas

All `model_config = ConfigDict(extra="forbid")`, matching Artifact One's convention exactly.

```python
# ingestion/models.py
class LgaCurrentStaffing(BaseModel):
    lga: str
    community_health_officer: int = Field(ge=0)
    community_health_extension_worker: int = Field(ge=0)
    junior_community_health_extension_worker: int = Field(ge=0)
    health_information_management: int = Field(ge=0)
    medical_doctor: int = Field(ge=0)
    medical_laboratory_scientist: int = Field(ge=0)
    nurse_midwife: int = Field(ge=0)
    pharmacist: int = Field(ge=0)
    total_core_health_workers: int = Field(ge=0)
    total_support_health_workers: int = Field(ge=0)
    grand_total: int = Field(ge=0)

class StateStaffingGap(BaseModel):
    phc_personnel: str
    minimum_no_per_phc: int = Field(ge=0)
    total_required_across_state: int = Field(ge=0)
    total_available_across_state: int = Field(ge=0)
    gap_across_state: int = Field(ge=0)

class LgaFacilityCount(BaseModel):
    lga: str
    facility_count: int = Field(ge=0)

class LgaFacilityDensity(BaseModel):
    lga: str
    density_per_10k_population: float = Field(ge=0)

class NphcdaMinimumStandard(BaseModel):
    minimum_standard: str
    minimum_no_per_phc: int = Field(ge=0)
```

```python
# optimizer/models.py
PHASE_1_CADRES = ("community_health_officer", "community_health_extension_worker",
                   "junior_community_health_extension_worker", "nurse_midwife")
# The four exactly-matched cadres (ULTIMATE_PRD.md Sec.5). Pharmacist/Medical Laboratory
# Scientist/Health Information Management/Medical Doctor are NEVER decision-variable cadres in
# Phase 1 -- if a future change adds them, it must also add the disclosed name-mapping assumption
# ULTIMATE_PRD.md Sec.5 explicitly deferred, not silently widen this tuple.

class TransferProposal(BaseModel):
    cadre: Literal[PHASE_1_CADRES]
    from_lga: str
    to_lga: str
    headcount: int = Field(gt=0)

class LgaAllocation(BaseModel):
    lga: str
    population_proxy: float                  # PRD Sec.3.2 -- derived, always rendered with that label
    grand_total_before: int
    grand_total_after: int
    ratio_before: float
    ratio_after: float

class OptimizationResult(BaseModel):
    transfers: list[TransferProposal]
    allocations: list[LgaAllocation]          # all 26 covered LGAs, always -- never filtered to only
                                               # the ones that changed, so the coverage disclosure
                                               # (PRD Sec.11's Guzamala row) has a complete list to render
    variance_before: float
    variance_after: float
    solver_status: str
```

---

## §4 API Route Signatures

**N/A.** The confirmed boundary (`baby_prd.md`) is explicit: a static, locally-generated output,
not a service. No HTTP API surface exists in this phase. Stating this explicitly here rather than
omitting the section, per `ULTIMATE_PRD.md`'s own instruction not to silently drop a required
template section.

---

## §5 Migrations

**N/A** for the same reason — `raw`/`stg`/`marts` schemas are created by `ingestion/db.py`'s DDL
and dbt's own model materialization, not a migration framework; matches Artifact One's own
`ingestion/db.py` pattern exactly, no new tooling introduced.

---

## §6 Implementation Logic Flow

1. **`ingestion/load_csv.py`** — reads each of the five `data/*.csv` files (stripping `#`-prefixed
   citation comment lines), validates every row against its Pydantic model (§3), inserts into
   `raw.*` tables. Fails loudly (raises, does not skip) on any row that fails Pydantic validation —
   these five files are the confirmed ground truth; a validation failure here means the CSV was
   edited incorrectly, not that a row should be silently dropped.
2. **dbt staging** — `stg_lga_current_staffing.sql` is a thin pass-through (already-clean data, no
   dedup logic needed, unlike Artifact One's MSDAT staging which handles multi-record dedup).
   `stg_lga_population_proxy.sql` computes `facility_count / density_per_10k * 10000` per LGA, and
   includes a dbt test asserting the population-weighted mean of the 26 derived values reconciles
   with the PDF's own stated state-level figures (6.9M population, 0.8/10k density, 329 facilities)
   to within a documented tolerance (start at ±5%; tighten once real reconciliation is observed).
3. **dbt marts** — `mart_reallocation_input.sql` joins current staffing (4-cadre subset + grand
   total) with the population proxy, producing exactly 26 rows (one per covered LGA), each with
   `ratio = grand_total / population_proxy`.
4. **`optimizer/formulate.py`** — reads `mart_reallocation_input`, builds the MILP per
   `ULTIMATE_PRD.md` §4 exactly: decision variables `x[i][j][c]` for the 4 Phase-1 cadres over the
   26×25 LGA-pair space, the per-cadre floor upper bound (`max(current[k][c] - 1, 0)`), and the
   linear L1-deviation objective from the fixed `target_ratio`.
5. **`optimizer/solve.py`** — calls `scipy.optimize.milp` (HiGHS backend), returns the raw
   integer solution and solver status. Any non-optimal status is surfaced in `OptimizationResult`,
   never silently treated as success.
6. **`optimizer/verify.py`** — **never trusts the solver's own report alone** (PRD §11's own
   discipline, applied to the code that ships, not just the human-facing acceptance criteria):
   independently recomputes, from the raw `x[i][j][c]` values, (a) that inbound headcount sums to
   outbound headcount exactly, (b) that no LGA/cadre combination that started ≥1 ends below 1, (c)
   population variance of `ratio` before and after, using plain arithmetic, not calling back into
   the solver. Raises if (a) or (b) fail — these should be structurally impossible per §4's design,
   so a failure here means a bug in `formulate.py`, not a data problem.
7. **`optimizer/main.py`** — orchestrates 4-6, writes `TransferProposal`/`LgaAllocation` rows back
   to Postgres and a dated CSV snapshot (matching Artifact One's `data_snapshots/` pattern).
8. **`viz/generate_report.py`** — static HTML: the transfer table, the before/after variance
   (both numbers, so a reviewer can independently recompute — acceptance criterion 4), the
   floor-labeling disclosure (acceptance criterion 3's documentation requirement), the 26-covered-
   LGA list with Guzamala's exclusion stated explicitly (PRD §11's Guzamala row), and the
   insecure-ward-flag section explicitly marked **not yet implemented** with the reason (PRD §8's
   open architecture question) — never silently omitted, never a placeholder that reads as "checked,
   found nothing."

---

## §7 Failure-Mode Guards

Restates `ULTIMATE_PRD.md` §11's table as concrete per-file guards:

| Guard | Where |
|---|---|
| Pydantic `extra="forbid"` rejects any CSV row with an unexpected column | `ingestion/models.py` |
| `test_csv_sums.py` fails the build if `data/*.csv`'s own sums drift from documented values | `tests/` |
| `verify.py` independently recomputes zero-sum and floor rather than trusting `solve.py`'s status | `optimizer/verify.py` |
| `stg_lga_population_proxy.sql`'s reconciliation test | `warehouse/dbt/models/staging/` |
| `test_lga_coverage_disclosure.py` asserts the rendered HTML names all 26 LGAs and Guzamala's exclusion | `tests/` |
| The insecure-ward section is a required, non-empty block in `generate_report.py` — build fails if the template renders it empty rather than with the explicit "not yet implemented" disclosure | `viz/generate_report.py` |

---

## §8 Phase Acceptance Criteria

Restates `baby_prd.md`'s confirmed criteria (as amended 2026-08-16), made concrete and testable:

1. `test_zero_sum.py` — for the generated `OptimizationResult`, `sum(headcount for t in transfers
   where from_lga==k) == sum(headcount for t in transfers where to_lga==k)` summed appropriately;
   passes trivially by construction (§4) but the test exists to catch a bug in reading back the
   solver's output, not to validate the model design itself.
2. `test_floor_constraint.py` — for every `(lga, cadre)` pair in the 4-cadre Phase-1 scope, if
   `current[lga][cadre] >= 1` then `current[lga][cadre] - outbound[lga][cadre] >= 1`.
3. `test_variance_improved.py` — `variance_after < variance_before`, both independently
   recomputed in the test from `mart_reallocation_input` and the transfer list, not read from
   `OptimizationResult`'s own self-reported fields.
4. `test_lga_coverage_disclosure.py` — the rendered HTML contains all 26 LGA names and an explicit
   sentence naming Guzamala's exclusion as a primary-source data gap.
5. `test_floor_labeling_disclosure.py` — the rendered HTML/README explicitly states the floor is
   this artifact's own constraint, not NPHCDA's minimum standard, and explicitly distinguishes it
   from Table 6's aspirational hiring target.
6. **Manual, not automatable:** confirm the insecure-ward section reads as "not yet implemented,
   here's why" rather than either silent omission or a false-negative "no flags" — this is a
   posture/voice check (`context.md`'s confirmed soft-context note), not a string match.

---

## §9 Explicit NON-GOALS

Restates `baby_prd.md`'s confirmed scope edges, plus this phase's own additions:

- No Pharmacist/Pharmacy-Technician or Medical-Laboratory-Scientist/Lab-Technician cadre mapping
  (ULTIMATE_PRD.md §5) — deferred to a genuine future phase, not built here even partially.
- No Guzamala data synthesis of any kind — its absence is disclosed, never filled by interpolation,
  averaging, or any other invented figure.
- No insecure-ward flag implementation until the LGA mapping (§8 of the PRD) is actually sourced —
  the section exists in the report template with an explicit "not yet implemented" state, not a
  half-built heuristic.
- No multi-state generalization, no recruitment modeling, no feasibility scoring, no live HR
  integration — unchanged from `baby_prd.md`.
