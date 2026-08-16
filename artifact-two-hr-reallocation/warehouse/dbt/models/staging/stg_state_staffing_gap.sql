-- Thin pass-through of raw.state_staffing_gap (PDF Table 4, p.25).
-- State-level only, cross-check use (ULTIMATE_PRD.md Sec.3.1) -- not joined
-- into mart_reallocation_input, since it has no per-LGA grain.

select
    trim(phc_personnel) as phc_personnel,
    minimum_no_per_phc,
    total_required_across_state,
    total_available_across_state,
    gap_across_state
from {{ source('raw', 'state_staffing_gap') }}
