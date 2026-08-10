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

## Still open

### MSDAT live-API accessibility
`https://msdat.fmohconnect.gov.ng/` renders as a JS-driven single-page app -- a static fetch returns
no substantive content, only a page title. This does not confirm or rule out a scrapable underlying
API; it only confirms that the answer cannot be determined by fetching the page as HTML. Needs
hands-on verification (browser network-tab inspection, or direct probing of likely DHIS2-analytics-API
style endpoints) during the build phase before the ingestion DAG is designed around an assumed
API/export path.

## Not yet re-verified

The following brief citations were flagged by the earlier red-team but not re-checked in this pass;
treat as still unverified until checked the same way as the above:
- "NSHIP data restricted" (originally cited to a Uganda DHIS2 study and a Walden dissertation on place
  of delivery -- neither concerns NSHIP).
- The routine-immunization DHIS2 national-rollout narrative's specific 53%-to-80%-completeness
  improvement figures (Shuaib et al. 2020, PMID 32694218 -- abstract confirms the rollout timeline and
  scale but the specific completeness percentages need pulling from the full text, not assumed from
  the brief).
