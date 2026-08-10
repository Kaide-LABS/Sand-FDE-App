-- One row per (LGA, indicator, year), taking the most recently-fetched MSDAT
-- snapshot when this pipeline has been run more than once. Source:
-- raw.msdat_indicator_values, populated by ingestion/fetch_msdat.py from a
-- live pull of MSDAT's public /api/data/ endpoint (see README.md).

with ranked as (
    select
        record_id,
        indicator_id,
        indicator_name,
        datasource_id,
        location_id,
        lga_name,
        period,
        year,
        value,
        msdat_updated_at,
        fetched_at,
        row_number() over (
            partition by location_id, indicator_id, year
            order by fetched_at desc
        ) as rn
    from raw.msdat_indicator_values
)

select
    record_id,
    indicator_id,
    indicator_name,
    datasource_id,
    location_id,
    trim(lga_name) as lga_name,
    period,
    year,
    value,
    msdat_updated_at,
    fetched_at
from ranked
where rn = 1
