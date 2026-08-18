"""Runtime discovery of MSDAT's public frontend-auth key pair.

MSDAT's own web app authenticates every anonymous visitor with a static key
pair (`x-frontend-key-id` / `x-frontend-auth`) that ships in plaintext inside
MSDAT's own publicly-served JS bundle (see README.md, "MSDAT investigation").
That pair is intentionally NOT hardcoded anywhere in this repo. It is
extracted here, at run time, the same way a browser loading the public
dashboard effectively obtains it -- a plain HTTP fetch of the homepage to
find the current JS bundle URL(s), a plain HTTP fetch of that bundle, and a
regex against its text. No headless browser is needed at run time; a browser
was only used during the original investigation to confirm where the value
came from in the first place.

Extracting it this way rather than pinning it as a constant means: (a)
nothing that looks like a credential ever sits in tracked source or git
history, and (b) if MSDAT ever rotates the value on a redeploy, this pipeline
keeps working without a code change, instead of failing on a stale literal.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests

from ingestion.config import MSDAT_HOMEPAGE_URL
from ingestion.models import MsdatFrontendKey

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30

# Matches both `src="/js/app.<hash>.js"` and `href="/js/app.<hash>.js"`
# (MSDAT's homepage references its bundles both ways -- <link rel=preload>
# and <script src=...>).
_SCRIPT_URL_RE = re.compile(r'(?:src|href)="(/js/[^"]+\.js)"')
_KEY_ID_RE = re.compile(r'VUE_APP_FRONTEND_KEY_ID"?\s*:\s*"([^"]+)"')
_AUTH_RE = re.compile(r'VUE_APP_FRONTEND_AUTH"?\s*:\s*"([^"]+)"')

# Optional disk cache so repeated invocations during a single working session
# don't re-download MSDAT's ~1-5MB JS bundle every time. Lives under
# data_snapshots/, which is entirely gitignored -- this file is never
# tracked, regardless of what it contains.
_CACHE_PATH = Path(__file__).resolve().parent.parent / "data_snapshots" / "_msdat_key_cache.json"
_CACHE_TTL_SECONDS = 3600

_memory_cache: MsdatFrontendKey | None = None


def _candidate_script_urls(session: requests.Session, homepage_url: str) -> list[str]:
    last_error: Exception | None = None
    resp = None
    for attempt in range(1, 3 + 1):
        try:
            resp = session.get(homepage_url, timeout=_REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as exc:
            last_error = exc
            resp = None
            time.sleep(2.0 * attempt)
    if resp is None:
        raise RuntimeError(
            f"Could not fetch MSDAT homepage at {homepage_url} after 3 attempts: {last_error}"
        )
    paths = list(dict.fromkeys(_SCRIPT_URL_RE.findall(resp.text)))  # de-dupe, keep order
    # The key pair has always been found in the main "app.<hash>.js" bundle
    # (confirmed during the original investigation); try it first, but keep
    # every other referenced bundle as a fallback in case a future MSDAT
    # deploy moves it into a different chunk.
    paths.sort(key=lambda p: 0 if "/js/app." in p else 1)
    origin = homepage_url.rstrip("/")
    return [f"{origin}{p}" for p in paths]


def _extract_from_bundle_text(text: str) -> MsdatFrontendKey | None:
    key_match = _KEY_ID_RE.search(text)
    auth_match = _AUTH_RE.search(text)
    if key_match and auth_match:
        return MsdatFrontendKey(key_id=key_match.group(1), auth=auth_match.group(1))
    return None


def _read_disk_cache() -> MsdatFrontendKey | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        if time.time() - float(payload["cached_at"]) > _CACHE_TTL_SECONDS:
            return None
        return MsdatFrontendKey(key_id=payload["key_id"], auth=payload["auth"])
    except (json.JSONDecodeError, KeyError, OSError, ValueError):
        return None


def _write_disk_cache(key: MsdatFrontendKey) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps({"key_id": key.key_id, "auth": key.auth, "cached_at": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        logger.debug("Could not write MSDAT frontend-key disk cache (non-fatal).", exc_info=True)


def discover_frontend_key(
    *, homepage_url: str = MSDAT_HOMEPAGE_URL, use_disk_cache: bool = True
) -> MsdatFrontendKey:
    """Extract MSDAT's current public frontend key pair from its own live JS.

    Cached in-memory for the lifetime of the process. Set
    `MSDAT_KEY_DISK_CACHE=0` to disable the optional on-disk cache described
    in this module's docstring.
    """
    global _memory_cache
    if _memory_cache is not None:
        return _memory_cache

    if use_disk_cache and os.environ.get("MSDAT_KEY_DISK_CACHE", "1") != "0":
        cached = _read_disk_cache()
        if cached is not None:
            logger.info("Using cached MSDAT frontend key (not re-fetching the JS bundle).")
            _memory_cache = cached
            return cached

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (compatible; sand-fde-katsina-pipeline/1.0)"}
    )

    script_urls = _candidate_script_urls(session, homepage_url)
    if not script_urls:
        raise RuntimeError(
            f"Could not find any /js/*.js bundle referenced from {homepage_url} -- "
            "MSDAT's page structure may have changed since this pipeline was built. "
            "See README.md 'MSDAT investigation' for the original discovery steps."
        )

    for url in script_urls:
        try:
            resp = session.get(url, timeout=_REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "Could not fetch %s while looking for MSDAT's frontend key: %s", url, exc
            )
            continue
        found = _extract_from_bundle_text(resp.text)
        if found is not None:
            logger.info("Extracted MSDAT's frontend key pair from %s.", url)
            _memory_cache = found
            if use_disk_cache:
                _write_disk_cache(found)
            return found

    raise RuntimeError(
        "Could not locate VUE_APP_FRONTEND_KEY_ID / VUE_APP_FRONTEND_AUTH in any of "
        f"MSDAT's {len(script_urls)} referenced JS bundles -- MSDAT's build or auth "
        "scheme may have changed. See README.md 'MSDAT investigation' for how this "
        "was found originally, and update the extraction pattern accordingly."
    )
