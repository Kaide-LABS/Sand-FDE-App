-- Adds the prior year's completeness fraction (per LGA) so we can compute a
-- year-over-year drop in reported indicator volume.

select
    location_id,
    lga_name,
    year,
    basket_indicators_reported,
    basket_size,
    completeness_fraction,
    lag(completeness_fraction) over (
        partition by location_id order by year
    ) as prior_year_completeness_fraction,
    lag(year) over (
        partition by location_id order by year
    ) as prior_year,
    case
        when lag(completeness_fraction) over (partition by location_id order by year) > 0
            then round(
                (
                    lag(completeness_fraction) over (partition by location_id order by year)
                    - completeness_fraction
                ) / lag(completeness_fraction) over (partition by location_id order by year),
                4
            )
        else null
    end as yoy_relative_drop
from {{ ref('int_lga_year_completeness') }}
