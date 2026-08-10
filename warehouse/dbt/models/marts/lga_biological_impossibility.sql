{{
    config(
        materialized='table'
    )
}}

-- Constraint 2: biological impossibility.
--
-- Aggregates int_lga_impossibility_detail (one row per LGA/indicator/year,
-- see that model for the exact test) up to one row per LGA across the full
-- retained history (2015-2025), so a persistently-implausible LGA ranks
-- worse than one with a single one-off spike.

select
    location_id,
    lga_name,
    count(*) filter (where is_impossible) as impossible_incident_count,
    count(*) filter (where is_extreme_impossible) as extreme_impossible_incident_count,
    count(distinct indicator_id) filter (where is_impossible) as distinct_indicators_affected,
    max(reported_coverage_pct) filter (where is_impossible) as max_reported_coverage_pct,
    max(year) filter (where is_impossible) as most_recent_impossible_year,
    (count(*) filter (where is_impossible) > 0) as biological_impossibility_flag
from {{ ref('int_lga_impossibility_detail') }}
group by location_id, lga_name
