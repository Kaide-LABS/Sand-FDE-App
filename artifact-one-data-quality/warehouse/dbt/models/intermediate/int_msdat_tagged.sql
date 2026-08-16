-- MSDAT indicator values tagged with basket / impossibility-test membership
-- from the indicator_reference seed (which mirrors ingestion/config.py's
-- REPORTING_BASKET_INDICATORS and IMPOSSIBILITY_INDICATORS -- see that file
-- for how each entry was sourced from MSDAT's own metadata).

select
    stg.location_id,
    stg.lga_name,
    stg.indicator_id,
    stg.indicator_name,
    stg.year,
    stg.value,
    ref.in_reporting_basket,
    ref.in_impossibility_test,
    ref.population_fraction,
    ref.denominator_source_text
from {{ ref('stg_msdat_indicator_values') }} as stg
inner join {{ ref('indicator_reference') }} as ref
    on stg.indicator_id = ref.indicator_id
