# Sand Technologies FDE Application

Two unsolicited technical artifacts built to accompany a Forward Deployed Engineer (Nigeria)
application to Sand Technologies. Sand's own public position is "Foundations Over Features": that
generative AI and dashboards built on top of broken or ungrounded data are the wrong first move,
and that the unglamorous work -- finding out where data can't be trusted, then acting on data once
it can be -- is the right one. Both artifacts try to demonstrate that kind of work directly, in
Sand's own stack (Python, PostgreSQL, Airflow, dbt, Superset), rather than describe it.

They are deliberately sequential, not two unrelated demos:

- **Artifact One** answers the question that has to come first: *can this data be trusted at all?*
  It is a deterministic data-quality audit of Katsina State's health reporting, and it finds real,
  citable problems in the data itself (reporting attrition, biologically impossible coverage
  values) without touching what any of it means for care delivery.
- **Artifact Two** assumes data that has cleared that bar and asks the next question: *given
  trustworthy data, what physical, real-world action does it justify?* It targets a different
  documented operational bottleneck in the Nigerian health system and produces a specific,
  actionable recommendation rather than another dashboard.

Read that as the throughline: trust the data first, then use it to make something happen.

## Artifacts

| | What it does | Status |
|---|---|---|
| [`artifact-one-data-quality/`](artifact-one-data-quality/) | Ranks Katsina State's 34 LGAs by how untrustworthy their reported health data is, and says exactly why -- reporting attrition, biologically impossible coverage values -- against live-pulled MSDAT and GRID3 data. Not a health-metrics dashboard: it never displays or ranks a health outcome, only the reliability of the reporting itself. | Built, verified, running |
| `artifact-two-*/` | Targets a second, distinct operational bottleneck (human-resource maldistribution, referral-network fragmentation, or access-vs-utilization mismatch -- final pick and directory name TBD) and models the physical intervention it justifies. | Spec/build in progress |

Each artifact directory is self-contained: its own README with a Quickstart, its own
`docker-compose.yml`, its own dependency list, its own `.gitignore` for its own build artifacts.
Cloning this repo and following either artifact's own README is enough to run it end-to-end; the
two don't share infrastructure or a Docker Compose stack.

## Why one repo

Both artifacts are part of the same application and the same underlying thesis, and a reviewer
should be able to open one link, not chase down two. Nothing in either artifact's data, code, or
infrastructure is shared or coupled -- they live side by side because they're read together, not
because they run together.
