"""Typed records for the optimizer's input, decision output, and final
result. All use `model_config = ConfigDict(extra="forbid")`, matching
Artifact One's convention exactly.

# Implements PHASE_1_SPEC.md Sec.3 (optimizer/models.py).
"""

from __future__ import annotations

from typing import Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field

from ingestion.config import PHASE_1_CADRES

__all__ = [
    "PHASE_1_CADRES",
    "LgaAllocation",
    "MartReallocationInputRow",
    "OptimizationResult",
    "TransferProposal",
    "as_cadre",
]

# `Literal[]` needs its members written as literal string expressions for
# mypy --strict to type-check `TransferProposal.cadre` (a `Literal[SOME_TUPLE_VAR]`
# spelling, as PHASE_1_SPEC.md Sec.3's illustrative code block shows, only
# works at runtime -- mypy rejects a variable there). To avoid that runtime
# spelling while still guaranteeing this can never silently drift from
# ingestion.config.PHASE_1_CADRES (the single source of truth for the
# Phase-1 cadre scope -- see that module), the four cadre names are written
# out literally here AND checked for exact equality against
# `PHASE_1_CADRES` at import time below. Editing one without the other now
# fails loudly on the very first import, the same "sync safeguard" discipline
# already used elsewhere in this two-artifact application.
_CadreLiteral = Literal[
    "community_health_officer",
    "community_health_extension_worker",
    "junior_community_health_extension_worker",
    "nurse_midwife",
]

if get_args(_CadreLiteral) != PHASE_1_CADRES:
    raise AssertionError(
        "optimizer.models._CadreLiteral has drifted from ingestion.config.PHASE_1_CADRES -- "
        "these two must name the exact same four cadres, in the same order. "
        f"_CadreLiteral={get_args(_CadreLiteral)!r} PHASE_1_CADRES={PHASE_1_CADRES!r}"
    )


def as_cadre(value: str) -> _CadreLiteral:
    """Validate `value` is one of the four Phase-1 cadre names and return it
    typed as the `Literal` `TransferProposal.cadre` expects.

    Callers decoding `optimizer.solve.SolveResult.x_values` (keyed by plain
    `tuple[str, str, str]`, since `optimizer/formulate.py`'s variable index
    is not itself Literal-typed) go through this rather than an unchecked
    `cast`, so a value that is not actually one of the four cadres fails
    loudly here instead of silently passing mypy's static check while being
    wrong at runtime. This should be structurally impossible given
    optimizer/formulate.py only ever builds its variable index from
    `PHASE_1_CADRES` -- a failure here means a bug upstream, not a data
    problem.
    """
    if value not in PHASE_1_CADRES:
        raise ValueError(f"{value!r} is not one of the four Phase-1 cadres: {PHASE_1_CADRES!r}.")
    return cast(_CadreLiteral, value)


class MartReallocationInputRow(BaseModel):
    """One row read back from `dbt_marts.mart_reallocation_input` --
    validated on read so a schema drift between the dbt mart and what
    formulate.py expects fails loudly instead of producing a wrong MILP.
    Not part of PHASE_1_SPEC.md Sec.3's illustrative schema block; added as
    a defensive boundary-validation addition (see AUTONOMOUS CRITIQUE).
    """

    model_config = ConfigDict(extra="forbid")

    lga: str
    community_health_officer: int = Field(ge=0)
    community_health_extension_worker: int = Field(ge=0)
    junior_community_health_extension_worker: int = Field(ge=0)
    nurse_midwife: int = Field(ge=0)
    grand_total: int = Field(ge=0)
    population_proxy: float = Field(gt=0)
    ratio: float = Field(ge=0)


class TransferProposal(BaseModel):
    """One proposed worker transfer: `headcount` workers of `cadre` moved
    from `from_lga` to `to_lga`.
    """

    model_config = ConfigDict(extra="forbid")

    cadre: _CadreLiteral
    from_lga: str
    to_lga: str
    headcount: int = Field(gt=0)


class LgaAllocation(BaseModel):
    """Before/after headcount and ratio for one LGA. All 26 covered LGAs are
    always represented here, never filtered to only the ones that changed --
    so the coverage disclosure (ULTIMATE_PRD.md Sec.11's Guzamala row) has a
    complete list to render against.
    """

    model_config = ConfigDict(extra="forbid")

    lga: str
    population_proxy: float = Field(
        description="Derived from PDF Fig. 1 & Fig. 2, not directly reported (ULTIMATE_PRD.md Sec.3.2)."
    )
    grand_total_before: int
    grand_total_after: int
    ratio_before: float
    ratio_after: float


class OptimizationResult(BaseModel):
    """The optimizer's full output: every proposed transfer, every LGA's
    before/after allocation, the state-wide before/after ratio variance, and
    the solver's own status -- surfaced, never silently treated as success
    (ULTIMATE_PRD.md Sec.4, PHASE_1_SPEC.md Sec.6 step 5).
    """

    model_config = ConfigDict(extra="forbid")

    transfers: list[TransferProposal]
    allocations: list[LgaAllocation]
    variance_before: float
    variance_after: float
    solver_status: str
