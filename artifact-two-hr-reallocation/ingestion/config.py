"""Constants that anchor the ingestion (and, by extension, the optimizer's)
layer to the Borno State PHC Workers Baseline Mapping Exercise PDF
(reference/borno_phc_baseline.pdf) and to the specific cadre scope, file
locations, and documented totals ULTIMATE_PRD.md verified against that PDF.

Nothing here is invented: every constant traces to a specific PDF page/table
citation already recorded as a header comment in the corresponding
data/*.csv file, or to ULTIMATE_PRD.md's own MODERNIZATION CHANGELOG
(Sec.2) and Data model (Sec.3) sections. Mirrors
../artifact-one-data-quality/ingestion/config.py's citation discipline.

# Implements PHASE_1_SPEC.md Sec.1 (ingestion/config.py), Sec.3 (PHASE_1_CADRES).
"""

from __future__ import annotations

from pathlib import Path

# --- File locations ---------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LGA_CURRENT_STAFFING_CSV = DATA_DIR / "lga_current_staffing.csv"
STATE_STAFFING_GAP_CSV = DATA_DIR / "state_staffing_gap.csv"
LGA_FACILITY_COUNT_CSV = DATA_DIR / "lga_facility_count.csv"
LGA_FACILITY_DENSITY_CSV = DATA_DIR / "lga_facility_density.csv"
NPHCDA_MINIMUM_STANDARD_CSV = DATA_DIR / "nphcda_minimum_standard.csv"

# --- Cadre scope --------------------------------------------------------------
#
# Table 1 (PDF p.21-22) lists 8 cadre columns for current headcount:
ALL_TABLE1_CADRE_COLUMNS: tuple[str, ...] = (
    "community_health_officer",
    "community_health_extension_worker",
    "junior_community_health_extension_worker",
    "health_information_management",
    "medical_doctor",
    "medical_laboratory_scientist",
    "nurse_midwife",
    "pharmacist",
)

# The four cadres with an exact, unambiguous name match between Table 1
# (current-headcount source) and Table 4/6/7 (gap-analysis source) --
# ULTIMATE_PRD.md Sec.2 finding 5, Sec.5. This is the single source of truth
# for the Phase-1 decision-variable cadre set; optimizer/models.py imports
# it rather than redefining the tuple, so the two files cannot drift apart.
#
# Pharmacist/Medical Laboratory Scientist/Health Information
# Management/Medical Doctor are NEVER decision-variable cadres in Phase 1 --
# if a future change adds them, it must also add the disclosed
# Pharmacist<->Pharmacy Technician / Medical Laboratory Scientist<->Lab
# Technician name-mapping assumption ULTIMATE_PRD.md Sec.5 explicitly
# deferred, not silently widen this tuple.
PHASE_1_CADRES: tuple[str, str, str, str] = (
    "community_health_officer",
    "community_health_extension_worker",
    "junior_community_health_extension_worker",
    "nurse_midwife",
)

# --- Documented expected totals (ULTIMATE_PRD.md Sec.2 finding 9, Sec.3.1) ----
#
# Used by tests/test_csv_sums.py to catch a future edit to data/*.csv
# silently breaking agreement with the PDF's own totals. These are the CSVs'
# own internal sums/row-counts, not a re-derivation from the PDF -- the CSVs
# are the confirmed, checked-in ground truth (PHASE_1_SPEC.md Sec.1).
EXPECTED_LGA_ROW_COUNT = 26  # Guzamala absent from Table 1 and Figures 1-2 alike.
EXPECTED_GRAND_TOTAL_SUM = 3_915  # Table 1's own listed rows; PDF's stated Grand Total is 3,916
# (a 1-worker discrepancy in the primary source itself -- ULTIMATE_PRD.md Sec.2 finding 9).
EXPECTED_GAP_ACROSS_STATE_SUM = 2_860  # Table 4/7; the Executive Summary's 2,628 is an
# unreconciled outlier (ULTIMATE_PRD.md Sec.2 finding 1) -- not used anywhere in this artifact.
EXPECTED_FACILITY_COUNT_SUM = 329  # Figure 1; matches the PDF's own stated total facility count.
