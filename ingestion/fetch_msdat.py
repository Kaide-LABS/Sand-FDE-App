"""Live-pull MSDAT NHMIS (Facility-based) indicator values for every Katsina LGA.

Run directly (`python -m ingestion.fetch_msdat`) or as an Airflow task. Writes:
  1. `raw.msdat_indicator_values` in Postgres (the pipeline's source of truth).
  2. A dated CSV snapshot under data_snapshots/ (for auditability -- a stranger
     re-running this later will get MSDAT's latest numbers, which may differ
     from the snapshot checked in at build time; that is expected of a live
     pull, not a bug).
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from pathlib import Path

from ingestion.config import (
    KATSINA_LGAS,
    MAX_YEAR,
    MIN_YEAR,
    NHMIS_ANNUAL_DATASOURCE_ID,
    REPORTING_BASKET_INDICATORS,
)
from ingestion.db import ensure_raw_schema, get_connection
from ingestion.models import MsdatIndicatorValue
from ingestion.msdat_client import MsdatApiError, MsdatClient, now_utc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REQUEST_PACING_SECONDS = 0.15  # be a polite anonymous client, not a hammer
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data_snapshots"


def _parse_period_to_year(period: str) -> int | None:
    period = period.strip()
    if period.isdigit() and len(period) == 4:
        return int(period)
    return None


def fetch_all() -> list[MsdatIndicatorValue]:
    client = MsdatClient()
    records: list[MsdatIndicatorValue] = []
    total_pairs = len(KATSINA_LGAS) * len(REPORTING_BASKET_INDICATORS)
    done = 0

    for location_id, lga_name in KATSINA_LGAS:
        for indicator_id, indicator_name in REPORTING_BASKET_INDICATORS:
            done += 1
            try:
                raw_rows = client.fetch_indicator_values(
                    indicator_id=indicator_id,
                    datasource_id=NHMIS_ANNUAL_DATASOURCE_ID,
                    location_id=location_id,
                )
            except MsdatApiError as exc:
                logger.warning(
                    "Skipping %s / indicator %s after repeated failures: %s",
                    lga_name,
                    indicator_id,
                    exc,
                )
                time.sleep(_REQUEST_PACING_SECONDS)
                continue

            fetched_at = now_utc()
            for row in raw_rows:
                year = _parse_period_to_year(row["period"])
                if year is None or not (MIN_YEAR <= year <= MAX_YEAR):
                    continue
                records.append(
                    MsdatIndicatorValue(
                        record_id=row["id"],
                        indicator_id=indicator_id,
                        indicator_name=indicator_name,
                        datasource_id=NHMIS_ANNUAL_DATASOURCE_ID,
                        location_id=location_id,
                        lga_name=lga_name,
                        period=row["period"],
                        year=year,
                        value=float(row["value"]),
                        msdat_updated_at=row["updated_at"],
                        fetched_at=fetched_at,
                    )
                )
            if done % 50 == 0 or done == total_pairs:
                logger.info("Fetched %d/%d LGA-indicator pairs from MSDAT.", done, total_pairs)
            time.sleep(_REQUEST_PACING_SECONDS)

    client.close()
    return records


def write_snapshot_csv(records: list[MsdatIndicatorValue]) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"msdat_katsina_nhmis_annual_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "record_id",
                "indicator_id",
                "indicator_name",
                "datasource_id",
                "location_id",
                "lga_name",
                "period",
                "year",
                "value",
                "msdat_updated_at",
                "fetched_at",
            ]
        )
        for r in records:
            writer.writerow(
                [
                    r.record_id,
                    r.indicator_id,
                    r.indicator_name,
                    r.datasource_id,
                    r.location_id,
                    r.lga_name,
                    r.period,
                    r.year,
                    r.value,
                    r.msdat_updated_at.isoformat(),
                    r.fetched_at.isoformat(),
                ]
            )
    return path


def write_to_postgres(records: list[MsdatIndicatorValue]) -> None:
    ensure_raw_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO raw.msdat_indicator_values (
                    record_id, indicator_id, indicator_name, datasource_id,
                    location_id, lga_name, period, year, value,
                    msdat_updated_at, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (record_id, fetched_at) DO NOTHING
                """,
                [
                    (
                        r.record_id,
                        r.indicator_id,
                        r.indicator_name,
                        r.datasource_id,
                        r.location_id,
                        r.lga_name,
                        r.period,
                        r.year,
                        r.value,
                        r.msdat_updated_at,
                        r.fetched_at,
                    )
                    for r in records
                ],
            )


def main() -> int:
    logger.info("Starting live MSDAT pull for Katsina State (%d LGAs).", len(KATSINA_LGAS))
    records = fetch_all()
    if not records:
        logger.error("No records fetched from MSDAT -- aborting without writing anything.")
        return 1
    snapshot_path = write_snapshot_csv(records)
    write_to_postgres(records)
    logger.info(
        "Done. %d records written to Postgres and snapshotted to %s.",
        len(records),
        snapshot_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
