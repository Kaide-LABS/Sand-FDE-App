-- One row per (LGA, indicator, year). Two distinct kinds of duplication get
-- resolved here, deliberately differently:
--
-- 1. The SAME MSDAT record (record_id) re-fetched across separate pipeline
--    runs -- keep only this pipeline's most recent snapshot of it
--    (`fetched_at`). This is just "don't double-count our own re-pulls."
--
-- 2. MULTIPLE GENUINELY DIFFERENT MSDAT records (distinct record_ids) for
--    the exact same (location, indicator, year) -- this is real, confirmed
--    by direct query: 107 of 5,789 Katsina LGA-indicator-year combinations
--    (~1.8%) have 2-3 distinct record_ids, concentrated almost entirely in
--    year 2023 (97 cases) with a handful in 2024 (10) -- i.e. a dateable
--    MSDAT-side reprocessing event, not an artifact of this pipeline's
--    fetch pattern. Resolved by taking the record with the latest
--    `msdat_updated_at` (MSDAT's own recency signal for that data point),
--    which mirrors MSDAT's own public dashboard: its frontend independently
--    queries `/api/data/?ordering=-updated_at&size=1` elsewhere on the same
--    page (confirmed by network inspection, see README.md), i.e. MSDAT's
--    own convention for "which value is current" when more than one exists
--    is also "most recently updated wins." `record_id desc` is an
--    additional deterministic tiebreak for the rare case of identical
--    `msdat_updated_at` timestamps -- it never fires in practice against
--    the live data at time of writing, but keeps this query's output fully
--    deterministic regardless.
--
-- Source: raw.msdat_indicator_values, populated by ingestion/fetch_msdat.py
-- from a live pull of MSDAT's public /api/data/ endpoint.

with latest_snapshot_per_record as (
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
            partition by record_id
            order by fetched_at desc
        ) as snapshot_rn
    from raw.msdat_indicator_values
),

latest_record_per_period as (
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
            order by msdat_updated_at desc, record_id desc
        ) as period_rn
    from latest_snapshot_per_record
    where snapshot_rn = 1
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
from latest_record_per_period
where period_rn = 1
