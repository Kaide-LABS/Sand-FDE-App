-- One row per (LGA, indicator, year) for the subset of indicators where
-- MSDAT's own metadata documents a fixed "X% of total population" denominator
-- (see indicator_reference seed). The eligible population is independently
-- recomputed from GRID3's population estimate for that LGA -- not MSDAT's own
-- (undocumented) population source -- so the flag reflects an external,
-- primary-source check rather than MSDAT re-checking its own arithmetic.
--
-- is_impossible: MSDAT's reported coverage for this indicator, applied to the
-- GRID3-derived eligible population, exceeds 100% -- i.e. more people were
-- reported served than GRID3 estimates exist in the target group MSDAT itself
-- defines the indicator against.
--
-- is_extreme_impossible: even under the maximally generous (and wrong)
-- assumption that every single person in the LGA -- not just the documented
-- target fraction -- was eligible, the implied headcount MSDAT's value
-- represents would still exceed GRID3's total LGA population. This can only
-- happen at very large overshoots and is flagged separately as a stronger
-- signal.

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
    g.source_label as grid3_source_label,
    round((g.population_mean * t.population_fraction)::numeric, 1) as grid3_eligible_population,
    round(
        ((t.value / 100.0) * (g.population_mean * t.population_fraction))::numeric,
        1
    ) as implied_headcount,
    (t.value > 100.0) as is_impossible,
    (
        (t.value / 100.0) * (g.population_mean * t.population_fraction) > g.population_mean
    ) as is_extreme_impossible
from {{ ref('int_msdat_tagged') }} as t
inner join {{ ref('stg_grid3_population') }} as g
    on t.lga_name = g.lga_name
where t.in_impossibility_test
