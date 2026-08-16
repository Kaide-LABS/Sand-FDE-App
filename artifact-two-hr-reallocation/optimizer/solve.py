"""Calls `scipy.optimize.milp` (HiGHS backend) and decodes the raw integer
solution. Any non-optimal status is surfaced as-is in `SolveResult` -- never
silently treated as success (PHASE_1_SPEC.md Sec.6 step 5); interpreting
that status is left to the caller (optimizer/main.py).

Solved with a disclosed, bounded MIP relative-gap tolerance and time limit
(`MIP_REL_GAP`, `TIME_LIMIT_SECONDS` below), not scipy's unbounded default.
This is a real, measured engineering finding, not a stylistic choice: on
the actual 26-LGA/4-cadre/2,626-variable Phase-1 problem, HiGHS's dual
bound on this formulation is weak (the objective depends only on each
LGA's *net* transfer per cadre, not on which specific destination LGA
receives it, so very many `x[i][j][c]` assignments are equally optimal --
confirmed by HiGHS's own "symmetry detection ... orbitope" log output) --
proving a strict 0%-gap global optimum was observed to take minutes without
converging, while a solution proven within 2% of the true optimum is found
in ~10-15s. Every acceptance criterion this artifact makes (zero-sum, the
per-cadre floor, and variance strictly improving -- ULTIMATE_PRD.md Sec.4,
PHASE_1_SPEC.md Sec.8) holds for *any* feasible solution the solver
returns, not only a proven-exact global optimum, so this tolerance does not
weaken what the artifact actually claims -- it is disclosed here and in
`_STATUS_LABELS` (`optimal_within_2pct_gap`, never bare `"optimal"`, so a
reader cannot mistake this for an unconditional zero-gap guarantee) rather
than silently assumed. See AUTONOMOUS CRITIQUE.

# Implements PHASE_1_SPEC.md Sec.6 step 5.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass

from scipy.optimize import milp

from optimizer.formulate import MilpProblem


def _flush_native_stdio() -> None:
    """Flushes the C runtime's own stdio buffers (not Python's `sys.stdout`).

    Needed because HiGHS's trace lines go through `printf`-family C stdio, which is
    fully buffered (not line-buffered) whenever fd 1 isn't a real terminal -- true for
    both `docker compose run` and pytest's capture. Those writes sit in libc's internal
    buffer and are only flushed by the C runtime's own atexit handler, which fires
    *after* `_suppress_native_stdout` has already restored the real fd 1 -- so
    redirecting the fd alone does not stop them, it only delays them to process exit
    (confirmed live: noise appeared, unsuppressed, immediately after the redirected
    block's own "done" marker printed -- CLONE_TEST_FINDINGS.md F3). Calling
    `fflush(NULL)` while fd 1 is still pointed at devnull drains that buffer into
    devnull for real, before the fd is restored.
    """
    libc = ctypes.cdll.msvcrt if sys.platform == "win32" else ctypes.CDLL(None)
    libc.fflush(None)


@contextlib.contextmanager
def _suppress_native_stdout() -> Iterator[None]:
    """Silences writes to OS file descriptor 1 (stdout) for the duration of the block.

    `contextlib.redirect_stdout` only rebinds Python's `sys.stdout` object -- it has no
    effect on a compiled C/C++ extension (HiGHS, scipy's MILP backend here) that writes
    directly to the process's real stdout file descriptor, which is exactly what leaks the
    solver's internal trace lines (e.g. its symmetry-detection orbitope log, see the module
    docstring) straight to the terminal regardless of any Python-level redirection
    (CLONE_TEST_FINDINGS.md F3 -- confirmed live: `contextlib.redirect_stdout` alone did not
    suppress this). Duplicating and restoring the real fd catches output a native extension
    writes below the Python layer, but is not by itself sufficient -- see
    `_flush_native_stdio`, called here before the fd is restored, for why.
    """
    stdout_fd = 1
    saved_fd = os.dup(stdout_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, stdout_fd)
        yield
    finally:
        _flush_native_stdio()
        os.dup2(saved_fd, stdout_fd)
        os.close(devnull_fd)
        os.close(saved_fd)


# Disclosed MIP relative-gap tolerance and wall-clock safety net -- see the
# module docstring above for the measured rationale. 2% was chosen as the
# tightest tolerance that reliably resolves in well under a minute on this
# problem's actual size; TIME_LIMIT_SECONDS is a generous backstop in case a
# future, larger LGA/cadre universe doesn't converge even to that gap, in
# which case the solver honestly reports `iteration_or_time_limit_reached`
# rather than silently returning a worse, unbounded-gap solution.
MIP_REL_GAP = 0.02
TIME_LIMIT_SECONDS = 120

# HiGHS-backed scipy.optimize.milp status codes
# (scipy.optimize.OptimizeResult.status, per the scipy.optimize.milp docs).
# Status 0 is deliberately NOT labeled bare "optimal" -- HiGHS reports 0
# when the solution is proven within MIP_REL_GAP of the true optimum, which
# is a disclosed near-optimality guarantee, not a claim of exact, zero-gap
# global optimality.
_STATUS_LABELS = {
    0: "optimal_within_2pct_gap",
    1: "iteration_or_time_limit_reached",
    2: "infeasible",
    3: "unbounded",
    4: "other",
}

# The one status label that means "the solver proved a usable solution" --
# callers (optimizer/main.py, viz/generate_report.py) compare against this
# set rather than hardcoding the string "optimal_within_2pct_gap" at each
# call site.
SUCCESS_STATUS_LABELS = frozenset({"optimal_within_2pct_gap"})

_INTEGER_TOLERANCE = 1e-6


@dataclass(frozen=True)
class SolveResult:
    """Raw MILP solution, decoded back into `(from_lga, to_lga, cadre)` /
    lga index space, plus the solver's own status.
    """

    status: int
    status_label: str
    message: str
    x_values: dict[tuple[str, str, str], int]  # only entries with headcount > 0
    d_values: dict[str, float]


def solve(problem: MilpProblem) -> SolveResult:
    """Solve the given MILP and decode its raw solution vector.

    Raises `ValueError` if the solver returns a value for an
    integer-constrained variable that is not (within floating-point
    tolerance) an integer -- this should be structurally impossible given
    `integrality=1` on every x variable, so a failure here indicates a
    solver or formulation bug, never a data problem.
    """
    # See _suppress_native_stdout's own docstring: HiGHS writes internal trace/debug lines
    # directly to the OS stdout file descriptor, independent of scipy's own `disp` option and
    # unreachable by `contextlib.redirect_stdout` -- CLONE_TEST_FINDINGS.md F3, confirmed live
    # on a fresh clone. `disp: False` is passed for the documented, scipy-level behavior it
    # does control; the fd-level suppression below is what actually guarantees no
    # solver-internal noise reaches the terminal.
    with _suppress_native_stdout():
        result = milp(
            c=problem.c,
            constraints=problem.constraint,
            integrality=problem.integrality,
            bounds=problem.bounds,
            options={
                "time_limit": TIME_LIMIT_SECONDS,
                "mip_rel_gap": MIP_REL_GAP,
                "disp": False,
            },
        )

    status_label = _STATUS_LABELS.get(int(result.status), f"unknown_status_{result.status}")

    x_values: dict[tuple[str, str, str], int] = {}
    d_values: dict[str, float] = {}

    if result.x is not None:
        for key, pos in problem.x_index.items():
            raw_value = float(result.x[pos])
            rounded = round(raw_value)
            if abs(raw_value - rounded) > _INTEGER_TOLERANCE:
                raise ValueError(
                    f"Solver returned a non-integer value {raw_value!r} for the "
                    f"integer-constrained variable x{key!r} -- this should be "
                    "structurally impossible given integrality=1 on all x "
                    "variables; treat as a solver or formulation bug, not data."
                )
            if rounded > 0:
                x_values[key] = int(rounded)

        for lga, pos in problem.d_index.items():
            d_values[lga] = float(result.x[pos])

    return SolveResult(
        status=int(result.status),
        status_label=status_label,
        message=str(result.message),
        x_values=x_values,
        d_values=d_values,
    )
