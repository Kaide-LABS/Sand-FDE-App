# CLONE_TEST_FINDINGS.md

Release-readiness check, not a build task. Findings first, in the order requested — nothing in
this repository was modified to produce the findings themselves. A **Fixes Applied** section was
appended afterward, once the findings were reported and the user asked to act on them; it is
clearly separated from the original findings below and dated after them, not merged into the
original text.

## Method

- Tore down every Docker container, volume, and network for both projects first
  (`docker compose down -v` in both artifact directories), then confirmed via `docker ps -a` /
  `docker volume ls` that nothing named `katsina_*` / `borno_*` / `artifact-*` remained anywhere
  on the machine.
- Cloned into `C:\temp\clone-test\`, a directory with no relationship to the working checkout.
  **Cloned from the local git history** (`git clone C:\Users\hp\Sand_FDE C:\temp\clone-test`),
  not from GitHub — the repo is currently **7 commits ahead of `origin/master`**, and none of
  Artifact Two's work has been pushed. A literal `git clone https://github.com/Kaide-LABS/Sand-FDE-App.git`
  run today would get the pre-Artifact-Two state, not what this test exercises. This is stated
  here as a precondition of the test, not a code defect — but it is the single fact that most
  determines whether this repo is actually "release-ready" right now, so it goes first.
- From inside the fresh clone, followed the README(s) literally — command-by-command, no
  knowledge from having built this used to skip or correct a step. Where a literal command
  failed, that failure is recorded below and the test continued using the most reasonable
  next step (never silently "fixing" the instruction and pretending it worked as written).
- Ran both pipelines end-to-end via **both** documented paths where both exist (Airflow DAG
  orchestration, and direct `docker compose run` invocation), and ran both test suites.
- Torn down again at the end of this test; nothing from this test run was left behind.

---

## Findings

### BLOCKER — a stranger cannot get past this without asking me

**B1. `artifact-two-hr-reallocation/` has no `README.md` at all.**
The top-level `README.md` states as fact: *"Each artifact directory is self-contained: its own
README with a Quickstart... Cloning this repo and following either artifact's own README is
enough to run it end-to-end."* This is true for Artifact One and false for Artifact Two. The
directory contains `ULTIMATE_PRD.md`, `PHASE_1_SPEC.md`, `BUILD_COMPLETE.md`, and
`COMPREHENSION.md` — none of them named or shaped like a README, and nothing in the top-level
README points a reader at any of them specifically. A stranger who clones this repo, reads the
top-level README, and goes looking for "artifact two's own README with a Quickstart" per the
README's own explicit promise finds nothing. (The instructions that *do* exist — buried inside
`BUILD_COMPLETE.md`'s "Reproducing the report from a clean clone" section — turned out to be
accurate and complete once found; see the FRICTION/PASS notes below. The blocker is discoverability,
not correctness of what's there.)

**B2. The top-level `README.md` describes Artifact Two as not built.**
Verbatim, row 2 of the Artifacts table: *`artifact-two-*/` | ...final pick and directory name
TBD... | Spec/build in progress.* This is the first and only thing a stranger reads about Artifact
Two. It is stale — the directory has existed under its real name
(`artifact-two-hr-reallocation/`) with a complete, reviewed, tested build and a `BUILD_COMPLETE.md`
since before this test began — but the README was never updated after Part 1's repo restructuring,
which is the only point at which this row was ever written. A stranger reading only this file
would reasonably conclude there is nothing to look at yet and stop.

**B3. `pip install -e ".[dev]"` — the literal first command in Artifact One's own README
"Quality gates" section — fails on a fresh clone.**
```
$ pip install -e ".[dev]"
error: Multiple top-level packages discovered in a flat-layout: ['viz', 'docker', 'airflow', 'ingestion', 'warehouse', 'data_snapshots'].
```
Reproduced identically on the fresh clone; this is not new — it was already known before this
test (flagged during the original build, never fixed, and the README was never corrected to
document a workaround). A stranger following the Quality Gates section literally hits a dead
stop at the first line. **Once worked around** (install `mypy`, `ruff`, `pytest`, and the runtime
deps directly, skip the editable install), `mypy --strict`, `ruff check`, and `pytest tests/` all
run and pass cleanly — the tools themselves are fine, only the documented install command is
broken, and no workaround is documented anywhere in the repo.

---

### FRICTION — works, but the documentation is wrong, incomplete, or misleading

**F1. The README's literal `cd sand-fde-application/artifact-one-data-quality` fails.**
```
$ cd sand-fde-application/artifact-one-data-quality
bash: cd: sand-fde-application/artifact-one-data-quality: No such file or directory
```
A fresh `git clone` is not automatically named `sand-fde-application` — the actual GitHub repo is
named `Sand-FDE-App`, so a default clone produces a directory called `Sand-FDE-App`, and any user
who names their clone something else (as most do) gets a third name. Trivial for anyone with
basic git familiarity to work around (just `cd` into wherever you actually cloned), but the
instruction as literally written does not execute on any real clone, including one done exactly
by the book from the actual GitHub URL.

**F2. [CORRECTED after the initial fix pass -- see below] No `.gitattributes`; every tracked
Python/SQL/YAML file, checked out on this machine, has CRLF line endings.** Originally recorded as
a portability FRICTION item. That conclusion was wrong, and the error is worth stating plainly
rather than quietly fixing: the check that produced this finding ran `file` against *working-tree*
files, on a machine with `core.autocrlf=true`. `git show HEAD:<path> | file -` on the same files
shows the content actually **stored** in git is already LF -- `core.autocrlf=true` converts LF
(stored) to CRLF (checkout) for local editing convenience on Windows, and back on commit. A
Linux/macOS clone, with git's typical non-Windows defaults, receives LF directly; nothing about
this repo's actual, portable content was ever CRLF. `git add --renormalize .` (run as part of the
fix pass below) confirms this by finding zero files needing normalization. **The correct
classification was COSMETIC at most, confined to this one Windows checkout, not a real
cross-platform issue** -- recorded here as a correction to the test's own methodology, not
silently rewritten. A `.gitattributes` declaring `text=auto eol=lf` was still added as a genuine
improvement (it makes normalization explicit and immune to a future contributor's individual git
config, rather than relying on convention), but it fixes a defensive gap, not the bug originally
described here.

**F3. `optimizer.main`'s solver run leaks raw HiGHS debug output to stdout, unframed, on every
invocation** — via Docker and via `pytest` alike:
```
HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();
HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();
... (repeated ~10x)
```
The run still succeeds and produces the correct result — this is not an error — but it is not
mentioned anywhere in `BUILD_COMPLETE.md`, `COMPREHENSION.md`, or any code comment, and to anyone
not already specifically familiar with HiGHS's own internal logging quirks it reads exactly like
something has gone wrong mid-run.

**F4. (Disclosed as a test precondition, not a docs bug, but load-bearing for the final verdict
below.)** Nothing in this repository is on GitHub yet. See Method, above.

---

### COSMETIC — noise, does not stop anything

**C1. dbt 1.7.20 prints two deprecation warnings (`log-path`/`target-path` config deprecated) on
every single `dbt seed`/`run`/`test` invocation, for both artifacts.** Informational only, does
not affect output or exit codes.

---

## What actually passed — confirmed on the fresh clone, not assumed

**Artifact One**, via both documented paths (Airflow DAG and, separately, the raw
`docker compose run --rm pipeline ...` commands the README also gives):
- `fetch_msdat`, `fetch_grid3`, `dbt_seed`, `dbt_run`, `dbt_test`, `generate_report` — all 6 tasks
  succeeded. Live pull against the real MSDAT and GRID3/WorldPop endpoints, zero credentials,
  zero API keys, zero login of any kind — the "no Ministry credentials" claim holds from a
  genuinely cold start, not just in principle.
- Output reproduced exactly: `dbt_marts.lga_data_toxicity_audit` ranks Danja (67), Bakori (57),
  Funtua (49)... identically to every prior run.
- Once the `pip install -e` workaround (B3) is applied: `mypy --strict` clean (12 files),
  `ruff check` clean, `pytest tests/` — 3/3 passed, 0 skipped.
- The two deterministic dbt-test constraints (reporting-attrition, biological-impossibility) ran
  as part of `dbt_test` and passed (severity=warn, by design — see that repo's own README for why).

**Artifact Two**, via both documented paths (Airflow DAG *and* the direct pipeline-invocation
sequence from `BUILD_COMPLETE.md`):
- `load_csv → dbt_seed → dbt_run → dbt_test → optimize → generate_report` — all 6 tasks succeeded,
  via Airflow, on a completely fresh Postgres with zero pre-existing data.
- Zero credentials, zero network calls of any kind — the five checked-in `data/*.csv` files and
  `reference/borno_phc_baseline.pdf` are genuinely sufficient; nothing is fetched live.
- All 26 rows loaded from each of the 5 CSVs; `mart_reallocation_input` built with exactly 26 rows.
- 14/14 dbt tests passed, including `population_proxy_reconciliation`.
- Solver output reproduced exactly: `optimal_within_2pct_gap`, 70 transfers, variance
  `3.51009e-07 → 2.53575e-08` — identical to the numbers already recorded in `BUILD_COMPLETE.md`.
- The rendered report contains, confirmed by direct grep on the freshly-generated file (not the
  original build's copy): `<strong>GUZAMALA is explicitly excluded</strong>` and
  `<h2>Insecure-ward flag -- not yet implemented</h2>` with its full explanation — both required
  disclosures render exactly as specified, on a file this test generated itself.
- `pytest -v`: **16/16 passed, 0 skipped** — every acceptance-criteria test
  (`test_zero_sum.py`, `test_floor_constraint.py`, `test_variance_improved.py`,
  `test_lga_coverage_disclosure.py`, `test_floor_labeling_disclosure.py`, `test_csv_sums.py`,
  `test_verify_module.py`) ran for real and passed for real — none skipped due to a missing
  dependency or environment gap.
- `mypy` clean (22 files), `ruff check` clean, `ruff format --check` clean.
- Both artifacts' Postgres/Airflow containers ran **simultaneously** without a port or
  container-name collision (`5442`/`8080` vs `5443`/`8081`, `katsina_*` vs `borno_*`) — the
  "self-contained, don't have to run one at a time" claim holds.
- No hardcoded absolute path (`C:\Users\hp\...` or otherwise) anywhere in either artifact's
  tracked code, config, dbt profiles, or Airflow DAGs — every path that needs to resolve
  differently on a different machine does so via a bind mount, an `env_var()` default, or a
  container-internal absolute path that only ever means something inside the container.
- No environment variable referenced in code lacks a working default; no `.env` file is required
  anywhere; no global-machine Python package silently satisfied a dependency the project files
  don't declare (checked by installing into fresh, empty virtual environments each time).

---

## Verdict

**No — not as-is, and specifically because of B1/B2.**

Artifact One, on its own, passes this test cleanly: a stranger with Docker installed, pointed at
`artifact-one-data-quality/`, gets a working pipeline and a real generated report by following its
README, modulo the two FRICTION items above (both trivially recoverable by anyone who's used git
and a terminal before).

Artifact Two's actual code does not fail this test — every pipeline task, every acceptance test,
every disclosure requirement reproduced exactly, cold, twice (once via Airflow, once via direct
invocation). The failure is entirely at the documentation layer: **there is no README to follow**,
and the one document that orients a reader to the whole repository actively tells them Artifact
Two isn't built yet. A stranger who trusts the top-level README — which is the only reasonable
thing to do on a first visit — never discovers that a working Artifact Two exists at all, let
alone how to run it.

A repo that does not start is worse than no repo. Right now, for Artifact Two specifically, that's
not because it doesn't start — it's because nothing tells a stranger to try.

---

## Fixes Applied

Appended after the findings above were reported and the user asked to act on them. Each item was
fixed and then independently re-verified — re-run, not just re-read — before being marked done
here; nothing below is claimed on the strength of the fix "looking right."

**B1 (no README for Artifact Two) — fixed.** Wrote
[`artifact-two-hr-reallocation/README.md`](artifact-two-hr-reallocation/README.md), mirroring
Artifact One's README structure (Quickstart via Docker/Airflow, direct-invocation, and no-Docker
test-only paths; architecture; primary-source verification summary; data sources; the optimizer's
constraints; Accountable Autonomy level; acceptance-criteria checklist; scope boundaries; quality
gates). Verified by literally following its own Quickstart on a stopped-and-restarted stack.

**B2 (top-level README describes Artifact Two as not built) — fixed.** Updated the Artifacts table
row and intro paragraph in the top-level [`README.md`](README.md) to name
`artifact-two-hr-reallocation/` concretely, describe what it actually does, and say "Built,
verified, running" instead of "Spec/build in progress."

**B3 (`pip install -e ".[dev]"` fails on a fresh clone) — fixed, in both artifacts.** Root cause:
setuptools' flat-layout auto-discovery finds every top-level directory (`docker/`, `airflow/`,
`warehouse/`, `data_snapshots/`, ...) as a candidate package and refuses to guess. Fixed by adding
an explicit `[tool.setuptools] packages = [...]` to each artifact's `pyproject.toml` (`["ingestion",
"viz"]` for Artifact One; `["ingestion", "optimizer", "viz"]` for Artifact Two). Verified via a
fresh Python 3.13 venv in each artifact: `pip install -e ".[dev]"` now succeeds,
`mypy --strict`/`ruff check`/`pytest` all still run clean. Separately disclosed, not "fixed": on
this machine's default Python 3.14, `dbt-core`'s `cffi<2.0.0` constraint has no prebuilt wheel and
needs MSVC Build Tools to build from source — an upstream dbt-core/cffi gap with bleeding-edge
Python, unrelated to B3, out of this repo's control. Python 3.13 is unaffected.

**F1 (README's literal `cd sand-fde-application/...` fails on a real clone) — fixed, both
locations.** Changed to `cd <cloned-directory>/...` in `artifact-one-data-quality/README.md` and
in `artifact-two-hr-reallocation/BUILD_COMPLETE.md`'s own "Reproducing the report from a clean
clone" section.

**F2 (CRLF line endings) — corrected, not fixed, because the original finding was wrong.** See the
inline correction above: the check that produced this finding read *working-tree* files on a
`core.autocrlf=true` Windows checkout, not what's actually stored in git. `git show HEAD:<path> |
file -` shows the stored content is already LF; `git add --renormalize .` found zero files needing
normalization. Reclassified in place from FRICTION to, at most, COSMETIC and confined to this one
Windows checkout — not a real cross-platform defect. Added
[`.gitattributes`](.gitattributes) (`* text=auto eol=lf`, binaries excluded) anyway, as a genuine
forward-looking improvement that makes normalization explicit rather than dependent on a future
contributor's individual git config — not a fix for a bug that turned out not to exist.

**F3 (HiGHS solver debug output leaks to stdout) — fixed, and the fix required a second root cause
to be found.** The first attempt (`os.dup2`-based OS file-descriptor redirection in
`optimizer/solve.py`'s `_suppress_native_stdout`) tested as fully working on direct Windows-native
execution, but the identical, verified-correct code still leaked noise when run inside the actual
Linux Docker container — the target environment this actually has to work in. Diagnosing this
inside the container (via `data_snapshots/diag_solve2.py`, a throwaway script built against the
real 2,626-variable problem and deleted once the investigation concluded) showed the noise
appearing only *after* the redirected block's own "done" marker — i.e. after the real fd had
already been restored. Root cause: HiGHS's trace lines go through C stdio, which is fully buffered
(not line-buffered) whenever stdout isn't a real terminal — true for both `docker compose run` and
pytest's capture — so the writes sit in libc's own buffer and are only flushed by the C runtime's
exit-time handler, which fires after Python's fd restoration, not before. Fixed by adding
`_flush_native_stdio()` (a `ctypes` call to `fflush(NULL)`, cross-platform via `msvcrt` on Windows)
and calling it *while fd 1 is still redirected to devnull*, before restoring the real fd — this
drains the buffered writes into devnull for real instead of merely delaying them. Verified inside
the actual Linux container, not just locally: `docker compose run --rm pipeline python -m
optimizer.main` now produces zero noise with the identical, correct result
(`optimal_within_2pct_gap`, 70 transfers, variance `3.51009e-07 -> 2.53575e-08`); the full
container-adjacent test suite (`pytest -v` against the running compose Postgres) still passes
16/16 with zero noise; `mypy`/`ruff check`/`ruff format --check` remain clean.

**C1 (dbt deprecation warnings) — fixed, both artifacts.** Removed the deprecated `target-path`/
`log-path` keys from each `dbt_project.yml`; dbt-core already reads `DBT_TARGET_PATH`/
`DBT_LOG_PATH` natively as environment variables, which were already set at the Docker/DAG level
in both artifacts. Verified: `dbt seed`/`dbt run` still succeed, target/logs still land in the same
container-local scratch paths, and the two specific deprecation warnings no longer appear (the
unrelated "dbt 1.7.20 is past EOL" notice is untouched — it was never what C1 was about).

### Revised verdict

**Yes — a stranger with Docker installed, and no other context, can now go from `git clone` to a
generated output for both artifacts, following only each artifact's own README.**

This reverses the original "No," and specifically because B1 and B2 — the two blockers the
original verdict turned on — are both fixed and re-verified above. F3 was the one open thread left
after the first fix pass; it is now closed and independently confirmed inside the real target
container, not just claimed. The one caveat carried forward, unchanged, is F4: this is true of a
clone from local git history, not yet of `github.com/Kaide-LABS/Sand-FDE-App` — nothing in this
fix pass pushed anything, and this document does not claim otherwise.
