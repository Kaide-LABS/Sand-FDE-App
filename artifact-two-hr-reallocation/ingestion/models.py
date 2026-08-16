"""Typed records for every row this pipeline ingests from the five checked-in
data/*.csv extractions of the Borno PHC baseline PDF.

Every model uses `model_config = ConfigDict(extra="forbid")` so that an
accidental edit to a CSV's header (an added, removed, or renamed column)
fails loudly at ingestion time instead of silently passing an unvalidated
row deeper into the pipeline -- matching
../artifact-one-data-quality/ingestion/models.py's discipline exactly.

# Implements PHASE_1_SPEC.md Sec.3 (ingestion/models.py).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LgaCurrentStaffing(BaseModel):
    """One row of PDF Table 1 (p.21-22): current PHC worker headcount by LGA
    and cadre. 26 rows -- Guzamala is absent from the source table itself
    (ULTIMATE_PRD.md Sec.2 finding 9); never synthesized here.
    """

    model_config = ConfigDict(extra="forbid")

    lga: str
    community_health_officer: int = Field(ge=0)
    community_health_extension_worker: int = Field(ge=0)
    junior_community_health_extension_worker: int = Field(ge=0)
    health_information_management: int = Field(ge=0)
    medical_doctor: int = Field(ge=0)
    medical_laboratory_scientist: int = Field(ge=0)
    nurse_midwife: int = Field(ge=0)
    pharmacist: int = Field(ge=0)
    total_core_health_workers: int = Field(ge=0)
    total_support_health_workers: int = Field(ge=0)
    grand_total: int = Field(ge=0)


class StateStaffingGap(BaseModel):
    """One row of PDF Table 4 (p.25): state-level (not per-LGA) staffing gap
    by professional area, cross-check only -- see ULTIMATE_PRD.md Sec.3.1.
    """

    model_config = ConfigDict(extra="forbid")

    phc_personnel: str
    minimum_no_per_phc: int = Field(ge=0)
    total_required_across_state: int = Field(ge=0)
    total_available_across_state: int = Field(ge=0)
    gap_across_state: int = Field(ge=0)


class LgaFacilityCount(BaseModel):
    """One row of PDF Figure 1 (p.13, bar chart): facility count per LGA.
    Read from a chart image, not a text-layer table -- highest
    transcription-risk file in this dataset (ULTIMATE_PRD.md Sec.2 finding 10).
    """

    model_config = ConfigDict(extra="forbid")

    lga: str
    facility_count: int = Field(ge=0)


class LgaFacilityDensity(BaseModel):
    """One row of PDF Figure 2 (p.14, bar chart): health facility density per
    10,000 population per LGA. Same chart-image transcription-risk caveat as
    LgaFacilityCount.
    """

    model_config = ConfigDict(extra="forbid")

    lga: str
    density_per_10k_population: float = Field(ge=0)


class NphcdaMinimumStandard(BaseModel):
    """One row of PDF Table 6 (p.26): NPHCDA's minimum staffing standard per
    PHC. Documentation/context only -- never used as the optimizer's floor
    (ULTIMATE_PRD.md Sec.3.1, Sec.6).
    """

    model_config = ConfigDict(extra="forbid")

    minimum_standard: str
    minimum_no_per_phc: int = Field(ge=0)
