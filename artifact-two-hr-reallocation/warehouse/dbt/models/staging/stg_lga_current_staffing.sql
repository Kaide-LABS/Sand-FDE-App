-- Thin pass-through of raw.lga_current_staffing (PDF Table 1, p.21-22).
-- Already-clean, single-snapshot data -- no dedup logic needed here, unlike
-- ../artifact-one-data-quality's MSDAT staging models, which handle
-- multi-record dedup over repeated live pulls. See PHASE_1_SPEC.md Sec.6
-- step 2.

select
    trim(lga) as lga,
    community_health_officer,
    community_health_extension_worker,
    junior_community_health_extension_worker,
    health_information_management,
    medical_doctor,
    medical_laboratory_scientist,
    nurse_midwife,
    pharmacist,
    total_core_health_workers,
    total_support_health_workers,
    grand_total
from {{ source('raw', 'lga_current_staffing') }}
