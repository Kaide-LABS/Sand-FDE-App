# ULTIMATE_PRD.md — Borno State PHC Worker Reallocation Optimizer

Artifact Two of the Sand Technologies FDE (Nigeria) application. Sibling to
`../artifact-one-data-quality/` (the Katsina LGA data-toxicity audit) in the same repository.
Where Artifact One proves the ability to tell when data can't be trusted, this artifact proves the
next move: turning a trustworthy, real, government-published workforce audit into a specific,
zero-budget, mathematically defensible staff reallocation, without ever letting a model's judgment
stand in for arithmetic a human can check.

Confirmed spec this was built against: `.claude/loopr/baby_prd.md`, `.claude/loopr/context.md` —
read those first; this document expands on a confirmed spec, it does not originate one. Anywhere
this PRD's own architecture decisions touch the confirmed acceptance criteria or boundary, it is
because `baby_prd.md`'s own `[AMENDED 2026-08-16]` section already recorded that change with the
user's explicit sign-off — this document does not unilaterally revise confirmed scope anywhere.

---

## 1. Primary source and what it actually contains

**Source:** Borno State Ministry of Health and Human Services / Borno State Primary Healthcare
Development Board, *Report of Baseline Mapping Exercise for Primary Healthcare Workers in Borno
State*, February 2025.
<https://hopegov.pfm.bo.gov.ng/wp-content/uploads/2025/03/Borno_State_Report_of_PHC_Workers_Baseline_Mapping_Exercise.pdf>
(downloaded and read in full for this PRD — not taken on the research brief's secondhand
description; see §2 for what that verification changed).

What it actually contains, precisely, since precision here is the entire point of this artifact:

- **329 registered PHC facilities** across **27 LGAs** and **312 wards**; **274 wards** currently
  have an operational facility, **38 wards** have none, "primarily because of the security
  situation" (p.12). Gap analysis and the upgrading programme are anchored on the 274 operational
  wards; the 38 are a disclosed exclusion, not an oversight in the source document.
- **Table 1** (p.21–22, "Distribution of Health workers in Borno State by Job Area") — **26 rows,
  one per LGA — not 27. Guzamala is entirely absent** (§2 finding 9; verified via exact table
  extraction, not just a read). Columns: Community Health Officer, Community Health Extension
  Worker, Junior Community Health Extension Worker, Health Information Management, Medical Doctor,
  Medical Laboratory Scientist, Nurse/Midwife, Pharmacist, Total Core Health Workers, Total Support
  Health Workers, Grand Total. This is the **only** per-LGA current-headcount table in the
  document, and its own listed rows sum to 3,915 against its own stated Grand Total of 3,916.
- **Table 4** (p.25, "Total PHC Staff Gap by Professional Area") — a *different* 8-cadre list:
  Nurses/Midwives, CHO, CHEWs, JCHEWs, Lab Technicians, Pharmacy Technicians, Environmental Health,
  Medical Record Officer — each with Minimum No. per PHC (NPHCDA standard), Total Required, Total
  Available, and Gap, at **state level only**, not per LGA.
- **Table 6** (p.26, "Minimum Standard for Primary Healthcare Staffing") — the NPHCDA minimum per
  facility: Medical Officer 1, CHO 1, Nurse/Midwife 4, CHEW 3, JCHEW 6, Pharmacy Technician 1,
  Environmental Officer 1, Medical Records Officer 1, Support Staff 5.
- **Table 7** (p.30) — the same 8 gap-analysis cadres, phased into a 5-year recruitment plan
  (2026–2030), summing to the same 2,860 total as Table 4.
- **Population:** only a **state-level** figure and trajectory — 6.9M (2025) → 9.2M (2030), 3.98%
  annual growth (p.11, p.33). **No ward-level or LGA-level population figure appears anywhere in
  the document.**
- **Figure 1** (p.13, "Number of Facilities per LGA") and **Figure 2** (p.14, "Health Facilities
  Density per 10,000 Populations Across LGAs") — bar charts, read directly from the PDF, giving
  facility count and density-per-10k-population per LGA. Used in §3 below to derive an LGA
  population proxy without leaving the source document.
- **Total workforce: 3,916**, across the 329 facilities. 35% (1,369 per prose, 1,367 per Table 1's
  own Grand Total cell — a 2-person internal discrepancy in the source, noted and not silently
  corrected) core health workers; 65% support staff.
- **Recommendation #1** of the report itself (p.37): *"Surplus PHC workers in facilities with
  surpluses should be redistributed to the facilities with shortages."* Strategy F of the State's
  own recruitment strategy (p.32) names this explicitly as "Staff re-distribution." **This
  artifact's entire premise is the State's own stated first recommendation, not an outside
  imposition** — worth stating plainly in any outward-facing material.

---

## 2. MODERNIZATION CHANGELOG

Every substantive change this drafting pass made to the research brief's original description of
this data source, each traced to a primary-source read of the actual PDF (§1), not inherited from
the brief or the corrections file uncritically. This is the second and third round of exactly the
failure mode `ARTIFACT_TWO_BRIEF_CORRECTIONS.md`'s own Correction 4 named as a standing discipline
for this build: a number or a structural claim that traces to a real, cited source is not
automatically correct — re-verify at the point of use.

1. **[VERIFIED, more precisely than the corrections file stated] The staffing gap is 2,860, and
   here is exactly why 2,628 is wrong.** The PDF's own Executive Summary (p.7) states "a total
   staffing gap of 2,628 workers" — this is the number the *original Gemini research brief*
   inherited, faithfully, from the PDF's own prose. It is not a transcription error introduced
   upstream. But **2,628 appears in exactly one place: the Executive Summary.** Section 2.2.1's
   prose (p.24–25), Table 4 (974+216+188+1,138+93+251+0+0 = 2,860), and Table 7 (429+573+716+628+514
   = 2,860) all independently state or compute 2,860. The primary source contains an internal
   inconsistency; 2,860 is the figure actually used in every place the document does arithmetic
   with it, 2,628 is an unreconciled outlier. This artifact uses 2,860, per the confirmed spec, now
   for a fully disclosed reason rather than "the corrections file said so."

2. **[NEW FINDING — materially changes architecture] Table 1 is LGA-level, not facility-level.**
   The confirmed acceptance criteria (pre-amendment) and the original research brief's own
   Proposal 1 description ("Transfer 3 CHEWs from Facility A in Maiduguri to Facility B in Kala
   Balge") both assumed facility-level granularity. Table 1 has 26 rows (§2 finding 9). The facility-level roster
   was clearly collected (Annex 2, p.39, is a facility-by-facility data-collection form) but is not
   published in this PDF. **User-confirmed resolution (2026-08-16): this artifact operates at LGA
   grain.** See `baby_prd.md`'s `[AMENDED 2026-08-16]` section for the acceptance-criteria
   revision this required.

3. **[NEW FINDING — materially changes architecture] No ward or LGA population figure exists in
   the source.** Only the state total is published. **User-confirmed resolution: derive an LGA
   population proxy from the PDF's own Figure 1 and Figure 2** (§3.2 below), explicitly labeled as
   a derived figure, not a directly reported one.

4. **[NEW FINDING — not yet resolved, flagged not fabricated] The 38 insecure wards are not
   mapped to LGAs anywhere in the document.** The PDF states the count (38) and that they are
   "distributed across several LGAs in the most conflict-affected zones" (p.12) but publishes no
   per-LGA breakdown. `[UNVERIFIED — confirm insecure-ward-to-LGA mapping before shipping]`. **Do
   not** proxy this from facility-coverage gaps (e.g. assuming Kala Balge/Marte/Biu, named on p.13
   as having "the lowest coverage," are the insecure ones) — low facility coverage and ward-level
   insecurity are correlated in the report's own narrative but are not the same measured quantity,
   and treating them as interchangeable would silently launder an assumption into a fact. This is
   an open architecture question (§8), not a resolved one.

5. **[NEW FINDING — narrows Phase 1's cadre scope, disclosed not silent] Table 1's per-LGA cadre
   columns do not match Table 4/6/7's gap-analysis cadre list.** Table 1 has: CHO, CHEW, JCHEW,
   Health Information Management, Medical Doctor, Medical Laboratory Scientist, Nurse/Midwife,
   Pharmacist. Table 4/6/7 has: Nurses/Midwives, CHO, CHEWs, JCHEWs, Lab Technicians, Pharmacy
   Technicians, Environmental Health, Medical Record Officer. Four cadres match exactly (CHO, CHEW,
   JCHEW, Nurse/Midwife). Two require an assumed name-equivalence across what are, in Nigerian PHC
   cadre nomenclature, genuinely different qualification tiers (Pharmacist ≠ Pharmacy Technician;
   Medical Laboratory Scientist ≠ Lab Technician) — **not assumed in Phase 1** (see §5). Two
   (Environmental Health, Medical Record Officer) have **no Table 1 source at all** — Table 1
   contains no columns for them, and Table 4 marks both at 0 gap ("Surplus to be redeployed"
   footnote), so they are lower-priority for a deficit-reduction optimizer in any case.

6. **[VERIFIED — no action needed] The 38-ward figure, the NPHCDA minimum-standard table, and the
   3,916 total workforce figure all check out exactly as the corrections file stated.** No
   discrepancy found on re-verification.

7. **[MINOR — noted, not corrected] Table 1's own Grand Total row shows 1,367 Total Core Health
   Workers, but summing its own listed cadre columns (58+634+506+41+4+3+122+1) gives 1,369** — a
   2-worker internal arithmetic slip in the source, matching the prose figure (1,369) elsewhere in
   the same document. Not load-bearing for this artifact (Grand Total per LGA, the figure this
   artifact's population-ratio metric actually uses, is internally consistent at 3,916), but named
   here because finding exactly this class of small, real inconsistency in a primary source is
   Artifact One's own thesis, and it would be dishonest to notice it and not say so.

8. **[MINOR — noted, not corrected] Section 3.1.4(F)'s narrative example is inconsistent with
   Table 4/7.** The recruitment strategy text (p.32) names "Laboratory technician" as a surplus
   cadre being redistributed within-LGA, citing Table 7 — but Table 4/7 shows Lab Technicians at a
   93-worker *deficit*, not a surplus; only Environmental Health and Medical Record Officer are
   actually marked surplus in those tables. Noted for completeness; does not affect this artifact's
   own cadre selection (§5), which already excludes Lab Technicians from Phase 1 for the taxonomy
   reason in finding 5, independently of this narrative slip.

9. **[NEW FINDING, confirmed via exact table extraction — materially affects optimizer scope]
   Table 1 lists only 26 LGAs, not 27 — Guzamala is entirely absent.** Re-extracted Table 1
   programmatically via `pdfplumber` (a text-layer table parser, not the vision-based read used for
   the rest of this document) to independently verify every cell rather than trust a hand
   transcription: 26 LGA rows, columns and values matching the earlier read exactly, summing to
   **3,915** against the table's own stated Grand Total of **3,916** — a 1-worker discrepancy. Borno
   State's standard 27-LGA list ([Nigerian Focus, "List of 27 Local Government Areas in Borno State
   and Their Headquarters"](https://nigerianfocus.com/list-of-27-local-government-areas-in-borno-state-and-their-headquarters/))
   names exactly one LGA absent from Table 1's list: **Guzamala**. The PDF never states why Guzamala
   is missing from this specific table — the most consistent explanation, given the document's own
   framing of the 38 insecure wards and Guzamala's well-documented severe conflict exposure, is that
   it could not be reached for data collection, but this document does not say so explicitly, so it
   is stated here as the likely explanation, not an established fact. **Architectural consequence:
   this artifact's optimizer operates over exactly the 26 LGAs Table 1 lists. Guzamala has zero
   current-headcount data and cannot be a transfer source or destination in Phase 1 — not because it
   doesn't need staff, plausibly the opposite, but because the primary source provides no data for
   it.** This must render as an explicit, visible disclosure in the output (§8), not silent omission
   — the same posture-of-honesty requirement already established for the insecure-ward flag.

10. **[Data-fidelity note, not a finding] Tables 1/4/6 are now independently verified via exact
    text-layer extraction (`pdfplumber`), not only the earlier vision-based read — every cell in
    §3.1's ingested tables matches byte-for-byte across both extraction methods.** Figures 1 and 2
    (the facility-count and density bar charts §3.2's population proxy derives from) have **no
    extractable text layer** — pdfplumber confirms their values are baked into chart images with no
    underlying text objects, so they can only be read via the vision-based pass and carry
    meaningfully more transcription risk than the pdfplumber-verified tables. This makes the
    population proxy (§3.2), not the current-headcount data, this artifact's single largest
    remaining data-fidelity risk — already labeled as a derived, chart-read figure in §3.2, and
    called out here explicitly for why that label matters more than it might first appear.

---

## 3. Data model and ingestion

### 3.1 Ingested tables (all sourced from the one PDF; no other document is ingested)

| Table | Source | Grain | Used for |
|---|---|---|---|
| `raw.lga_current_staffing` | PDF Table 1 | **26 rows** (Guzamala absent, §2 finding 9) × 8 cadre columns + Grand Total | Optimizer's current-headcount input; Grand Total column drives the population-ratio metric |
| `raw.lga_staffing_gap` | PDF Table 4 | 8 cadres × state-level Required/Available/Gap | Cross-check only (state-level, not directly usable per-LGA — see §5) |
| `raw.nphcda_minimum_standard` | PDF Table 6 | 9 rows (cadre → minimum per PHC) | Documentation/context only — **not** used as the optimizer's floor (see §6.3: the floor is this artifact's own constraint, not NPHCDA's) |
| `raw.lga_facility_count` | PDF Figure 1 | 26 rows (Guzamala absent here too; sums to exactly 329, self-consistent) | LGA population proxy derivation (§3.2) |
| `raw.lga_facility_density` | PDF Figure 2 | 26 rows (Guzamala absent here too) | LGA population proxy derivation (§3.2) |

Digitization of these five tables/charts is a **one-time, manual, checked-in CSV extraction**, not
a live scrape — this is a static PDF, not an API. Each CSV carries a header comment citing the
exact page number and table/figure number it was transcribed from, mirroring
`ingestion/config.py`'s citation discipline in Artifact One. A `tests/test_pdf_extraction_sums.py`
safeguard (same shape as Artifact One's `test_indicator_reference_sync.py`) asserts the checked-in
`raw.lga_current_staffing` Grand Total column sums to 3,916 and `raw.lga_staffing_gap`'s Gap column
sums to 2,860, so a future edit to either CSV that silently breaks agreement with the PDF's own
totals fails a test rather than shipping quietly wrong.

### 3.2 Deriving the LGA population proxy (Finding 3, §2)

```
LGA_population[k] ≈ facilities_in_LGA[k] / density_per_10k[k] × 10,000
```

Both `facilities_in_LGA` (Figure 1) and `density_per_10k` (Figure 2) are read directly off the
PDF's own bar charts — this stays entirely within the confirmed boundary's "sole source of
staffing data" constraint (population is a *derived* figure, not a second staffing source), but it
is **read off chart bar heights**, not a table of exact numbers, so each value carries real
transcription risk. `stg_lga_population_proxy.sql`'s own model-level test cross-checks the derived
values against the one number the PDF *does* state as ground truth in prose (p.13: state health
facility density "0.8 per 10,000 population," 329 facilities, ~6.9M state population in 2025) —
the population-weighted average of the 27 derived `LGA_population` values must reconcile with the
state total to within a disclosed tolerance, or the model fails loudly rather than silently
shipping a bad derivation. Every rendered output that uses this figure is labeled, inline, as
`(derived from PDF Fig. 1 & Fig. 2, not directly reported)` — never presented as if the PDF states
LGA population directly, because it doesn't.

### 3.3 Why no PostGIS, no GRID3, no HFR

Nothing in this artifact's confirmed scope involves a geometry, a coordinate, or a spatial join —
Table 1 is a plain LGA×cadre count table, and the derived population proxy (§3.2) is a plain
LGA×number table. Shipping PostGIS or ingesting GRID3/HFR would be exactly the
stack-completeness-for-its-own-sake `../artifact-one-data-quality/README.md`'s own "Why plain
Postgres, not PostGIS" section already rules out for the sibling project, for the identical reason:
no `ST_*` call anywhere in this codebase. Plain `postgres:16`, matching Artifact One's own pinned
image.

---

## 4. Optimizer formulation

**Decision variables:** `x[i][j][c]` — integer number of workers of cadre `c` transferred from
LGA `i` to LGA `j` (`i ≠ j`), for `c ∈ {CHO, CHEW, JCHEW, Nurse/Midwife}` (the four
exactly-matched cadres — see §5 for why the other four are excluded from Phase 1), for all
`i, j` in the **26 LGAs Table 1 lists** (all 27 minus Guzamala — §2 finding 9).

**Zero-sum payroll — true by construction, not by a constraint.** Every unit of `x[i][j][c]`
contributes exactly −1 to LGA `i`'s net change and exactly +1 to LGA `j`'s net change for cadre
`c`. Summed across the whole solution, net change is 0 *by the structure of the decision
variables themselves* — there is no feasible assignment of `x` that is not zero-sum, because the
model has no notion of a worker appearing or disappearing, only moving between two named LGAs.
This is worth stating as a design property, not merely a checked constraint: acceptance criterion 1
(exact zero-sum) cannot fail for an arithmetic reason, only for a data-entry bug in reading back the
solver's own output — which is exactly why the acceptance criterion still requires an independent
third-party recomputation (a reviewer sums a column in a spreadsheet), not a claim that the model
"guarantees" it.

**Per-cadre floor (baby_prd.md acceptance criterion 3, amended to LGA grain):** for LGA `k`,
cadre `c`, with `current[k][c]` from `raw.lga_current_staffing`:

```
sum_j x[k][j][c]  ≤  max(current[k][c] − 1, 0)
```

When `current[k][c] = 0`, the upper bound is 0 — an LGA with zero of a cadre has no eligible
outbound transfer for it, which is ordinary non-negativity, never a special case in the model
itself (matches the acceptance criterion's own framing exactly).

**Objective — a linear proxy for variance, with variance itself computed and reported
separately.** True population variance of the ratio distribution is a quadratic quantity
(`Σ(ratio_k − mean)²`), which `scipy.optimize.milp` (a linear/mixed-integer solver, not quadratic)
cannot take as an objective. The optimizer instead minimizes the **sum of absolute deviations**
from the state's population-weighted target ratio — itself a genuine linear quantity in the
decision variables, since `population[k]` is a fixed constant per LGA:

```
target_ratio = (Σ_k Grand_Total[k]) / (Σ_k LGA_population[k])   — a fixed constant (3,916 / state population proxy)
ratio[k] = (Grand_Total[k] + Σ_c net[k][c]) / LGA_population[k]  — linear in x
minimize  Σ_k d[k]   subject to   d[k] ≥ ratio[k] − target_ratio,   d[k] ≥ target_ratio − ratio[k]
```

This is a standard, well-established linearization of an L1 dispersion-minimization objective
(the same "minimize deviation from a target" shape validated in Blanco, Gázquez & Leal 2022,
*Mathematical optimization models for reallocating and sharing health equipment in pandemic
situations*, TOP (Springer), DOI [10.1007/s11750-022-00643-3](https://doi.org/10.1007/s11750-022-00643-3)
— a real MILP-based health-resource reallocation-across-facilities paper, cited narrowly for that
one methodological precedent; that paper's own model is *not* zero-sum and has *no* minimum-floor
constraint, so it validates "MILP-based health-resource reallocation is an established technique,"
not this artifact's specific zero-sum-plus-floor variant, which is disclosed rather than
overclaimed). **Population variance itself (the literal statistic named in acceptance criterion 4)
is computed post-hoc from the same solved allocation** — a standard `numpy`/plain-Python variance
calculation over the 27 resulting `ratio[k]` values, before and after — and is what actually
renders in the output table, independently reproducible by a reviewer with a spreadsheet, exactly
as the acceptance criterion requires. The distinction (linear L1 objective the solver actually
optimizes vs. quadratic variance the output reports and a reviewer recomputes) is stated explicitly
in the rendered report, not left for a reader to assume they're the same thing.

**Solver: `scipy.optimize.milp`** (HiGHS-backed, deterministic — [SciPy 1.18.0](https://github.com/scipy/scipy/releases/tag/v1.18.0),
released 2026-06-19, requires Python 3.12–3.14 and NumPy ≥2.0.0), chosen over OR-Tools
([9.15.6755 on PyPI](https://pypi.org/project/ortools/), released 2026-01-14) for this Phase 1:
the problem is small (26 LGAs × 4 cadres × ≤25 destination LGAs each ≈ a few thousand integer
variables), well within a pure-Python-plus-HiGHS solve, and `scipy.optimize.milp`'s dependency
footprint is far lighter than OR-Tools' C++ binary — matching Artifact One's own
minimal-dependency discipline (`pyproject.toml`'s short, individually-justified list). OR-Tools
remains a documented fallback if a later phase's constraint set needs CP-SAT-style extensions
(e.g. genuinely nonlinear or combinatorial constraints) this MILP formulation can't express.

---

## 5. Phase 1 cadre scope (disclosed narrowing, not silent)

**In scope for the optimizer's decision variables:** Community Health Officer (CHO), Community
Health Extension Worker (CHEW), Junior Community Health Extension Worker (JCHEW), Nurse/Midwife —
the four cadres with an exact, unambiguous name match between Table 1 (current headcount source)
and Table 4/6/7 (gap-analysis source). Together these four account for 974 + 216 + 188 + 1,138 =
**2,516 of the state's 2,860-worker gap (88%)** — the substantial majority of the deficit, not a
token subset.

**Explicitly out of Phase 1, named per §2 finding 5:**
- Pharmacist (Table 1) / Pharmacy Technician (Table 4/6/7) — plausible but unconfirmed
  name-equivalence across what are different qualification tiers in Nigerian PHC nomenclature.
- Medical Laboratory Scientist (Table 1) / Lab Technician (Table 4/6/7) — same reason.
- Environmental Health, Medical Record Officer — no Table 1 source at all; also already at 0 gap
  per Table 4 ("Surplus to be redeployed"), so lower priority for a deficit-reduction optimizer
  regardless.

A later phase could resolve the Pharmacist/Lab ambiguity (e.g. by direct confirmation from Borno
SPHCDB of whether the two labels denote the same role in this dataset) and extend the optimizer's
cadre set accordingly — this is named as a real, concrete non-goal for Phase 1, not silently
dropped.

---

## 6. Universal invariants

- Pydantic v2, `model_config = ConfigDict(extra="forbid")` on every `BaseModel`, matching Artifact
  One's own convention exactly.
- `mypy --strict` clean; type hints on every signature.
- **Deterministic-only correctness boundary (this artifact's PROJECT HARD BOUNDARY).** Every number
  this artifact reports as fact — each proposed transfer's headcount, the zero-sum check, the
  per-cadre floor check, the before/after variance — is produced by deterministic arithmetic or
  `scipy.optimize.milp`, never by LLM judgment or LLM-generated arithmetic, and computed only from
  figures traceable to the PDF's own Table 1/4/6/Figures 1–2 (§3.1) or their disclosed derivations
  (§3.2) — never an invented, estimated, or LLM-recalled figure standing in for a real one. Code
  that would **violate** this boundary: any LLM API call inside the optimizer's constraint
  construction, solve, or verification path; any hardcoded staffing or population figure not
  sourced from the checked-in, cited CSVs in §3.1; any silent fallback that substitutes a
  plausible-looking guess when an LGA or cadre is missing from the ingested data, instead of
  surfacing it as a load-bearing gap (exactly the discipline §2 finding 4 already applies to the
  insecure-ward mapping). A future review pass should grep the optimizer module and its call sites
  for any LLM client import and treat any hit as an automatic HALT.
- No credential-gated data source, ever — the PDF is public, no login, no key, matching Artifact
  One's own zero-credential acceptance bar.
- Commits stay neutral (no AI attribution), matching this repo's existing convention.

---

## 7. Tech stack

Same rationale, same disclosed choices as `../artifact-one-data-quality/`, made independently here
rather than copied uncritically — and, if anything, more clearly the right call for this project
since it has even less spatial/interactive-dashboard need:

- **Python + plain PostgreSQL** (no PostGIS — §3.3), **Airflow** (on-demand DAG, `schedule=None`,
  triggered by hand — the ingestion is a one-time PDF extraction, not a live pull, but keeping the
  DAG orchestrating seed → optimize → report matches Sand's stated stack and Artifact One's own
  precedent for demonstrating the same tool), **dbt** (staging → marts, transforming the five
  checked-in CSVs (§3.1) into the optimizer's input tables and the reported output marts).
- **Static HTML report, not Superset** — the deliverable is one transfer table, one before/after
  ratio comparison, and the insecure-ward-flag disclosure (once §8's open question resolves); the
  same disproportionate-operational-surface argument
  `../artifact-one-data-quality/README.md`'s "Why a static HTML report, not Superset" section
  already made applies at least as strongly here.
- **No hosting** (per the confirmed hard constraint carried from Artifact One) — the local run's
  own generated output (the transfer table, the report) is the deliverable.
- **Version drift, disclosed rather than silently matched or silently upgraded:** current stable
  releases as of this drafting pass (2026-08-16) are Apache Airflow 3.3.0 (released 2026-07-06 — a
  major-version jump from Artifact One's pinned 2.9.3) and dbt-core 1.12.2 (vs. Artifact One's
  pinned `dbt-postgres>=1.7,<1.8`). This artifact stays on the **same 2.x Airflow / 1.7.x dbt line
  Artifact One already uses and has proven working**, a deliberate consistency choice for a
  two-artifact application read by the same reviewers, not an oversight — flagged here rather than
  silently left unexplained. Revisiting either pin is a reasonable future change, not a defect in
  this PRD.

---

## 8. OPEN ARCHITECTURE QUESTIONS

1. **Insecure-ward-to-LGA mapping (§2 finding 4).** Blocking for acceptance criterion 2 (the
   insecure-ward flag). Needs either a supplementary section of the underlying State HRH database
   (the PDF's own §1.4.2 names this as its primary source, distinct from the published PDF itself)
   or direct confirmation from Borno SPHCDB. **Until resolved, the rendered output must state
   explicitly that this flag is not yet implemented and why** — silence on this point, or a
   fabricated proxy, would both be worse than a disclosed gap, per the same discipline
   `baby_prd.md`'s soft-context note about the insurgency flag already established as load-bearing
   for how this artifact is judged.
2. **Pharmacist/Lab cadre-name ambiguity (§5).** Not blocking — Phase 1 ships without these two
   cadres, at 88% of the state's actual gap covered by the four confirmed-match cadres. Worth
   resolving before any later phase extends the optimizer's cadre set.

---

## 9. Accountable Autonomy level

**Human-in-the-Loop**, unchanged from the confirmed boundary. The optimizer proposes; a human
SPHCDB HR Director reviews and executes. Not Full Automation (a proposed transfer is not itself the
decision — see the confirmed posture/voice soft-context note in `context.md`: this artifact must
read as a draft offered for review, never a prescription). Not Supervised Automation (the
socio-political and logistical feasibility factors named in the confirmed scope edges — housing,
security, staff willingness — are exactly the class of judgment a deterministic optimizer cannot
parse, and the confirmed scope explicitly excludes scoring them). Not Human Required (a wrong
transfer proposal is fully reversible — a reviewer rejects it before it becomes a real HR action —
and low-severity on its own, the same reasoning Artifact One's own Accountable Autonomy section
already applied to a structurally similar decision-support, not decision-making, system).

---

## 10. Non-goals (restates confirmed scope edges — see `baby_prd.md` for the authoritative text)

No multi-state generalization. No recruitment/hiring modeling (the separate 2,860-worker five-year
hiring plan is untouched). No socio-political/logistical feasibility scoring inside the optimizer.
No live HR/payroll system integration. No modeling of anything not present in the checked-in,
cited CSVs (§3.1) or their disclosed derivations (§3.2) — a genuine data need beyond those becomes
an open question (§8), never an invented value.

---

## 11. Failure-mode analysis (Phase 1 must bake these in — see PHASE_1_SPEC.md §7)

| Failure mode | Detection | Prevention |
|---|---|---|
| A transfer references a cadre/LGA combination not in `raw.lga_current_staffing` | `stg_lga_current_staffing` dbt model fails a `not_null`/relationship test | Ingestion-time schema validation via Pydantic `extra="forbid"` models, matching Artifact One's `ingestion/models.py` discipline |
| The optimizer's solution is infeasible (over-constrained) | `scipy.optimize.milp`'s own status code, surfaced not swallowed | Report the infeasibility explicitly rather than silently returning an empty or partial solution |
| A floor violation slips through due to an off-by-one in the upper-bound calculation | `tests/test_floor_constraint.py` — a Python-level test independent of the solver, recomputing every LGA/cadre's post-transfer headcount from the solver's own output and asserting no cadre that started ≥1 ends below 1 | Same "independent recomputation, not solver self-report" discipline the acceptance criteria already require of a human reviewer, applied as an automated test too |
| The population-proxy derivation (§3.2) silently drifts from the PDF's own stated 0.8/10k state average | `stg_lga_population_proxy.sql`'s reconciliation test (§3.2) | Fails loudly rather than shipping a bad derived denominator |
| Someone mistakes the reported "floor of 1" for "meets NPHCDA minimum standard" | N/A — a documentation failure mode, not a code one | Explicit labeling requirement already in `baby_prd.md`'s confirmed acceptance criteria (the floor-labeling criterion) |
| The insecure-ward flag ships silently unimplemented, read as "no transfers touch an insecure ward" rather than "not yet checkable" | Manual review before any outward-facing send | §8's explicit disclosure requirement — this is the single highest-consequence failure mode named anywhere in this PRD, given the confirmed soft-context note about what "judged a failure" means here |
| A reader assumes the optimizer covers all 27 LGAs and infers Guzamala was assessed and found not to need staff | The report's own rendered output | §2 finding 9's disclosure requirement: the report must explicitly list which 26 LGAs are covered and state Guzamala's exclusion is a primary-source data gap, not an assessment result |

---

## 12. Repository layout (planned — not yet built; PHASE_1_SPEC.md details the actual file list)

```
artifact-two-hr-reallocation/
  reference/borno_phc_baseline.pdf  The primary source itself, checked in verbatim -- a static
                            government PDF, not a live API, so the artifact stays reproducible even
                            if the source URL (hopegov.pfm.bo.gov.ng) ever goes offline.
  data/                    Checked-in, cited CSV extractions from the PDF (§3.1) — five files,
                            each with a header comment citing its exact page/table/figure number.
  optimizer/                The MILP formulation (§4) — Pydantic models, scipy.optimize.milp call,
                            zero-sum/floor verification independent of the solver's own report.
  warehouse/dbt/            staging -> marts, mirroring artifact-one-data-quality's own structure.
  airflow/dags/              On-demand DAG (schedule=None), matching the sibling project's pattern.
  viz/generate_report.py     Static HTML report generator, matching the sibling project's pattern.
  tests/                     Independent recomputation tests (zero-sum, floor, population
                              reconciliation) -- never trusting the solver's own self-report alone.
```
