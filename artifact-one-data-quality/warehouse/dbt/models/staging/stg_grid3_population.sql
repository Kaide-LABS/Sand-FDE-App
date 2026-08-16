-- One row per LGA, taking the most recently-fetched GRID3 snapshot. Source:
-- raw.grid3_lga_population, populated by ingestion/fetch_grid3.py from the
-- GRID3/WorldPop "Bottom-up gridded population estimates for Nigeria" v1.2
-- dataset (CC BY 4.0). See README.md for the exact dataset and URL.

with ranked as (
    select
        state,
        lga_name,
        population_mean,
        population_q025,
        population_q975,
        source_label,
        fetched_at,
        row_number() over (
            partition by lga_name
            order by fetched_at desc
        ) as rn
    from raw.grid3_lga_population
)

select
    state,
    trim(lga_name) as lga_name,
    population_mean,
    population_q025,
    population_q975,
    source_label,
    fetched_at
from ranked
where rn = 1
