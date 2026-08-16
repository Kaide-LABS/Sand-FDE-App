"""Ingestion layer: loads the five checked-in, cited CSV extractions of the
Borno State PHC Workers Baseline Mapping Exercise PDF (reference/borno_phc_baseline.pdf)
into Postgres' `raw` schema. No live API, no scrape -- see ULTIMATE_PRD.md Sec.3.1.
"""

from __future__ import annotations
