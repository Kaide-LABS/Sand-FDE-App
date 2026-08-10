{{
    config(
        materialized='table'
    )
}}

-- Constraint 1: reporting-volume attrition.
--
-- What "month-over-month" became and why: the PRD framed this test as
-- catching a sharp month-over-month drop in reported indicator volume,
-- grounded in the Gombe State DHIS2 completeness study (Bhattacharya et al.
-- 2019, PLOS ONE -- see VERIFIED_SOURCES.md). Hands-on inspection of MSDAT's
-- live API (documented in README.md) established that MSDAT's own public
-- aggregate only publishes true month-grain data at STATE level -- its
-- LGA-level publication grain for these indicators is ANNUAL. Month-grain
-- LGA data exists only inside raw facility-level DHIS2/NHMIS, which is
-- explicitly out of scope (credential-gated). Rather than fabricate a
-- monthly signal that doesn't exist in any genuinely open source, this test
-- operates YEAR-OVER-YEAR, at the actual resolution the open data supports.
--
-- Threshold, grounded in VERIFIED_SOURCES.md (Gombe State, NOT Katsina --
-- Katsina's own completeness has not been separately measured; these numbers
-- justify *where* a threshold is non-arbitrary, they are not claimed as
-- Katsina's own figures):
--   - Bhattacharya et al. found facility-level average completeness of 75%,
--     with the worst-performing indicators (anemia screening, proteinuria
--     screening, malaria IPT) falling under 25-33% of expected reports.
--   - Referral facilities under-reported skilled-birth-attendant deliveries
--     by more than 50% versus paper registers.
-- We treat "under 33% of the basket reported" as a hard floor (the same
-- order of magnitude as Gombe's own worst-performing indicators) and "a
-- year-over-year relative drop of 50% or more" as a sharp-attrition signal
-- (the same order of magnitude as Gombe's documented under-reporting rate).
-- An LGA-year is flagged if either condition holds.

with latest_year_per_lga as (
    select
        location_id,
        lga_name,
        year,
        basket_indicators_reported,
        basket_size,
        completeness_fraction,
        prior_year,
        prior_year_completeness_fraction,
        yoy_relative_drop,
        row_number() over (partition by location_id order by year desc) as rn
    from {{ ref('int_lga_year_over_year') }}
)

select
    location_id,
    lga_name,
    year as latest_year,
    basket_indicators_reported,
    basket_size,
    completeness_fraction,
    prior_year,
    prior_year_completeness_fraction,
    yoy_relative_drop,
    (completeness_fraction < 0.33) as below_gombe_worst_performer_floor,
    (yoy_relative_drop >= 0.50) as sharp_yoy_drop,
    (
        (completeness_fraction < 0.33)
        or (yoy_relative_drop >= 0.50)
    ) as reporting_attrition_flag
from latest_year_per_lga
where rn = 1
