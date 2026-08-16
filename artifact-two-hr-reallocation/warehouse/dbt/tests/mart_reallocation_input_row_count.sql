-- mart_reallocation_input must have exactly 26 rows -- one per LGA PDF
-- Table 1 lists (ULTIMATE_PRD.md Sec.2 finding 9; PHASE_1_SPEC.md Sec.6
-- step 3). A count other than 26 means stg_lga_current_staffing and
-- stg_lga_population_proxy have silently drifted out of agreement on which
-- 26 LGAs are covered.
--
-- A dbt test fails if it returns any rows -- this returns one row only when
-- the count is wrong.

select count(*) as actual_row_count
from {{ ref('mart_reallocation_input') }}
having count(*) != 26
