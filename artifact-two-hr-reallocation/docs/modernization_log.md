# Modernization log

Model strings and pinned dependency versions this build used, each with its
citation. Created as part of Phase 1 per PHASE_1_SPEC.md Sec.2's pinned
versions instruction.

This artifact makes **no LLM API calls anywhere in its optimizer's
constraint construction, solve, or verification path** (ULTIMATE_PRD.md
Sec.6, the Deterministic-Only Correctness Boundary) -- there is no "model
string" for a language model to log here. What follows is the pinned
dependency versions ULTIMATE_PRD.md Sec.4/Sec.7 already justified, restated
here as the single dated log entry this file exists to hold.

## 2026-08-16 -- Phase 1 build

| Dependency | Pin | Why | Citation |
|---|---|---|---|
| `scipy` | `>=1.18,<2.0` | `scipy.optimize.milp` (HiGHS-backed, deterministic) is this artifact's sole solver. Version 1.18.0 is current as of this build and requires Python 3.12-3.14 and NumPy >=2.0.0 -- this project's `pyproject.toml` `requires-python` and both Dockerfiles' base images (`python:3.12-slim`, `apache/airflow:2.9.3-python3.12`) are pinned accordingly as a direct consequence. | ULTIMATE_PRD.md Sec.4: "[SciPy 1.18.0](https://github.com/scipy/scipy/releases/tag/v1.18.0), released 2026-06-19, requires Python 3.12-3.14 and NumPy >=2.0.0" |
| `dbt-postgres` | `>=1.7,<1.8` | Matches `../artifact-one-data-quality`'s own pin -- a disclosed consistency choice for a two-artifact application read by the same reviewers, not staleness. Current stable as of this build is dbt-core 1.12.2; this artifact deliberately does not track it. | ULTIMATE_PRD.md Sec.7: "This artifact stays on the same 2.x Airflow / 1.7.x dbt line Artifact One already uses and has proven working" |
| Airflow (Docker image) | `apache/airflow:2.9.3-python3.12` | Same 2.9.3 release `../artifact-one-data-quality/docker/Dockerfile.airflow` pins (`apache/airflow:2.9.3-python3.11`); only the Python minor version differs, forced by the `scipy` pin above. Current stable as of this build is Airflow 3.3.0; this artifact deliberately does not track it, for the same disclosed consistency reason as the dbt pin. | ULTIMATE_PRD.md Sec.7: "current stable releases as of this drafting pass (2026-08-16) are Apache Airflow 3.3.0 ... This artifact stays on the same 2.x Airflow ... line" |
| `pydantic` | `>=2.6` | `model_config = ConfigDict(extra="forbid")` on every `BaseModel`, matching `../artifact-one-data-quality`'s convention exactly. | ULTIMATE_PRD.md Sec.6 |
| `psycopg[binary]` | `>=3.1` | Postgres driver, matching `../artifact-one-data-quality`'s own pin. | ULTIMATE_PRD.md Sec.7 |

No `requests`, no `ortools`, no PostGIS/`geopandas`/spatial library of any
kind -- PHASE_1_SPEC.md Sec.2 and ULTIMATE_PRD.md Sec.3.3 both rule these out
explicitly for this phase; restated here only as a cross-reference, not
re-justified.
