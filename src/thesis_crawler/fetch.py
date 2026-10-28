"""Polite HTTP fetching: robots.txt, per-host delay, retries and an on-disk cache.

`file://` URLs are read straight from disk, which is how the test fixtures and
offline runs work.
"""

from __future__ import annotations

import hashlib
import logging
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import httpx

log = logging.getLogger(__name__)

USER_AGENT = (
    "thesis-crawler/0.1 (personal master thesis search; "
    "+https://github.com/leokarsikas/Master-Thesis-Crawler)"
)


class FetchError(Exception):
    pass


class Fetcher:
    def __init__(
        self,
        cache_dir: Path | None = Path("cache"),
        cache_ttl: float = 6 * 3600,
        delay: float = 1.0,
        timeout: float = 20.0,
        retries: int = 2,
        respect_robots: bool = True,
    ):
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.delay = delay
        self.retries = retries
        self.respect_robots = respect_robots
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en,sv;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get(self, url: str, params: dict | None = None) -> str:
        parts = urlsplit(url)
        if parts.scheme == "file":
            path = Path(url2pathname(parts.path))
            try:
                return path.read_text(encoding="utf-8")
            except OSError as e:
                raise FetchError(f"{url}: {e}") from e

        full_url = str(httpx.URL(url, params=params)) if params else url
        cached = self._read_cache(full_url)
        if cached is not None:
            return cached

        if not self._allowed(full_url):
            raise FetchError(f"{full_url}: disallowed by robots.txt")

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._wait_for_host(parts.netloc)
            try:
                resp = self._client.get(full_url)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    last_error = FetchError(f"{full_url}: HTTP {resp.status_code}")
                    time.sleep(2 ** attempt * 2)
                    continue
                resp.raise_for_status()
                self._write_cache(full_url, resp.text)
                return resp.text
            except httpx.HTTPStatusError as e:
                raise FetchError(f"{full_url}: HTTP {e.response.status_code}") from e
            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.retries:
                    time.sleep(2 ** attempt * 2)
        raise FetchError(f"{full_url}: {last_error}")

    def _wait_for_host(self, host: str) -> None:
        elapsed = time.monotonic() - self._last_hit.get(host, 0.0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_hit[host] = time.monotonic()

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            parser: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
            try:
                resp = self._client.get(f"{base}/robots.txt")
                if resp.status_code >= 400:
                    parser = None  # no robots.txt: everything allowed
                else:
                    parser.parse(resp.text.splitlines())
            except httpx.HTTPError:
                parser = None
            self._robots[base] = parser
        parser = self._robots[base]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".html")

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        if path and path.exists() and time.time() - path.stat().st_mtime < self.cache_ttl:
            return path.read_text(encoding="utf-8")
        return None

    def _write_cache(self, url: str, body: str) -> None:
        path = self._cache_path(url)
        if path:
            path.write_text(body, encoding="utf-8")
