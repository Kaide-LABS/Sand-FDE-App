-- dbt test implementing constraint 1 (reporting-volume attrition).
--
-- This is deliberately severity=warn, not error: a "failing" row here is the
-- detection signal this whole pipeline exists to produce, not a pipeline
-- defect. `dbt test` reports every LGA that trips the attrition flag defined
-- in models/marts/lga_reporting_attrition.sql (see that model for the exact
-- thresholds and their Gombe-study grounding); those rows are also visible,
-- with full context, in the lga_data_toxicity_audit mart.

{{ config(severity='warn') }}

select *
from {{ ref('lga_reporting_attrition') }}
where reporting_attrition_flag
