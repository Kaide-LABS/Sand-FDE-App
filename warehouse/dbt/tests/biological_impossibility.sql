-- dbt test implementing constraint 2 (biological impossibility).
--
-- severity=warn for the same reason as reporting_volume_attrition.sql: a
-- "failing" row is a detected LGA/indicator/year where MSDAT's reported
-- coverage, applied to GRID3's population estimate, implies more people were
-- served than the documented target population could contain. See
-- models/intermediate/int_lga_impossibility_detail.sql for the exact
-- computation and its sourcing.

{{ config(severity='warn') }}

select *
from {{ ref('int_lga_impossibility_detail') }}
where is_impossible
