"""Rate-limited requests.Session with retry logic and disk cache."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import (
    DEFAULT_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_TIMEOUT,
    DISK_CACHE_DIR,
)

logger = logging.getLogger(__name__)


class RateLimitedSession:
    """HTTP session with per-second rate limiting, retries, and optional disk cache."""

    def __init__(
        self,
        rate_limit: float = 2.0,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_RETRY_BACKOFF,
        timeout: int = DEFAULT_TIMEOUT,
        cache_name: str | None = None,
    ):
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.timeout = timeout
        self._last_request_time = 0.0

        self.session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": "VetOrgDirectory/1.0 (research; contact: vetorgdir@example.com)"
        })

        self._cache_dir = None
        if cache_name:
            self._cache_dir = DISK_CACHE_DIR / cache_name
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _wait_for_rate_limit(self):
        if self.min_interval > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _cache_key(self, method: str, url: str, **kwargs) -> str:
        key_data = f"{method}:{url}:{json.dumps(kwargs.get('params', {}), sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> dict | None:
        if not self._cache_dir:
            return None
        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text())
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _set_cached(self, cache_key: str, data: dict):
        if not self._cache_dir:
            return
        cache_file = self._cache_dir / f"{cache_key}.json"
        try:
            cache_file.write_text(json.dumps(data))
        except OSError:
            pass

    def get(self, url: str, use_cache: bool = True, **kwargs) -> requests.Response:
        if use_cache and self._cache_dir:
            key = self._cache_key("GET", url, **kwargs)
            cached = self._get_cached(key)
            if cached is not None:
                resp = requests.Response()
                resp.status_code = cached.get("status_code", 200)
                resp._content = cached.get("content", "").encode()
                resp.headers.update(cached.get("headers", {}))
                return resp

        self._wait_for_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.get(url, **kwargs)

        if use_cache and self._cache_dir and resp.status_code == 200:
            key = self._cache_key("GET", url, **kwargs)
            self._set_cached(key, {
                "status_code": resp.status_code,
                "content": resp.text,
                "headers": dict(resp.headers),
            })

        return resp

    def post(self, url: str, **kwargs) -> requests.Response:
        self._wait_for_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)

    def download_file(self, url: str, dest: Path, chunk_size: int = 8192) -> Path:
        """Download a file with streaming, returning the destination path."""
        self._wait_for_rate_limit()
        logger.info(f"Downloading {url} → {dest}")
        with self.session.get(url, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
        logger.info(f"Downloaded {dest} ({dest.stat().st_size:,} bytes)")
        return dest
