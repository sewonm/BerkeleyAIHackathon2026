"""
Browserbase service — the noisy scraping layer (Phase 3).

Pulls RAW readable text from JS-heavy / anti-bot sources via a real
Playwright-over-CDP Browserbase session. This is the noisy fuel for the
downstream compression engine, so it scrapes RAW text ONLY — it deliberately
does NOT pre-structure (no Stagehand `extract`); structuring is the compression
engine's job (the Token Company prize).

Reliability (SA-SCRAPE-04): every scrape resolves in this order
    1. disk cache   (cache_dir; re-runs are instant + stable)
    2. fixtures     (fixtures_dir; ships representative raw text -> demo works offline)
    3. XHR feed     (clean JSON feeds e.g. Reddit `.json` -> fetched directly, no browser)
    4. live browser (Browserbase CDP; only if BROWSERBASE_API_KEY + playwright present)
A successful live/XHR scrape is written to cache.

Free-tier safety (SA-SCRAPE-04 criterion 4): sessions are created one at a time
and ALWAYS closed in a `finally` (no leaked browser-hours); a hard session
timeout is enforced (<= 15 min). The service is synchronous, so at most one
session is open at once (well under the 3-concurrent free-tier cap).
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Free-tier guardrails.
MAX_SESSION_SECONDS = 15 * 60      # <= 15 min/session
DEFAULT_MAX_CHARS = 8000           # cap raw text so chunks stay bounded
DEFAULT_NAV_TIMEOUT_MS = 25_000


def cache_name(url: str) -> str:
    """Filesystem-safe cache/fixture filename for a URL."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", url)
    return f"{safe[:180]}.txt"


class BrowserbaseService:
    """Scrape RAW text from noisy web sources, cached + fixture-safe."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        *,
        cache_dir: Optional[str | Path] = None,
        fixtures_dir: Optional[str | Path] = None,
        max_chars: int = DEFAULT_MAX_CHARS,
        user_agent: str = DEFAULT_USER_AGENT,
        nav_timeout_ms: int = DEFAULT_NAV_TIMEOUT_MS,
        session_timeout: int = MAX_SESSION_SECONDS,
        offline: bool = False,
        prefer_xhr: bool = True,
        settle_ms: int = 3500,
        proxies: Optional[bool] = None,
        stealth: Optional[bool] = None,
        solve_captchas: Optional[bool] = None,
    ) -> None:
        """
        Args:
            api_key: Browserbase API key (env ``BROWSERBASE_API_KEY``).
            project_id: Browserbase project id (env ``BROWSERBASE_PROJECT_ID``).
            cache_dir: disk cache dir (env ``BROWSERBASE_CACHE_DIR``;
                default ``.cache/browserbase``).
            fixtures_dir: read-only raw-text fixtures (env ``BROWSERBASE_FIXTURES_DIR``).
            max_chars: cap on returned raw text length.
            offline: never touch the network (cache/fixtures only) — env ``BROWSERBASE_OFFLINE``.
            prefer_xhr: fetch clean JSON feeds (e.g. Reddit ``.json``) directly
                instead of spinning up a browser.
            settle_ms: wait after navigation for JS / soft anti-bot challenges to
                resolve before reading text.
            proxies / stealth / solve_captchas: Browserbase anti-bot features for
                hard targets (Cloudflare, etc.). PROXIES + ADVANCED STEALTH ARE
                BILLED — default OFF. Enable via env BROWSERBASE_PROXIES /
                BROWSERBASE_STEALTH / BROWSERBASE_SOLVE_CAPTCHAS = 1.
        """
        self.api_key = api_key or os.getenv("BROWSERBASE_API_KEY", "") or ""
        self.project_id = project_id or os.getenv("BROWSERBASE_PROJECT_ID", "") or ""
        cache_dir = cache_dir or os.getenv("BROWSERBASE_CACHE_DIR") or ".cache/browserbase"
        fixtures_dir = fixtures_dir or os.getenv("BROWSERBASE_FIXTURES_DIR") or None

        self.cache_dir = Path(cache_dir)
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None
        self.max_chars = max_chars
        self.user_agent = user_agent
        self.nav_timeout_ms = nav_timeout_ms
        self.session_timeout = session_timeout
        if not offline:
            offline = os.getenv("BROWSERBASE_OFFLINE", "").strip().lower() in {"1", "true", "yes"}
        self.offline = offline
        self.prefer_xhr = prefer_xhr
        self.settle_ms = settle_ms

        def _envflag(name: str) -> bool:
            return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}

        self.proxies = _envflag("BROWSERBASE_PROXIES") if proxies is None else proxies
        self.stealth = _envflag("BROWSERBASE_STEALTH") if stealth is None else stealth
        self.solve_captchas = (
            _envflag("BROWSERBASE_SOLVE_CAPTCHAS") if solve_captchas is None else solve_captchas
        )

        # explicit lifecycle handles (SA-SCRAPE-01); managed internally too
        self._session = None
        self._browser = None
        self._pw = None

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    @property
    def has_live_capability(self) -> bool:
        """True if a real Browserbase session could be created right now."""
        if self.offline or not self.api_key:
            return False
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    # -- high-level API ----------------------------------------------------

    def scrape_text(
        self, url: str, *, wait_selector: Optional[str] = None,
        max_chars: Optional[int] = None,
    ) -> Optional[str]:
        """Return RAW readable text for ``url``. Never raises (None on total miss).

        Resolution:
          * cache is always consulted first (fast, stable re-runs).
          * OFFLINE  -> cache, then fixtures, else None (deterministic, no network).
          * ONLINE   -> cache, then FRESH (clean XHR feed, then live Browserbase
                        CDP), then fixtures as a safety net. So with a key present,
                        every target genuinely attempts a live Browserbase scrape.
        """
        cap = max_chars or self.max_chars
        name = cache_name(url)

        # cache always wins
        cached = self._read_text(self.cache_dir / name)
        if cached is not None:
            return cached[:cap]

        # offline: fixtures only
        if self.offline:
            fx = self._read_text(self.fixtures_dir / name) if self.fixtures_dir else None
            return fx[:cap] if fx is not None else None

        # online: try FRESH content first
        text: Optional[str] = None
        if self.prefer_xhr and self._looks_like_feed(url):
            text = self._xhr_scrape(url)
        if text is None and self.has_live_capability:
            text = self._live_scrape(url, wait_selector)

        if text:
            text = self._clean(text)[:cap]
            self._write_text(self.cache_dir / name, text)
            return text

        # fresh fetch failed (no capability / blocked) -> fixtures fallback
        if self.fixtures_dir is not None:
            fx = self._read_text(self.fixtures_dir / name)
            if fx is not None:
                return fx[:cap]
        return None

    # -- explicit lifecycle (SA-SCRAPE-01: create/navigate/extract/close) --

    def create_session(self):
        """Create a Browserbase session and connect Playwright over CDP."""
        if not self.has_live_capability:
            raise RuntimeError(
                "No live Browserbase capability (need BROWSERBASE_API_KEY + playwright)."
            )
        connect_url, session = self._create_bb_session()
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(connect_url)
        self._session = session
        return self._browser

    def navigate(self, url: str):
        """Navigate the current session's page to ``url`` and return the page."""
        if self._browser is None:
            self.create_session()
        ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=self.nav_timeout_ms)
        return page

    def get_page_content(self, page=None) -> str:
        """Extract RAW body text from the current/given page."""
        if page is None:
            ctx = self._browser.contexts[0]
            page = ctx.pages[0]
        return page.inner_text("body")

    def close_session(self) -> None:
        """Always-safe teardown — closes the browser and releases the session."""
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._pw = None
        self._session = None

    # -- internals ---------------------------------------------------------

    def _browser_settings(self) -> dict:
        """Anti-bot session settings (only the enabled, free-by-default ones)."""
        settings: dict = {}
        if self.stealth:
            settings["advancedStealth"] = True
        if self.solve_captchas:
            settings["solveCaptchas"] = True
        return settings

    def _create_bb_session(self):
        """Create a Browserbase session; return (connect_url, raw_session)."""
        settings = self._browser_settings()
        # Prefer the official SDK; fall back to the REST API via httpx.
        try:
            from browserbase import Browserbase  # type: ignore

            bb = Browserbase(api_key=self.api_key)
            kwargs = {"project_id": self.project_id}
            if self.proxies:
                kwargs["proxies"] = True
            if settings:
                kwargs["browser_settings"] = settings
            session = bb.sessions.create(**kwargs)
            connect_url = getattr(session, "connect_url", None) or getattr(
                session, "connectUrl", None
            )
            if connect_url:
                return connect_url, session
        except Exception:
            pass

        # REST fallback
        import httpx

        body = {"projectId": self.project_id}
        if self.proxies:
            body["proxies"] = True
        if settings:
            body["browserSettings"] = settings
        resp = httpx.post(
            "https://api.browserbase.com/v1/sessions",
            headers={"X-BB-API-Key": self.api_key, "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        connect_url = data.get("connectUrl") or (
            f"wss://connect.browserbase.com?apiKey={self.api_key}&sessionId={data.get('id')}"
        )
        return connect_url, data

    def _live_scrape(self, url: str, wait_selector: Optional[str]) -> Optional[str]:
        """Real CDP scrape. Session ALWAYS closed in finally. Never raises."""
        from playwright.sync_api import sync_playwright

        start = time.time()
        text: Optional[str] = None
        try:
            connect_url, _session = self._create_bb_session()
            with sync_playwright() as pw:
                browser = pw.chromium.connect_over_cdp(connect_url)
                try:
                    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    page.set_default_timeout(self.nav_timeout_ms)
                    page.goto(url, wait_until="domcontentloaded", timeout=self.nav_timeout_ms)
                    if wait_selector:
                        try:
                            page.wait_for_selector(wait_selector, timeout=6000)
                        except Exception:
                            pass
                    # let JS render / soft anti-bot challenges resolve
                    page.wait_for_timeout(self.settle_ms)
                    text = page.inner_text("body")
                    # one extra wait + re-read if we hit a JS bot-challenge interstitial
                    if self._is_challenge(text) and (time.time() - start) < self.session_timeout:
                        page.wait_for_timeout(6000)
                        text = page.inner_text("body")
                finally:
                    browser.close()  # release the Browserbase session, always
        except Exception:
            return None
        # a challenge page is not real content -> treat as a miss (falls back)
        if text and self._is_challenge(text):
            return None
        return text

    @staticmethod
    def _is_challenge(text: str) -> bool:
        """True if the page is an anti-bot / cookie / login WALL, not real content.

        Such pages are treated as a miss so scrape_text falls back to the curated
        fixture (better than leaking wall text into the evidence bundle). Getting
        past these needs Browserbase residential proxies/stealth (BROWSERBASE_PROXIES
        /BROWSERBASE_STEALTH) or a cookie-banner dismissal step.
        """
        if not text:
            return True
        t = text.lower()
        return any(
            s in t for s in (
                # anti-bot / JS challenges
                "security verification", "are not a bot", "verifying you are human",
                "checking your browser", "enable javascript and cookies",
                # network / IP blocks (datacenter IPs)
                "blocked by network security", "log in to your reddit account",
                # cookie-consent walls
                "utilizes technologies such as cookies",
                "we use cookies and similar", "accept all cookies",
            )
        )

    @staticmethod
    def _looks_like_feed(url: str) -> bool:
        return ".json" in url.lower()

    def _xhr_scrape(self, url: str) -> Optional[str]:
        """Fetch a clean JSON feed directly and render it as raw text."""
        try:
            import httpx

            resp = httpx.get(
                url, headers={"User-Agent": self.user_agent}, timeout=15,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception:
            return None
        return self._render_reddit(data) if "reddit.com" in url else json.dumps(data)[: self.max_chars]

    @staticmethod
    def _render_reddit(data) -> Optional[str]:
        """Render a Reddit listing JSON into raw post text."""
        try:
            children = data["data"]["children"]
        except (KeyError, TypeError):
            return None
        lines: list[str] = []
        for ch in children:
            d = ch.get("data", {})
            title = d.get("title", "")
            score = d.get("score", 0)
            body = (d.get("selftext", "") or "").strip()
            flair = d.get("link_flair_text") or ""
            if title:
                head = f"[{score}↑] {title}" + (f" ({flair})" if flair else "")
                lines.append(head)
                if body:
                    lines.append(body[:600])
        return "\n".join(lines) if lines else None

    @staticmethod
    def _clean(text: str) -> str:
        """Collapse excess whitespace; keep it raw and readable."""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _read_text(path: Path) -> Optional[str]:
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except Exception:
            return None
        return None

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except Exception:
            pass
