"""Typed records for every value this pipeline ingests.

Every model uses `model_config = ConfigDict(extra="forbid")` so that a change in
an upstream API's response shape (an added or renamed field) fails loudly at
ingestion time instead of silently passing an unvalidated dict deeper into the
pipeline.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MsdatIndicatorValue(BaseModel):
    """One row from MSDAT's `/api/data/` endpoint for the NHMIS-annual
    datasource, restricted to a single Katsina LGA and a single indicator.
    """

    model_config = ConfigDict(extra="forbid")

    record_id: int = Field(description="MSDAT's own primary key for this data point.")
    indicator_id: int
    indicator_name: str
    datasource_id: int
    location_id: int
    lga_name: str
    period: str = Field(description='MSDAT period label, e.g. "2024".')
    year: int
    value: float
    msdat_updated_at: datetime = Field(
        description="MSDAT's own `updated_at` timestamp for this record -- when "
        "MSDAT last (re)computed this figure, not when we fetched it."
    )
    fetched_at: datetime = Field(description="When this pipeline run pulled the record.")


class Grid3LgaPopulation(BaseModel):
    """One row from the GRID3/WorldPop bottom-up gridded population estimates
    (v1.2) admin-level-3 (LGA) summary table, restricted to Katsina State.
    """

    model_config = ConfigDict(extra="forbid")

    state: str
    lga_name: str
    population_mean: float = Field(description="Point estimate (posterior mean).")
    population_q025: float = Field(description="2.5th percentile of the estimate.")
    population_q975: float = Field(description="97.5th percentile of the estimate.")
    source_label: str
    fetched_at: datetime


class MsdatLocation(BaseModel):
    """One row from MSDAT's `/api/location/` endpoint."""

    model_config = ConfigDict(extra="forbid")

    location_id: int
    name: str
    parent_id: int | None
    level: int
