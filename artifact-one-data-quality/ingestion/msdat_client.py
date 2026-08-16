"""A thin, honest HTTP client for MSDAT's public data API.

Nothing here talks to a browser or requires Ministry credentials: it replicates
exactly the two HTTP calls MSDAT's own public web app makes on every page load
-- the frontend key those calls use is extracted at run time from MSDAT's own
live JS (see msdat_key_discovery.py), never hardcoded.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import requests

from ingestion.config import MSDAT_API_BASE
from ingestion.msdat_key_discovery import discover_frontend_key

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2.0


class MsdatApiError(RuntimeError):
    """Raised when MSDAT's API returns something this client cannot handle."""


class MsdatClient:
    """Minimal client: fetch a frontend token, then call read-only endpoints."""

    def __init__(self, base_url: str = MSDAT_API_BASE) -> None:
        self._base_url = base_url
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "sand-fde-katsina-pipeline/1.0"})
        self._token: str | None = None
        self._token_fetched_at: float = 0.0
        self._token_ttl_seconds = 800  # MSDAT issues 900s tokens; refresh early.

    def _ensure_token(self) -> str:
        now = time.monotonic()
        if self._token is not None and (now - self._token_fetched_at) < self._token_ttl_seconds:
            return self._token
        frontend_key = discover_frontend_key()
        resp = self._session.post(
            f"{self._base_url}auth/frontend-token/",
            headers={
                "x-frontend-key-id": frontend_key.key_id,
                "x-frontend-auth": frontend_key.auth,
                "content-type": "application/json",
                "accept": "application/json",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            raise MsdatApiError(
                f"Failed to obtain MSDAT frontend token: HTTP {resp.status_code} {resp.text[:300]}"
            )
        token = resp.json().get("token")
        if not token:
            raise MsdatApiError("MSDAT frontend-token response had no 'token' field.")
        self._token = str(token)
        self._token_fetched_at = now
        logger.info("Obtained a fresh MSDAT frontend token (valid ~15 minutes).")
        return self._token

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            token = self._ensure_token()
            try:
                resp = self._session.get(
                    f"{self._base_url}{path}",
                    headers={"x-frontend-jwt": f"Token {token}", "accept": "application/json"},
                    params=params,
                    timeout=_REQUEST_TIMEOUT_SECONDS,
                )
            except requests.exceptions.RequestException as exc:
                # Connection-level failures (dropped connection, timeout, DNS
                # blip) never reach the status-code checks below at all --
                # without this, a single transient network hiccup against a
                # live external API killed the whole fetch with zero retries,
                # which is exactly the kind of flakiness a paced, polite
                # anonymous client against a real government platform should
                # expect and absorb rather than propagate.
                last_error = MsdatApiError(f"Connection error calling MSDAT on {path}: {exc}")
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
                continue
            if resp.status_code == 401:
                # Token expired mid-run; force a refresh and retry.
                self._token = None
                last_error = MsdatApiError(f"401 from MSDAT on {path}: {resp.text[:200]}")
                time.sleep(_RETRY_BACKOFF_SECONDS)
                continue
            if resp.status_code != 200:
                last_error = MsdatApiError(
                    f"HTTP {resp.status_code} from MSDAT on {path}: {resp.text[:200]}"
                )
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
                continue
            result: dict[str, Any] = resp.json()
            return result
        raise MsdatApiError(str(last_error))

    def fetch_locations(self) -> list[dict[str, Any]]:
        """All locations MSDAT knows about (country/state/LGA/senatorial-district)."""
        data = self._get("location/", params={"size": 1500})
        results: list[dict[str, Any]] = data["results"]
        return results

    def fetch_indicator_values(
        self, *, indicator_id: int, datasource_id: int, location_id: int
    ) -> list[dict[str, Any]]:
        """All periods MSDAT has for one indicator/datasource/location triple."""
        data = self._get(
            "data/",
            params={
                "indicator": indicator_id,
                "datasource": datasource_id,
                "location": location_id,
                "size": 100,
            },
        )
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    def close(self) -> None:
        self._session.close()


def now_utc() -> datetime:
    return datetime.now(UTC)
