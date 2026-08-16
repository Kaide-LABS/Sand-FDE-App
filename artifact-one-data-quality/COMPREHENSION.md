# COMPREHENSION.md

Post-build architecture and decision comprehension pass for the Katsina LGA data-toxicity audit
pipeline, produced by the architect session, anchored to the actual code and to live queries against
the running database -- not to the README's own self-description. Written outside `loopr`'s formal
Step 14 machinery (`loopr customize --step 14` correctly HALTs on this project: it never went through
`step10`/`step11`/`step12`, so no modernized PRD / `PHASE_1_SPEC.md` exists for that command to verify
against -- a deliberate scope decision made earlier in this build, not an oversight). This file captures
the same comprehension-pass substance Step 14 is meant to produce, reflecting the repo's state after
the post-review fix round, not before it.

Confirmed spec this was built against: `.claude/loopr/baby_prd.md`, `.claude/loopr/context.md`.

---

## 1. Architecture walkthrough

**Ingestion** (`ingestion/`): `config.py` holds every ID/indicator/formula this pipeline relies on,
each commented with its MSDAT/GRID3 provenance. `msdat_key_discovery.py` extracts MSDAT's public
frontend-auth key pair at run time from its own live JS bundle (never hardcoded -- see the security
fix earlier in this build's history, commits `df19ea1`/`28afcc4`). `msdat_client.py` is the ~100-line
HTTP client: fetch a 15-minute frontend token, call `data/`, retry on both bad HTTP status *and*
connection-level failures (the latter fixed in `bc8489c` after a live connection drop during
re-verification). `fetch_msdat.py` pulls all 34 Katsina LGAs x 24 basket indicators (816 calls, paced
0.15s apart) into `raw.msdat_indicator_values` plus a dated CSV snapshot. `fetch_grid3.py` downloads
and caches GRID3/WorldPop's admin-level population zip, filters to Katsina's 34 LGAs, writes to
`raw.grid3_lga_population`.

**Warehouse** (`warehouse/dbt/`): staging dedupes to the latest snapshot; `stg_msdat_indicator_values`
now performs a second, distinct dedup pass (added in `0bb82a8`, see section 3) resolving genuinely
conflicting MSDAT records, not just this pipeline's own re-fetches. Intermediate models tag indicators
against the basket/impossibility membership, compute per-LGA-year completeness, year-over-year drops,
and impossibility detail. Marts compute the two constraint outputs and join them into
`lga_data_toxicity_audit`, the deliverable. `tests/` (the dbt ones, `severity=warn`) just re-select
the flagged rows from each mart -- the tests *are* the detection logic.

**New since the original build:** `tests/test_indicator_reference_sync.py` (repo-root `tests/`, a
pytest/plain-Python module, not a dbt test) -- three assertions that `config.py`'s indicator lists and
`warehouse/dbt/seeds/indicator_reference.csv` haven't drifted apart, since nothing at runtime enforced
that before.

**Viz / orchestration / stack:** unchanged from the original build -- `viz/generate_report.py` renders
a static HTML report via direct psycopg query; the Airflow DAG (`schedule=None`) runs
`[fetch_msdat, fetch_grid3] >> dbt_seed >> dbt_run >> dbt_test >> generate_report`; the stack is now
plain `postgres:16` (switched from `postgis/postgis:16-3.4` in `356efb1` -- see section 2).

---

## 2. Decisions, and what they cost/bought -- updated with what the fix round settled

**dbt for the checks, not hand-rolled Python.** Unchanged assessment: right call, buys `severity=warn`
and `{{ ref() }}` lineage, costs the config.py/seed duplication -- **now mitigated**, not just
flagged: `tests/test_indicator_reference_sync.py` fails loudly on drift instead of silently producing
a wrong join.

**GRID3 denominator: mean vs. q975 -- resolved.** The original comprehension pass flagged this as an
unstated judgment call inappropriate for a test called "impossibility." Fixed in `1d71ba3`: both flags
now use `population_q975`. Verified two ways, independently: algebraically (the population term
cancels out of both ratio tests, so the choice provably cannot change either flag), and empirically --
I queried the live table directly and confirmed `is_impossible=780`, `is_extreme_impossible=68`,
identical to the pre-switch counts. This was a free upgrade: strictly more defensible test definition,
zero cost in lost findings.

**The reporting-attrition threshold: real distribution now known, not just "fired zero times."** The
original pass flagged that constraint 1 fired on 0/34 LGAs without knowing whether that was a
near-miss or nowhere close. Now measured directly against the live table (`int_lga_year_over_year`,
374 total LGA-years, 340 with a computable year-over-year drop):

```
completeness_fraction range: 0.3750 -- 0.8333   (floor fires below 0.33)
yoy_relative_drop range:     -0.5455 -- 0.4000   (fires at >= 0.50)
LGA-years within 10 points of the 0.33 floor:  6 / 374
LGA-years within 10 points of the 0.50 drop:   1 / 340
```

Not a near-miss on either threshold -- the real data, across the full 2015-2025 window, simply doesn't
show attrition this severe for any Katsina LGA on this indicator basket. A Katsina-relative threshold
(e.g. flag the bottom decile, ~0.42) was considered and deliberately **not** adopted: a relative
threshold always flags *something* by construction, which would have forfeited the ability to report
zero and mean it. The Gombe-grounded absolute threshold was kept, and the true result is now stated
plainly in `README.md` rather than left to be inferred from a "worth being explicit about" paragraph.

**PostGIS: confirmed unused, now removed.** `356efb1` switched to plain `postgres:16`. This closes the
gap the original pass flagged (stack claim implying spatial capability that was never exercised) --
verified the swap holds on both a reused and a fresh volume.

**Runtime key extraction:** unchanged from the original comprehension pass -- still the right call,
still costs one extra HTTP round trip per run.

**`toxicity_score = 3xattrition + 1ximpossible + 2xextreme`:** unchanged, still an asserted (not
derived) weighting -- not addressed in the fix round, still worth having a one-line justification
ready if asked, per the original pass.

---

## 3. Domain mechanics -- the headline finding, now verified rather than merely observed

**The extreme impossibility values are real MSDAT data, confirmed live, not a units bug.** This is the
single most important update since the original comprehension pass, which explicitly flagged this as
unresolved and recommended spot-checking before presenting it as fact. It has now been checked, and
checked precisely -- I independently re-ran the underlying query myself rather than trust the report:

```sql
select location_id, lga_name, indicator_id, year, value, msdat_updated_at
from raw.msdat_indicator_values
where lga_name = 'Katsina' and indicator_id = 18 and year = 2023
order by msdat_updated_at;
```
```
value    | msdat_updated_at
175.4    | 2024-06-19 11:46:16
39754    | 2024-08-07 19:41:36
21054.6  | 2024-08-07 19:41:37   <- latest, one second after the row above
```

MSDAT's own database genuinely holds three distinct, irreconcilable values for the same LGA, indicator,
and year -- not a pipeline artifact. This is real across the dataset, not a one-off: **107 of 5,589**
Katsina LGA-indicator-year combinations have 2-3 conflicting `record_id`s (I independently recomputed
this denominator; the fix's own commit message says "5,789," which is a transcription slip -- the 107
and the year-concentration below are both exactly right), concentrated almost entirely in one window:
**97 in 2023, 10 in 2024** -- a dateable MSDAT-side reprocessing incident, not noise spread evenly
across the whole series.

The dedup fix (`0bb82a8`) now resolves these by MSDAT's own recency signal (`msdat_updated_at desc`),
which was independently confirmed (via the same network-inspection technique used for the original
auth investigation) to be MSDAT's own convention: its dashboard separately issues
`ordering=-updated_at&size=1` queries elsewhere on the page. Before this fix, the dedup broke ties on
this *pipeline's own fetch timestamp* -- non-deterministic whenever more than one conflicting record
landed in the same run, meaning the specific "which extreme number appears" was previously an artifact
of run timing, not of MSDAT's own data. It no longer is.

**What this means for the artifact's central claim:** it can now be stated as fact, not hedged --
*MSDAT's own live database contains internally conflicting values for the same reporting period,
confirmed by direct inspection, concentrated in a specific, dateable incident in 2023* -- rather than
"MSDAT reports some very large coverage percentages, cause unconfirmed." That is a substantially
stronger and more specific finding than the pipeline shipped with originally, and it is exactly the
kind of "foundations over features" finding this artifact exists to surface.

**Everything else in the original domain-mechanics section is unchanged and still accurate**: the
MSDAT NHMIS-annual/LGA-grain resolution (month-grain doesn't exist at LGA level in the open aggregate),
the single GRID3 population layer (no ward boundaries, no facilities v2.0, no settlement extents),
MSDAT's own population-fraction denominator text used verbatim and not independently re-derived from
WHO/UNICEF methodology, and the Accountable Autonomy level being asserted in prose with no enforced
override mechanism in code (now stated accurately in the README per the fix round, rather than implied
otherwise).

---

## 4. Honesty audit -- re-confirmed after the fix round

All findings from the original pass still hold (independently re-grepped, not just re-asserted):
"78,000"/zero-dose and "38%" appear only in prose *naming what was rejected*, never as live figures;
no synthetic/fabricated data found anywhere in `ingestion/` or `warehouse/dbt/models/`; no killed
architecture (clinic-siting, Open Buildings) present; reproducible with zero Ministry credentials,
confirmed structurally.

**Two overclaims identified in the original pass are now fixed, and I verified the fix, not just the
intent:**
- The README no longer implies GRID3 ward-level data is used -- corrected to state precisely that only
  the LGA-level population-estimate layer is ingested.
- The README no longer claims a human override *mechanism* exists -- corrected to state that flags
  surface to a queryable table, and that a review/override step is the intended next stage, not
  something built.

**One residual accuracy gap, minor:** the commit message for `0bb82a8` states "107 of 5,789"
combinations; the real total (which I computed directly against the live table) is 5,589. The 107
itself, and the 97/10 year split, are both exactly right. This is a small transcription slip in a
commit message, not a wrong finding -- worth a one-line fixup commit if you want the trail
fully clean, but it doesn't touch anything in the README or the actual pipeline logic.

---

## 5. What's left to reconsider

Of the five priority items the original comprehension pass raised, **all five have been addressed**:
the extreme values are verified real (not a units bug) and the root cause (MSDAT's own conflicting
records) is now understood and fixed; the attrition-zero finding is now stated plainly with its real
distribution; the GRID3 denominator now uses the defensible upper bound; both README overclaims are
corrected. The two secondary hygiene items (unused PostGIS, config/seed duplication) are also both
resolved.

**What remains, in order of how much it matters:**
1. The "5,789 vs 5,589" commit-message typo above -- cosmetic, cheap to fix, only matters if someone
   reads git history closely.
2. The `toxicity_score` weighting (3/1/2) is still asserted rather than derived -- not wrong, but have
   your one-line answer ready ("attrition is weighted highest because total data absence is a worse
   failure mode than one bad number") since nothing in the repo currently states that reasoning.
3. MSDAT's own population-fraction denominator text is still trusted verbatim, not independently
   checked against WHO/UNICEF target-population methodology -- a reasonable trust boundary for this
   scope, but worth knowing you haven't re-derived it if someone asks why 5% and not some other figure.

Nothing else from either comprehension pass is still open. The artifact is materially stronger now
than it was at the end of the original build: what was previously "a striking number we haven't
checked" is now "a verified, dateable MSDAT data-integrity incident, confirmed by direct inspection" --
which is a better story, not just a safer one.
