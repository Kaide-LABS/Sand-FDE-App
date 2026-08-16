-- Derives an LGA population proxy from the PDF's own Figure 1 (facility
-- count per LGA, p.13) and Figure 2 (facility density per 10,000
-- population per LGA, p.14) -- ULTIMATE_PRD.md Sec.3.2. No LGA or ward
-- population figure appears anywhere in the source document itself; this is
-- a derived, chart-read figure, never a directly reported one, and every
-- rendered output that uses it must say so explicitly (viz/generate_report.py).
--
--   LGA_population[k] ~= facility_count[k] / density_per_10k[k] * 10,000
--
-- Reconciliation against the PDF's own stated state-level figures happens
-- in warehouse/dbt/tests/population_proxy_reconciliation.sql, not here --
-- see that file for why the reconciliation target is the state's own
-- facility-count/density identity (329 facilities / 0.8 per 10k), not the
-- separately-stated ~6.9M total state population, which uses a different,
-- non-reconcilable population base (a genuine internal inconsistency in the
-- source document, disclosed there rather than silently resolved).

select
    trim(fc.lga) as lga,
    fc.facility_count,
    fd.density_per_10k_population,
    (fc.facility_count / fd.density_per_10k_population) * 10000 as population_proxy
from {{ source('raw', 'lga_facility_count') }} fc
inner join {{ source('raw', 'lga_facility_density') }} fd
    on trim(fc.lga) = trim(fd.lga)
where fd.density_per_10k_population > 0
