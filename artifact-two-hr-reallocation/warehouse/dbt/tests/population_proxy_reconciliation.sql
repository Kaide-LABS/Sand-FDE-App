-- Reconciles stg_lga_population_proxy's aggregate against the PDF's own
-- stated state-level facility-count/density identity (p.13: 329
-- facilities, 0.8 facilities per 10,000 population) -- ULTIMATE_PRD.md
-- Sec.3.2. Deliberately NOT reconciled against the separately-stated ~6.9M
-- total 2025 state population.
--
-- Why not the 6.9M figure: computing implied population from the state's
-- own stated facility count and density (329 / 0.8 * 10,000 = 4,112,500)
-- does not equal the state's separately stated 2025 population (6.9M) -- a
-- ~41% gap. That mismatch is a genuine internal inconsistency in the
-- primary source (the "per 10,000 population" denominator Figure 2's
-- density is computed against evidently is not the same population base as
-- the state total quoted in prose elsewhere in the document -- plausibly a
-- catchment-population base rather than total state population, though the
-- PDF does not say so explicitly), not an error introduced by this
-- pipeline. Reconciling this pipeline's own derivation against a state
-- figure the derivation was never mathematically related to in the first
-- place would produce a test that fails on correct code -- so this test
-- reconciles against the one combination that IS self-consistent: summing
-- the 26 independently-derived LGA-level population proxies should closely
-- reproduce the state-level version of the same facility-count/density
-- identity. Observed reconciliation is ~1.6%, comfortably inside the
-- disclosed +/-5% starting tolerance (PHASE_1_SPEC.md Sec.6 step 2 --
-- "tighten once real reconciliation is observed"; ~1.6% would support
-- tightening to +/-3% in a later revision, left at +/-5% here since Phase 1
-- is a one-time run, not a recurring pipeline where the wider margin costs
-- anything).
--
-- A dbt test fails if it returns any rows -- this returns one row only when
-- the reconciliation is out of tolerance.

with proxy_total as (
    select sum(population_proxy) as summed_population_proxy
    from {{ ref('stg_lga_population_proxy') }}
),

state_identity as (
    select (329.0 / 0.8) * 10000 as state_implied_population
),

tolerance as (
    select 0.05 as pct_tolerance
)

select
    proxy_total.summed_population_proxy,
    state_identity.state_implied_population,
    abs(proxy_total.summed_population_proxy - state_identity.state_implied_population)
        / state_identity.state_implied_population as pct_diff
from proxy_total
cross join state_identity
cross join tolerance
where
    abs(proxy_total.summed_population_proxy - state_identity.state_implied_population)
        / state_identity.state_implied_population > tolerance.pct_tolerance
