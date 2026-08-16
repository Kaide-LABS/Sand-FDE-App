"""The MILP-based worker reallocation optimizer (ULTIMATE_PRD.md Sec.4).

Deterministic-only correctness boundary (ULTIMATE_PRD.md Sec.6, this
project's PROJECT HARD BOUNDARY): no LLM API call anywhere in this
package's constraint construction, solve, or verification path, and no
hardcoded or estimated staffing/population figure standing in for one of
the five checked-in, cited CSVs in data/. Every number this package produces
is deterministic arithmetic or the output of `scipy.optimize.milp`.
"""

from __future__ import annotations
