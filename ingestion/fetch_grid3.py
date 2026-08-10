"""Live-pull GRID3/WorldPop LGA-level population estimates for Katsina State.

Downloads the official admin-level summary bundle (see config.py for the exact
dataset and URL), extracts the LGA (admin-level-3) CSV, filters to Katsina, and
writes the result to `raw.grid3_lga_population` plus a dated CSV snapshot.

The zip is cached under data_snapshots/_grid3_cache/ after the first download
(it is a ~2.7MB static release artifact, not a live-updating feed -- re-downloading
it on every run would be pointless network load for no new information). Delete
that cache directory to force a fresh download.
"""

from __future__ import annotations

import csv as csv_module
import io
import logging
import sys
import zipfile
from pathlib import Path

import requests

from ingestion.config import GRID3_ADMIN_ZIP_URL, GRID3_DATASET_LABEL
from ingestion.db import ensure_raw_schema, get_connection
from ingestion.models import Grid3LgaPopulation
from ingestion.msdat_client import now_utc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data_snapshots"
CACHE_DIR = SNAPSHOT_DIR / "_grid3_cache"
CACHE_ZIP_PATH = CACHE_DIR / "NGA_population_v1_2_admin.zip"
LGA_CSV_NAME = "NGA_population_v1_2_admin/NGA_population_v1_2_admin_level3.csv"


def _download_zip() -> bytes:
    if CACHE_ZIP_PATH.exists():
        logger.info("Using cached GRID3 admin zip at %s.", CACHE_ZIP_PATH)
        return CACHE_ZIP_PATH.read_bytes()

    logger.info("Downloading GRID3 admin-level population bundle from %s.", GRID3_ADMIN_ZIP_URL)
    resp = requests.get(GRID3_ADMIN_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    resp.raise_for_status()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_ZIP_PATH.write_bytes(resp.content)
    return resp.content


def fetch_katsina_population() -> list[Grid3LgaPopulation]:
    zip_bytes = _download_zip()
    fetched_at = now_utc()
    records: list[Grid3LgaPopulation] = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf, zf.open(LGA_CSV_NAME) as f:
        text_stream = io.TextIOWrapper(f, encoding="utf-8")
        reader = csv_module.DictReader(text_stream)
        for row in reader:
            if row["state"].strip() != "Katsina":
                continue
            records.append(
                Grid3LgaPopulation(
                    state=row["state"].strip(),
                    lga_name=row["local"].strip(),
                    population_mean=float(row["mean"]),
                    population_q025=float(row["q025"]),
                    population_q975=float(row["q975"]),
                    source_label=GRID3_DATASET_LABEL,
                    fetched_at=fetched_at,
                )
            )

    if len(records) != 34:
        logger.warning(
            "Expected 34 Katsina LGAs from GRID3, found %d -- check the source file "
            "for a schema change.",
            len(records),
        )
    return records


def write_snapshot_csv(records: list[Grid3LgaPopulation]) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"grid3_katsina_lga_population_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv_module.writer(f)
        writer.writerow(
            ["state", "lga_name", "population_mean", "population_q025", "population_q975",
             "source_label", "fetched_at"]
        )
        for r in records:
            writer.writerow(
                [r.state, r.lga_name, r.population_mean, r.population_q025,
                 r.population_q975, r.source_label, r.fetched_at.isoformat()]
            )
    return path


def write_to_postgres(records: list[Grid3LgaPopulation]) -> None:
    ensure_raw_schema()
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
                INSERT INTO raw.grid3_lga_population (
                    state, lga_name, population_mean, population_q025,
                    population_q975, source_label, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (lga_name, fetched_at) DO NOTHING
                """,
            [
                (r.state, r.lga_name, r.population_mean, r.population_q025,
                 r.population_q975, r.source_label, r.fetched_at)
                for r in records
            ],
        )


def main() -> int:
    records = fetch_katsina_population()
    if not records:
        logger.error("No GRID3 records found for Katsina -- aborting without writing anything.")
        return 1
    snapshot_path = write_snapshot_csv(records)
    write_to_postgres(records)
    logger.info(
        "Done. %d Katsina LGA population records written to Postgres and snapshotted to %s.",
        len(records),
        snapshot_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
