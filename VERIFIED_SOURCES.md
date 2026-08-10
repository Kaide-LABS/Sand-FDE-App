# Verified Sources

Primary-source verification pass against the load-bearing claims in the original research brief
(`NIGERIA_HEALTH_TARGET_BRIEF.md` / "Nigerian Health Data Architecture Plan.md"), run before scaffolding
the build. Per the confirmed acceptance criteria, every factual claim reaching Sand must trace to a
primary source -- this file is that trace. Checked 2026-08-10.

## Confirmed real (safe to cite)

### MSDAT's two-month reporting latency
**Verbatim, from the MSDAT legacy platform's own disclaimer**
(https://msdat.old.fmohconnect.gov.ng/covid19_health_service_uptake/index.html):

> "There is usually a two month time lag before data appears on the system and dependent on
> reporting rates from facilities."

This is a primary-source platform disclaimer, not a misattributed study. The original brief's citation
was vague (pointed at a COVID service-uptake page without quoting it); the underlying claim holds up.
Cite the platform disclaimer directly, not the brief.

### Gombe State DHIS2 data quality (Bhattacharya et al. 2019, PLOS ONE)
PMID 30682130, DOI 10.1371/journal.pone.0211265, https://pubmed.ncbi.nlm.nih.gov/30682130/

Facilities offering ANC/postnatal care (n=497) and labor/delivery services (n=486) in Gombe State,
audited July 2016-June 2017 against facility registers (register extraction Jan-Jun 2017; 97 primary +
18 referral facilities compared directly).

- Facility-level average reporting completeness: **75%** of expected monthly reports submitted.
- Indicator-level completeness range: best performers (first ANC visit, facility deliveries, tetanus
  toxoid) at **52-65%** of expected/submitted reports; worst performers (anemia screening, proteinuria
  screening, malaria IPT) under **25-33%**.
- Denominators (ANC visits, facility deliveries, live births) agreed well between DHIS2 and registers.
- **Over-reporting** vs. paper registers: **50-60%** higher in DHIS2 for skilled-birth-attendant
  deliveries and early postpartum/postnatal care.
- **Under-reporting** vs. paper registers: referral facilities under-reported skilled-birth-attendant
  deliveries by **more than 50%**.
- 12 of 14 priority maternal/neonatal indicators were assessable in DHIS2 (2 -- oxytocin for PPH
  prevention, essential newborn care -- captured in registers but absent from DHIS2 entirely).

These are the real numbers behind the brief's vague "40% incomplete, 10-60% underreport" claim --
use these instead; they are precise, sourced, and Nigeria-specific (not national, Gombe State only).

### Bauchi State vaccine stockout prevalence, pre-intervention (Sato et al. 2023, BMC Public Health)
PMID 37658292, DOI 10.1186/s12889-023-16575-x

Cost analysis of Nigeria's Vaccine Direct Delivery (VDD) program. The paper's own facility-level data
(Table 2) reports pre-VDD stockout prevalence in **Bauchi State** of approximately **39% (0.389)**.
This is a real, Nigeria-specific, correctly-scoped figure from the study's own analysis -- always cite
it as "Bauchi State, pre-intervention," never generalized to "national."

## Confirmed misattributed or wrongly scoped -- do not cite as originally framed

### "38% national stock-out prevalence" (as stated in the original brief)
Same paper as above (Sato et al. 2023) does contain a "38%" figure, but it is a citation to a
**different** paper describing **sub-Saharan Africa as a whole**, not Nigeria:

> "38% of sub-Saharan countries experience national-level stockouts" -- citing Lydon P, Schreiber B,
> Gasca A, Dumolard L, Urfer D, Senouci K. "Vaccine stockouts around the world: are essential vaccines
> always available when needed?" Vaccine. 2017;35(17):2121-6.

The brief's claim of a "historically documented national [Nigerian] stock-out prevalence rate of 38%"
is not supported by this citation. If a stockout figure is needed, use the Bauchi State 39% figure
above instead, correctly scoped.

### "HFR severely undercounts private facilities" via TB service-disruption study
The cited paper (Oga-Omenka et al. 2023, PLOS Global Public Health, PMID 36963094, DOI
10.1371/journal.pgph.0001618) is a mixed-methods study of **COVID-19's effect on private-sector TB
service delivery** in Kano and Lagos (2,412 facilities surveyed on service disruption, screening
uptake, and notification volume during lockdown). It contains no comparison between the Health
Facility Registry's facility counts and any independent private-facility census. It cannot support a
claim about HFR undercounting. Red-team finding confirmed -- do not cite this paper for that claim.

## Resolved during the build phase

### MSDAT live-API accessibility -- RESOLVED: a genuine, scrapable, credential-free API exists
Investigated 2026-08-10 by headless-browser network-tab inspection of
`https://msdat.fmohconnect.gov.ng/dashboard/Health_Outcomes_and_Service_Coverage`, followed by direct
probing with plain HTTP requests to confirm the browser was not load-bearing. Findings:

- MSDAT's public web app calls a real REST backend at `https://msdat-api.fmohconnect.gov.ng/api/`.
- Anonymous visitors are issued a short-lived (~15 minute) JWT by `POST
  {base}auth/frontend-token/`, authenticated with two header values (`x-frontend-key-id` and a
  matching `x-frontend-auth` hash) that are **static, shipped in plaintext inside MSDAT's own
  public JS bundle** (`VUE_APP_FRONTEND_KEY_ID` / `VUE_APP_FRONTEND_AUTH` in `js/app.<hash>.js`).
  This is the exact mechanism every browser that loads the public dashboard uses; it is not a
  Ministry-issued credential, there is no account, login form, or registration involved, and the
  same two static values work from a plain `requests.post()` call with no browser at all (verified
  directly). The exact values are deliberately not reproduced here or anywhere else in this repo --
  `ingestion/msdat_key_discovery.py` extracts them at run time from MSDAT's own live JS on every
  pipeline invocation instead of pinning them as literals, so nothing credential-shaped sits in
  tracked source regardless of how public the underlying value is.
- That token, sent as `x-frontend-jwt: Token <jwt>`, authorizes read access to
  `/api/location/`, `/api/indicators/`, `/api/datasources/`, `/api/datasource_specific_indicator/`,
  and `/api/data/` -- the endpoints that actually carry indicator values.
- Location hierarchy: Katsina State is `location=28`; its 34 LGAs are a specific, enumerated set of
  location IDs (see `ingestion/config.py`) one level below it.
- Data grain, established by direct query (not assumed): MSDAT's **NHMIS (Facility-based)**
  datasource (`datasource=6`) publishes LGA-level values, but at **annual** grain only (period
  labels like `"2024"`). MSDAT also runs an **NHMIS monthly (Facility-based)** datasource
  (`datasource=30`) with true month-grain periods (e.g. `"Jun 2026"`), but querying it for any
  Katsina LGA location ID returns zero rows -- it only publishes at State and National level.
  True LGA-by-month figures exist only inside raw facility-level DHIS2/NHMIS, which is out of scope
  (credential-gated). This is why the pipeline's reporting-volume-attrition test operates
  year-over-year rather than month-over-month -- see `warehouse/dbt/models/marts/lga_reporting_attrition.sql`.
- MSDAT's own indicator metadata (`/api/datasource_specific_indicator/`) documents, for several
  coverage indicators, an explicit fixed population-fraction denominator in plain text -- e.g. ANC
  Coverage (1 Visit): "5% of the total population"; DPT3/Penta 3 coverage: "4% of the total
  population". These strings are quoted directly from MSDAT's own API response, not inferred, and
  are what the biological-impossibility test's population denominators are built from (in
  combination with GRID3, not MSDAT's own unstated population source -- see below).

Net effect on scope: no manual-extraction fallback was needed. Every MSDAT figure this pipeline
uses is a live pull against the real API, re-executed on every pipeline run.

### GRID3 LGA population baseline
GRID3/WorldPop "Bottom-up gridded population estimates for Nigeria", version 1.2 (CC BY 4.0),
published via the Humanitarian Data Exchange:
https://data.humdata.org/dataset/bottom-up-gridded-population-estimates-for-nigeria . The
admin-level-3 (LGA) summary CSV inside that release's `NGA_population_v1_2_admin.zip` (resolved via
HDX's own package API to `https://wopr.worldpop.org/download/2` as of 2026-08-10) contains all 774
Nigerian LGAs, including all 34 Katsina LGAs by name, with a posterior mean population estimate and
a 95% uncertainty interval (q025-q975) per LGA. This is the population denominator source the
biological-impossibility test uses -- independent of whatever population figure MSDAT itself uses
internally, which MSDAT does not document.

## Not yet re-verified

The following brief citations were flagged by the earlier red-team but not re-checked in this pass;
treat as still unverified until checked the same way as the above:
- "NSHIP data restricted" (originally cited to a Uganda DHIS2 study and a Walden dissertation on place
  of delivery -- neither concerns NSHIP).
- The routine-immunization DHIS2 national-rollout narrative's specific 53%-to-80%-completeness
  improvement figures (Shuaib et al. 2020, PMID 32694218 -- abstract confirms the rollout timeline and
  scale but the specific completeness percentages need pulling from the full text, not assumed from
  the brief).
