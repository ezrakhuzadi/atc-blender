import json
from dataclasses import dataclass
from os import environ as env
from typing import Any
from urllib.parse import urljoin

import requests
from loguru import logger

from geo_fence_operations.url_safety import validate_public_url


DEFAULT_TIMEOUT_S = float(env.get("HTTP_TIMEOUT_S", "10"))
DEFAULT_MAX_REDIRECTS = int(env.get("HTTP_MAX_REDIRECTS", "3"))
DEFAULT_MAX_DOWNLOAD_BYTES = int(env.get("HTTP_MAX_DOWNLOAD_BYTES", str(1024 * 1024)))  # 1MB


@dataclass(frozen=True)
class DownloadSettings:
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_redirects: int = DEFAULT_MAX_REDIRECTS
    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES
    allow_http: bool = False
    require_https: bool = True


def _is_json_content_type(content_type: str) -> bool:
    lowered = (content_type or "").lower()
    # JWKS often uses application/jwk-set+json; allow anything that indicates JSON.
    return "json" in lowered


def fetch_json_url(url: str, *, settings: DownloadSettings, session: requests.Session | None = None) -> dict[str, Any] | None:
    """
    Fetch JSON from a URL with SSRF protections, redirect validation, timeouts, and a size limit.
    Returns parsed JSON dict on success, otherwise None.
    """
    ok, reason = validate_public_url(url, allow_http=settings.allow_http, require_https=settings.require_https)
    if not ok:
        logger.warning("Blocked URL {} ({})", url, reason)
        return None

    s = session or requests.Session()
    current_url = url

    for hop in range(settings.max_redirects + 1):
        try:
            response = s.get(
                current_url,
                timeout=settings.timeout_s,
                allow_redirects=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("HTTP fetch failed for {}: {}", current_url, exc)
            return None

        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                logger.warning("Redirect without Location for {}", current_url)
                return None
            if hop >= settings.max_redirects:
                logger.warning("Too many redirects fetching {}", url)
                return None
            next_url = urljoin(current_url, location)
            ok, reason = validate_public_url(next_url, allow_http=settings.allow_http, require_https=settings.require_https)
            if not ok:
                logger.warning("Blocked redirect URL {} ({})", next_url, reason)
                return None
            current_url = next_url
            continue

        if response.status_code != 200:
            logger.warning("Non-200 response fetching {}: {}", current_url, response.status_code)
            return None

        content_type = response.headers.get("Content-Type", "")
        if content_type and not _is_json_content_type(content_type):
            logger.warning("Non-JSON Content-Type fetching {}: {}", current_url, content_type)
            return None

        try:
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total > settings.max_download_bytes:
                    logger.warning("Response too large fetching {}", current_url)
                    return None
            raw = b"".join(chunks).decode("utf-8", errors="replace")
            parsed = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse JSON from {}: {}", current_url, exc)
            return None

        if not isinstance(parsed, dict):
            logger.warning("Expected JSON object from {}", current_url)
            return None

        return parsed

    return None
