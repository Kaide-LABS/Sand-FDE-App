{{
    config(
        materialized='table'
    )
}}

-- THE optimizer's input table. One row per LGA covered by PDF Table 1 --
-- exactly 26 rows (Guzamala absent, ULTIMATE_PRD.md Sec.2 finding 9; this
-- inner join intentionally does not backfill it). Exposes only the four
-- Phase-1 decision-variable cadres (community_health_officer,
-- community_health_extension_worker,
-- junior_community_health_extension_worker, nurse_midwife --
-- ULTIMATE_PRD.md Sec.5) plus grand_total (all 8 cadres, used for the
-- staff-to-population ratio metric) and the derived population proxy.
--
-- ratio = grand_total / population_proxy -- current staff-to-population
-- ratio per LGA, the metric optimizer/formulate.py's objective minimizes
-- the dispersion of (ULTIMATE_PRD.md Sec.4).

select
    s.lga,
    s.community_health_officer,
    s.community_health_extension_worker,
    s.junior_community_health_extension_worker,
    s.nurse_midwife,
    s.grand_total,
    p.population_proxy,
    s.grand_total / p.population_proxy as ratio
from {{ ref('stg_lga_current_staffing') }} s
inner join {{ ref('stg_lga_population_proxy') }} p
    on s.lga = p.lga
