{{
    config(
        materialized='table'
    )
}}

-- THE DELIVERABLE: a ranked LGA data-toxicity audit list -- which Katsina
-- LGAs have the least trustworthy MSDAT data, and why. This is not a
-- health-metrics dashboard; no health outcome is scored or interpreted here,
-- only the reliability of the reporting itself.
--
-- toxicity_score (higher = less trustworthy data), a simple, fully
-- transparent weighted sum:
--   +3   if the LGA trips the reporting-volume-attrition flag (constraint 1)
--   +1   per distinct LGA/indicator/year combination flagged biologically
--        impossible (constraint 2)
--   +2   extra per combination that is *extremely* impossible (implied
--        headcount exceeds the LGA's entire GRID3 population, not just the
--        documented target sub-group)
--
-- This score is a triage ranking, not a certified statistical index -- it
-- exists to tell a human data steward where to look first.

select
    lga.location_id,
    lga.lga_name,
    grid3.population_mean as grid3_population_estimate,
    grid3.source_label as grid3_source_label,
    attrition.latest_year,
    attrition.basket_indicators_reported,
    attrition.basket_size,
    attrition.completeness_fraction,
    attrition.prior_year,
    attrition.prior_year_completeness_fraction,
    attrition.yoy_relative_drop,
    attrition.reporting_attrition_flag,
    coalesce(impossibility.impossible_incident_count, 0) as impossible_incident_count,
    coalesce(impossibility.extreme_impossible_incident_count, 0)
        as extreme_impossible_incident_count,
    coalesce(impossibility.distinct_indicators_affected, 0) as distinct_indicators_affected,
    impossibility.max_reported_coverage_pct,
    impossibility.most_recent_impossible_year,
    coalesce(impossibility.biological_impossibility_flag, false) as biological_impossibility_flag,
    (
        3 * (case when attrition.reporting_attrition_flag then 1 else 0 end)
        + coalesce(impossibility.impossible_incident_count, 0)
        + 2 * coalesce(impossibility.extreme_impossible_incident_count, 0)
    ) as toxicity_score,
    concat_ws(
        '; ',
        case when attrition.reporting_attrition_flag
            then format(
                'reporting-volume attrition: %s%% of basket reported in %s (prior year %s%%)',
                round(attrition.completeness_fraction * 100, 1),
                attrition.latest_year,
                round(coalesce(attrition.prior_year_completeness_fraction, 0) * 100, 1)
            )
            else null
        end,
        case when coalesce(impossibility.impossible_incident_count, 0) > 0
            then format(
                'biological impossibility: %s indicator-year(s) across %s distinct indicator(s), max %s%% coverage (most recent: %s)',
                impossibility.impossible_incident_count,
                impossibility.distinct_indicators_affected,
                impossibility.max_reported_coverage_pct,
                impossibility.most_recent_impossible_year
            )
            else null
        end
    ) as toxicity_reasons
from {{ ref('dim_lga') }} as lga
left join {{ ref('stg_grid3_population') }} as grid3
    on lga.lga_name = grid3.lga_name
left join {{ ref('lga_reporting_attrition') }} as attrition
    on lga.location_id = attrition.location_id
left join {{ ref('lga_biological_impossibility') }} as impossibility
    on lga.location_id = impossibility.location_id
order by toxicity_score desc, lga.lga_name asc
