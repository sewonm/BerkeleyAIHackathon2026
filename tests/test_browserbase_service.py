"""
Phase 3 — BrowserbaseService tests.

Covers:
- cache -> fixture -> (xhr/live) resolution order and offline safety (SA-SCRAPE-04),
- the real Playwright-over-CDP lifecycle via a fake browser (SA-SCRAPE-01),
- sessions ALWAYS closed in finally, even when navigation raises (criterion 4).

No real Browserbase key is needed: the live path is exercised against a fake
CDP browser injected via monkeypatch.
"""

from pathlib import Path

import pytest

from app.services.browserbase_service import BrowserbaseService, cache_name

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "noisy"


# ---------------------------------------------------------------------------
# Resolution order + offline safety (SA-SCRAPE-04)
# ---------------------------------------------------------------------------

def test_cache_name_stable_and_safe():
    n = cache_name("https://www.reddit.com/r/baseball/hot/.json?limit=10")
    assert n.endswith(".txt")
    assert "/" not in n and "?" not in n
    assert n == cache_name("https://www.reddit.com/r/baseball/hot/.json?limit=10")


def test_cache_hit_returns_cached(tmp_path):
    svc = BrowserbaseService(cache_dir=tmp_path, offline=True)
    url = "https://example.com/page"
    (tmp_path / cache_name(url)).write_text("CACHED RAW TEXT", encoding="utf-8")
    assert svc.scrape_text(url) == "CACHED RAW TEXT"


def test_fixture_fallback_offline(tmp_path):
    """With network off, shipped fixtures still return raw text."""
    svc = BrowserbaseService(
        cache_dir=tmp_path, fixtures_dir=FIXTURES_DIR, offline=True
    )
    url = "https://www.reddit.com/r/baseball/hot/.json?limit=10"
    text = svc.scrape_text(url)
    assert text and "r/baseball" in text


def test_offline_without_data_returns_none(tmp_path):
    svc = BrowserbaseService(cache_dir=tmp_path, offline=True)
    assert svc.scrape_text("https://nope.example.com/missing") is None


def test_successful_scrape_is_cached(tmp_path, monkeypatch):
    """A live scrape result is written through to the cache."""
    cache = tmp_path / "cache"
    svc = BrowserbaseService(cache_dir=cache)
    # has_live_capability is a property -> patch at the class level
    monkeypatch.setattr(BrowserbaseService, "has_live_capability", property(lambda self: True))
    monkeypatch.setattr(svc, "_live_scrape", lambda url, sel: "FRESH RAW TEXT")
    url = "https://fbref.com/en/something"
    assert svc.scrape_text(url) == "FRESH RAW TEXT"
    # second call hits cache (no live needed)
    monkeypatch.setattr(svc, "_live_scrape", lambda url, sel: pytest.fail("used live"))
    assert svc.scrape_text(url) == "FRESH RAW TEXT"
    assert (cache / cache_name(url)).is_file()


def test_max_chars_caps_output(tmp_path):
    svc = BrowserbaseService(cache_dir=tmp_path, offline=True, max_chars=10)
    url = "https://example.com/big"
    (tmp_path / cache_name(url)).write_text("X" * 500, encoding="utf-8")
    assert len(svc.scrape_text(url)) == 10


def test_no_live_capability_without_key():
    svc = BrowserbaseService(api_key="", offline=False)
    assert svc.has_live_capability is False


# ---------------------------------------------------------------------------
# Real CDP lifecycle via a fake browser (SA-SCRAPE-01 + always-close)
# ---------------------------------------------------------------------------

class _FakePage:
    def __init__(self, raise_on_goto=False):
        self.raise_on_goto = raise_on_goto

    def set_default_timeout(self, *_a, **_k):
        pass

    def goto(self, *_a, **_k):
        if self.raise_on_goto:
            raise RuntimeError("navigation blew up")

    def wait_for_selector(self, *_a, **_k):
        pass

    def wait_for_timeout(self, *_a, **_k):
        pass

    def inner_text(self, _sel):
        return "  LIVE   raw\n\n\n body  text "


class _FakeContext:
    def __init__(self, page):
        self.pages = [page]

    def new_page(self):
        return self.pages[0]


class _FakeBrowser:
    def __init__(self, page, closed_flag):
        self.contexts = [_FakeContext(page)]
        self._closed_flag = closed_flag

    def close(self):
        self._closed_flag["closed"] = True


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser

    def connect_over_cdp(self, _url):
        return self._browser


class _FakePW:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _install_fake_playwright(monkeypatch, page, closed_flag):
    import app.services.browserbase_service as mod

    browser = _FakeBrowser(page, closed_flag)
    fake_module = type("M", (), {"sync_playwright": staticmethod(lambda: _FakePW(browser))})
    monkeypatch.setitem(
        __import__("sys").modules, "playwright.sync_api", fake_module
    )
    return mod


def test_live_scrape_extracts_and_closes(monkeypatch):
    closed = {"closed": False}
    svc = BrowserbaseService(api_key="k", project_id="p", cache_dir="/tmp/bb_t1")
    monkeypatch.setattr(svc, "_create_bb_session", lambda: ("wss://fake", {}))
    _install_fake_playwright(monkeypatch, _FakePage(), closed)

    text = svc._live_scrape("https://fbref.com/x", None)
    assert text is not None and "LIVE" in text
    assert closed["closed"] is True, "browser/session must be closed"


def test_live_scrape_closes_even_on_error(monkeypatch):
    """Session is released in finally even when navigation raises."""
    closed = {"closed": False}
    svc = BrowserbaseService(api_key="k", project_id="p", cache_dir="/tmp/bb_t2")
    monkeypatch.setattr(svc, "_create_bb_session", lambda: ("wss://fake", {}))
    _install_fake_playwright(monkeypatch, _FakePage(raise_on_goto=True), closed)

    text = svc._live_scrape("https://fbref.com/x", None)
    assert text is None  # never raises
    assert closed["closed"] is True, "browser must close on the error path too"
