-- One row per (LGA, indicator, year) for the subset of indicators where
-- MSDAT's own metadata documents a fixed "X% of total population" denominator
-- (see indicator_reference seed). The eligible population is independently
-- recomputed from GRID3's population estimate for that LGA -- not MSDAT's own
-- (undocumented) population source -- so the flag reflects an external,
-- primary-source check rather than MSDAT re-checking its own arithmetic.
--
-- The denominator uses GRID3's population_q975 (the upper bound of its 95%
-- uncertainty interval), not population_mean. "Impossible" is a strong claim
-- that should survive the most generous plausible population estimate, not
-- just the point estimate -- flagging against the mean would call something
-- impossible that a higher-but-still-credible population figure could
-- explain away. population_mean is still carried as a column for reference
-- and display; it is not what the flags are computed against.
--
-- is_impossible: MSDAT's reported coverage for this indicator, applied to the
-- GRID3-q975-derived eligible population, exceeds 100% -- i.e. more people
-- were reported served than GRID3's own most generous estimate of the target
-- group MSDAT itself defines the indicator against.
--
-- is_extreme_impossible: even under the double-generous (and wrong)
-- assumption that every single person in GRID3's upper-bound estimate of the
-- LGA's ENTIRE population -- not just the documented target fraction, and
-- not just the mean -- was eligible, the implied headcount MSDAT's value
-- represents would still exceed it. This can only happen at very large
-- overshoots and is flagged separately as a stronger signal.

select
    t.location_id,
    t.lga_name,
    t.indicator_id,
    t.indicator_name,
    t.year,
    t.value as reported_coverage_pct,
    t.population_fraction,
    t.denominator_source_text,
    g.population_mean as grid3_population_mean,
    g.population_q975 as grid3_population_q975,
    g.source_label as grid3_source_label,
    round((g.population_q975 * t.population_fraction)::numeric, 1) as grid3_eligible_population,
    round(
        ((t.value / 100.0) * (g.population_q975 * t.population_fraction))::numeric,
        1
    ) as implied_headcount,
    (t.value > 100.0) as is_impossible,
    (
        (t.value / 100.0) * (g.population_q975 * t.population_fraction) > g.population_q975
    ) as is_extreme_impossible
from {{ ref('int_msdat_tagged') }} as t
inner join {{ ref('stg_grid3_population') }} as g
    on t.lga_name = g.lga_name
where t.in_impossibility_test
