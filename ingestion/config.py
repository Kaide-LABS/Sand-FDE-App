"""Constants that anchor the ingestion layer to Katsina State and to the specific
MSDAT indicators / GRID3 population figures this pipeline uses.

Every ID and formula in this file was captured by hands-on inspection of the live
MSDAT platform on 2026-08-10 (network-tab-style inspection of
https://msdat.fmohconnect.gov.ng/, see README.md "MSDAT investigation" section for
the full methodology and evidence). Nothing here is invented -- location IDs,
indicator IDs and denominator formulas are all direct copies of what MSDAT's own
API returns for its own metadata endpoints.
"""

from __future__ import annotations

# --- MSDAT API -------------------------------------------------------------
#
# MSDAT's public web app (https://msdat.fmohconnect.gov.ng/) is a Vue.js SPA that
# calls a REST backend at MSDAT_API_BASE. Anonymous visitors (i.e. anyone loading
# the public site, no login) are issued a short-lived (15 minute) JWT by POSTing to
# `${MSDAT_API_BASE}auth/frontend-token/` with two headers whose values are baked
# in plaintext into MSDAT's own publicly-shipped JS bundle
# (js/app.<hash>.js, VUE_APP_FRONTEND_KEY_ID / VUE_APP_FRONTEND_AUTH). This is the
# same mechanism every browser that loads the public dashboard uses -- it is not a
# Ministry-issued credential, there is no login form involved, and no account is
# required to obtain it. See README.md for the exact discovery steps.
MSDAT_API_BASE = "https://msdat-api.fmohconnect.gov.ng/api/"
MSDAT_FRONTEND_KEY_ID = "msdat_key_v1"
MSDAT_FRONTEND_AUTH = "REDACTED_MSDAT_FRONTEND_AUTH_KEY_SEE_ingestion_msdat_key_discovery_py"

# --- Location hierarchy ------------------------------------------------------
# MSDAT location IDs, taken verbatim from GET {MSDAT_API_BASE}location/?size=1500.
KATSINA_STATE_LOCATION_ID = 28

# (location_id, LGA name without the " LGA" suffix). MSDAT lists 34 level-4
# ("LGA") locations under Katsina (location=28); it additionally lists 3 level-5
# "Senatorial District" locations under the same parent, which are excluded here
# since they are not LGAs. Names are given in the form used to join against the
# GRID3 population table (see grid3_client.py), where they match exactly.
KATSINA_LGAS: list[tuple[int, str]] = [
    (458, "Bakori"),
    (459, "Batagarawa"),
    (460, "Batsari"),
    (461, "Baure"),
    (462, "Bindawa"),
    (463, "Charanchi"),
    (464, "Dan Musa"),
    (465, "Dandume"),
    (466, "Danja"),
    (467, "Daura"),
    (468, "Dutsi"),
    (469, "Dutsin Ma"),
    (470, "Faskari"),
    (471, "Funtua"),
    (472, "Ingawa"),
    (473, "Jibia"),
    (474, "Kafur"),
    (475, "Kaita"),
    (476, "Kankara"),
    (477, "Kankia"),
    (478, "Katsina"),
    (479, "Kurfi"),
    (480, "Kusada"),
    (481, "Mai'Adua"),
    (482, "Malumfashi"),
    (483, "Mani"),
    (484, "Mashi"),
    (485, "Matazu"),
    (486, "Musawa"),
    (487, "Rimi"),
    (488, "Sabuwa"),
    (489, "Safana"),
    (490, "Sandamu"),
    (491, "Zango"),
]

# --- Datasource ---------------------------------------------------------------
# MSDAT datasource id 6 = "NHMIS (Facility-based)" (National Health Management
# Information System). This is the only MSDAT datasource that publishes
# LGA-level values for the coverage/service-delivery indicators below.
# Confirmed by hands-on inspection: its publication grain at LGA level is
# ANNUAL (one row per LGA per calendar year, period values like "2024"), not
# monthly. MSDAT also runs an "NHMIS monthly (Facility-based)" datasource
# (id 30) with true month-grain periods (e.g. "Jun 2026"), but that datasource
# only publishes at STATE and National level -- querying it for any Katsina LGA
# location id returns zero rows. See README.md for the exact API calls that
# established this. This is why the reporting-volume-attrition model below
# operates year-over-year rather than month-over-month: month-grain LGA data
# simply does not exist in MSDAT's public aggregate (only in raw facility-level
# DHIS2/NHMIS, which is explicitly out of scope -- credential-gated).
NHMIS_ANNUAL_DATASOURCE_ID = 6

# Full basket of NHMIS-annual indicators that MSDAT itself tags as LGA-level +
# "Monthly" underlying reporting frequency (per
# GET {MSDAT_API_BASE}datasource_specific_indicator/?size=5000, filtered to
# datasource=6 and lga=true). This basket defines "expected reporting volume":
# for a given LGA-year, reporting completeness = (how many of these 24
# indicators have a non-null reported value that year) / 24.
REPORTING_BASKET_INDICATORS: list[tuple[int, str]] = [
    (23, "Antenatal revisits receiving IPT2"),
    (5, "ANC Coverage (1 Visit)"),
    (21, "Pct children fully immunized by age 1"),
    (30, "Neonatal mortality rate (facility)"),
    (32, "Under 5 mortality rate (facility)"),
    (584, "Rotavirus 1 Vaccine Coverage"),
    (585, "Rotavirus 2 Vaccine Coverage"),
    (586, "Rotavirus 3 Vaccine Coverage"),
    (587, "Yellow Fever Coverage"),
    (19, "IPV Coverage (Annualized)"),
    (6, "ANC Coverage (4 Visits)"),
    (4, "Contraceptive Prevalence Rate"),
    (31, "Infant Mortality Rate"),
    (16, "Underweight Rate (<5 years, facility)"),
    (29, "Maternal mortality ratio (facility)"),
    (20, "Measles Dose Coverage (Annualized)"),
    (1, "Fertility Rate"),
    (18, "DPT 3/Penta 3 coverage rate (Annualized)"),
    (457, "Deliveries by skilled birth attendants"),
    (212, "DPT 1/Penta 1 coverage rate (Annualized)"),
    (410, "Tetanus Toxoid (2+) Coverage"),
    (22, "Pct Antenatal 1st Visits receiving IPT1"),
    (398, "PNC1 / Live births"),
    (330, "Antenatal 1st visits before 20 weeks rate"),
]

# Subset of the basket above for which MSDAT's own indicator metadata documents
# an explicit, fixed "X% of total population" denominator (rather than a
# denominator defined relative to some other reported count, e.g. "live
# births" or "ANC attendance", which cannot be independently checked against a
# population baseline). Only this subset is used for the biological-
# impossibility test, specifically so that every population figure the test
# relies on traces to a quoted, primary-source formula -- never an invented
# demographic assumption.
#
# (indicator_id, short_name, population_fraction, denominator_text_from_MSDAT)
IMPOSSIBILITY_INDICATORS: list[tuple[int, str, float, str]] = [
    (5, "ANC Coverage (1 Visit)", 0.05, "5% of the total population"),
    (6, "ANC Coverage (4 Visits)", 0.05, "5% of the total population"),
    (21, "Pct children fully immunized by age 1", 0.04, "4% of the total population"),
    (584, "Rotavirus 1 Vaccine Coverage", 0.04, "0.04*Total Population"),
    (585, "Rotavirus 2 Vaccine Coverage", 0.04, "0.04*Total Population"),
    (586, "Rotavirus 3 Vaccine Coverage", 0.04, "0.04*Total Population"),
    (587, "Yellow Fever Coverage", 0.04, "0.04*Total Population"),
    (19, "IPV Coverage (Annualized)", 0.04, "4% of the total Population"),
    (18, "DPT 3/Penta 3 coverage rate (Annualized)", 0.04, "4% of the total population"),
    (212, "DPT 1/Penta 1 coverage rate (Annualized)", 0.04, "4% of the total population"),
    (410, "Tetanus Toxoid (2+) Coverage", 0.05, "Total Population *0.05"),
    (20, "Measles Dose Coverage (Annualized)", 0.04, "4% of the total Population"),
]

# Years to retain after pulling MSDAT's full period history for each
# LGA/indicator pair. MSDAT's own LGA-annual history for these indicators goes
# back to 2013; we keep a recent window that is long enough to compute
# multiple year-over-year comparisons without dragging in the sparsest early
# years.
MIN_YEAR = 2015
MAX_YEAR = 2025

# --- GRID3 population baseline -------------------------------------------------
# GRID3 / WorldPop "Bottom-up gridded population estimates for Nigeria",
# version 1.2 (CC BY 4.0). Published via the Humanitarian Data Exchange:
# https://data.humdata.org/dataset/bottom-up-gridded-population-estimates-for-nigeria
# The admin-level-3 (LGA) summary table used here is
# NGA_population_v1_2_admin_level3.csv, bundled inside NGA_population_v1_2_admin.zip,
# hosted at https://wopr.worldpop.org/download/2 (the exact URL HDX's own package
# API resolves the resource to as of 2026-08-10).
GRID3_ADMIN_ZIP_URL = "https://wopr.worldpop.org/download/2"
GRID3_DATASET_LABEL = (
    "GRID3/WorldPop Bottom-up gridded population estimates for Nigeria, v1.2 (CC BY 4.0)"
)
