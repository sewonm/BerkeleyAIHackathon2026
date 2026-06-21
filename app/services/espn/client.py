"""
Thin, stubbable HTTP client for ESPN's free JSON APIs (Phase 2).

Why a wrapper:
- ESPN APIs are undocumented -> every call must degrade gracefully (return None,
  never raise) so a transient failure or shape change drops one chunk, not the
  whole bundle.
- Determinism + offline demo: the client can read recorded **fixtures** (instead
  of the network) so tests are byte-stable and the demo survives the network
  being off. It can also **record** live responses into a fixtures dir.
- Disk cache: optional on-disk cache so repeated runs are fast and stable.

Resolution order for ``get_json(url, params)``:
    1. fixtures_dir  (read-only golden responses; if set and present -> use it)
    2. cache_dir     (read; if present and not expired -> use it)
    3. network       (httpx if available, else urllib stdlib)
       -> on success, write to cache_dir and/or record_dir
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode, urlparse, parse_qsl

# Browser-like UA — ESPN's undocumented endpoints expect a normal client.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 10.0


def fixture_name(url: str, params: Optional[dict] = None) -> str:
    """Deterministic, filesystem-safe fixture filename for a URL + params.

    Folds any query string already on the URL together with ``params`` so a
    ``$ref`` URL (which carries its own query) and a (url, params) call collide
    iff they hit the same effective endpoint.

    e.g. ``site.api.espn.com/.../baseball/mlb/scoreboard`` ->
         ``site__apis-site-v2-sports-baseball-mlb-scoreboard.json``
    """
    parsed = urlparse(url)
    host = parsed.netloc.split(".")[0] or "host"  # 'site' or 'sports'
    path = parsed.path.strip("/").replace("/", "-")

    merged = dict(parse_qsl(parsed.query))
    if params:
        merged.update({str(k): str(v) for k, v in params.items()})
    query = ""
    if merged:
        query = "__" + "-".join(f"{k}_{v}" for k, v in sorted(merged.items()))

    raw = f"{host}__{path}{query}"
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", raw)
    return f"{safe[:180]}.json"


class ESPNClient:
    """Stubbable JSON-over-HTTP client. Never raises on fetch — returns None."""

    def __init__(
        self,
        *,
        fixtures_dir: Optional[str | Path] = None,
        cache_dir: Optional[str | Path] = None,
        record_dir: Optional[str | Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        cache_ttl: Optional[float] = None,
        offline: bool = False,
    ) -> None:
        """
        Args:
            fixtures_dir: read-only golden responses (highest priority). If set,
                a fixture miss returns None (no network) — perfect for tests.
                Defaults to env ``ESPN_FIXTURES_DIR``.
            cache_dir: read/write on-disk cache for live responses.
                Defaults to env ``ESPN_CACHE_DIR``.
            record_dir: when set, every live response is also written here as a
                fixture (used by the fixture-recording script).
            timeout: per-request timeout in seconds.
            user_agent: UA header.
            cache_ttl: seconds; cache entries older than this are ignored.
                None = cache never expires.
            offline: hard offline — never touch the network (fixtures/cache only).
                Defaults to truthy env ``ESPN_OFFLINE``.

        Explicit args always override the corresponding environment variable.
        """
        fixtures_dir = fixtures_dir or os.getenv("ESPN_FIXTURES_DIR") or None
        cache_dir = cache_dir or os.getenv("ESPN_CACHE_DIR") or None
        if not offline:
            offline = os.getenv("ESPN_OFFLINE", "").strip().lower() in {"1", "true", "yes"}

        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.record_dir = Path(record_dir) if record_dir else None
        self.timeout = timeout
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl
        self.offline = offline

        for d in (self.cache_dir, self.record_dir):
            if d is not None:
                d.mkdir(parents=True, exist_ok=True)

    # -- public ------------------------------------------------------------

    def get_json(self, url: str, params: Optional[dict] = None) -> Optional[Any]:
        """Fetch JSON. Returns the parsed body, or None on any failure/miss."""
        name = fixture_name(url, params)

        # 1) fixtures (read-only; a miss in fixtures mode means "no data")
        if self.fixtures_dir is not None:
            data = self._read_json(self.fixtures_dir / name)
            if data is not None:
                return data
            if self.offline:
                return None
            # fixtures set but missing + online -> fall through to network

        # 2) cache (read)
        if self.cache_dir is not None:
            cached = self._read_cache(self.cache_dir / name)
            if cached is not None:
                return cached

        # 3) network
        if self.offline:
            return None
        data = self._http_get_json(url, params)
        if data is None:
            return None

        # write-through to cache + record
        if self.cache_dir is not None:
            self._write_json(self.cache_dir / name, data)
        if self.record_dir is not None:
            self._write_json(self.record_dir / name, data)
        return data

    def get_ref(self, ref: Any, params: Optional[dict] = None) -> Optional[Any]:
        """Follow an ESPN core-API ``$ref`` (str or ``{"$ref": url}``)."""
        url = ref.get("$ref") if isinstance(ref, dict) else ref
        if not isinstance(url, str) or not url:
            return None
        # core API refs are sometimes http:// — normalize to https://
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        return self.get_json(url, params)

    # -- internals ---------------------------------------------------------

    def _http_get_json(self, url: str, params: Optional[dict]) -> Optional[Any]:
        """Real network GET. httpx if importable, else urllib. Never raises."""
        full = url
        if params:
            sep = "&" if urlparse(url).query else "?"
            full = f"{url}{sep}{urlencode(params)}"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}

        # Prefer httpx (sync); fall back to stdlib so the module works anywhere.
        try:
            import httpx  # type: ignore

            try:
                resp = httpx.get(
                    full, headers=headers, timeout=self.timeout, follow_redirects=True
                )
                if resp.status_code != 200:
                    return None
                return resp.json()
            except Exception:
                return None
        except ImportError:
            pass

        try:
            import urllib.request

            req = urllib.request.Request(full, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                if getattr(r, "status", 200) != 200:
                    return None
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _read_json(path: Path) -> Optional[Any]:
        try:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return None

    def _read_cache(self, path: Path) -> Optional[Any]:
        if not path.is_file():
            return None
        if self.cache_ttl is not None:
            try:
                if (time.time() - path.stat().st_mtime) > self.cache_ttl:
                    return None
            except OSError:
                return None
        return self._read_json(path)

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass  # cache/record writes are best-effort, never fatal
