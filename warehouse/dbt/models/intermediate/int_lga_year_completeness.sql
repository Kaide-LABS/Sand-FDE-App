-- Per LGA-year: how many of the reporting-basket indicators MSDAT
-- actually has a value for, out of the full basket size. This is our proxy for
-- "reported indicator volume" at the only grain MSDAT's public LGA-level
-- aggregate actually publishes (annual) -- see the reporting-volume-attrition
-- mart for the full justification of that adaptation, grounded in the Gombe
-- State DHIS2 completeness study cited in VERIFIED_SOURCES.md.
--
-- Every (LGA x year) combination present in the source data is included even
-- when zero basket indicators were reported that year -- an LGA that reports
-- nothing is the most toxic case this test is designed to catch, not a row to
-- silently drop.

with basket_size as (
    select count(*) as n
    from {{ ref('indicator_reference') }}
    where in_reporting_basket
),

years_present as (
    select distinct year
    from {{ ref('stg_msdat_indicator_values') }}
),

lga_years as (
    select
        lga.location_id,
        lga.lga_name,
        yrs.year
    from {{ ref('dim_lga') }} as lga
    cross join years_present as yrs
),

reported_counts as (
    select
        location_id,
        lga_name,
        year,
        count(distinct indicator_id) as basket_indicators_reported
    from {{ ref('int_msdat_tagged') }}
    where in_reporting_basket
    group by 1, 2, 3
)

select
    ly.location_id,
    ly.lga_name,
    ly.year,
    coalesce(rc.basket_indicators_reported, 0) as basket_indicators_reported,
    bs.n as basket_size,
    round(
        coalesce(rc.basket_indicators_reported, 0)::numeric / nullif(bs.n, 0),
        4
    ) as completeness_fraction
from lga_years as ly
left join reported_counts as rc
    on ly.location_id = rc.location_id and ly.year = rc.year
cross join basket_size as bs
