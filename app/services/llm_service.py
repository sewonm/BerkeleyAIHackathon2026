"""
LLMService — provider-pluggable, never-raising structured-call layer.

SAFETY-04 deliverable: every failure path returns ChatResult(ok=False) and
never raises. No top-level SDK imports; no key reads at import or __init__ time.
Compatible with asyncio.to_thread() as a blocking call boundary.

Providers:
  "asi1"      — ASI:One via OpenAI-compatible client (default)
  "anthropic" — Anthropic claude-haiku-4-5

Env vars read lazily (at call time, not import/init):
  ASI1_API_KEY       — required for asi1 provider
  ANTHROPIC_API_KEY  — required for anthropic provider
  LLM_PROVIDER       — override provider ("asi1" | "anthropic")
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ChatResult — immutable-ish value object returned by chat_json()
# ---------------------------------------------------------------------------

@dataclass
class ChatResult:
    ok: bool                                      # True = data is a valid dict
    data: dict = field(default_factory=dict)      # parsed dict when ok; {} when not
    error: str = ""                               # "" when ok; human-readable reason when not
    provider: str = "none"                        # "asi1" | "anthropic" | "none"


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------

class LLMService:
    """
    Provider-pluggable, never-raising LLM call layer.

    Construction is safe with no env vars and no SDK installed.
    All failure paths return ChatResult(ok=False, ...) — never raises.
    """

    def __init__(self, provider: str | None = None, timeout: float = 15.0):
        # NO key read here. NO SDK import here.
        self.provider = provider or os.getenv("LLM_PROVIDER", "asi1")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Lazy env read at call time so toggling env mid-process works."""
        if self.provider == "asi1":
            return bool(os.getenv("ASI1_API_KEY", "").strip())
        if self.provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
        return False

    def chat_json(self, system: str, user: str) -> ChatResult:
        """
        Blocking. Never raises. Caller wraps in asyncio.to_thread(...).

        Returns ChatResult(ok=True, data=<dict>) on success, or
        ChatResult(ok=False, error=<reason>) on any failure.
        """
        if not self.available:
            return ChatResult(
                ok=False,
                error="LLM unavailable: no key set",
                provider=self.provider,
            )

        try:
            if self.provider == "asi1":
                return self._with_retry(self._call_asi1, system, user)
            elif self.provider == "anthropic":
                return self._with_retry(self._call_anthropic, system, user)
            else:
                return ChatResult(
                    ok=False,
                    error=f"unknown provider: {self.provider!r}",
                    provider=self.provider,
                )
        except Exception as exc:  # absolute catch-all safety net
            logger.error("chat_json unexpected error: %s", type(exc).__name__)
            return ChatResult(
                ok=False,
                error=f"unexpected error ({type(exc).__name__})",
                provider=self.provider,
            )

    # ------------------------------------------------------------------
    # Provider call helpers (lazy SDK imports inside each)
    # ------------------------------------------------------------------

    def _call_asi1(self, system: str, user: str) -> ChatResult:
        """Call ASI:One via OpenAI-compatible client. LAZY openai import."""
        try:
            from openai import OpenAI  # noqa: PLC0415 (lazy by design)
        except ImportError:
            return ChatResult(ok=False, error="openai SDK not installed", provider="asi1")

        try:
            client = OpenAI(
                base_url="https://api.asi1.ai/v1",
                api_key=os.environ["ASI1_API_KEY"],
                timeout=self.timeout,
            )
            resp = client.chat.completions.create(
                model="asi1-mini",
                temperature=0,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            raw = (resp.choices[0].message.content or "") if resp.choices else ""
            return self._parse_ladder(raw, "asi1")
        except Exception as exc:
            return self._handle_provider_error(exc, "asi1")

    def _call_anthropic(self, system: str, user: str) -> ChatResult:
        """Call Anthropic claude-haiku-4-5. LAZY anthropic import."""
        try:
            from anthropic import Anthropic  # noqa: PLC0415 (lazy by design)
        except ImportError:
            return ChatResult(ok=False, error="anthropic SDK not installed", provider="anthropic")

        try:
            client = Anthropic(timeout=self.timeout)
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=512,
                messages=[{"role": "user", "content": f"{system}\n\n{user}"}],
            )
            raw = next((b.text for b in resp.content if hasattr(b, "text")), "")
            return self._parse_ladder(raw, "anthropic")
        except Exception as exc:
            return self._handle_provider_error(exc, "anthropic")

    # ------------------------------------------------------------------
    # One-tight-retry wrapper (RESEARCH.md Pattern 6)
    # ------------------------------------------------------------------

    def _with_retry(self, call_fn, system: str, user: str) -> ChatResult:
        """
        Call call_fn once. If the result signals rate-limit or server error,
        sleep 1 s and call exactly once more. Cap at 1 retry total.
        """
        result = call_fn(system, user)
        if result.ok:
            return result

        should_retry = ("rate" in result.error or "server error" in result.error)
        if should_retry:
            time.sleep(1.0)
            result = call_fn(system, user)

        return result

    # ------------------------------------------------------------------
    # 5-rung parse ladder (RESEARCH.md Pattern 4)
    # ------------------------------------------------------------------

    def _parse_ladder(self, raw: str, provider: str) -> ChatResult:
        """
        Try to extract a JSON dict from `raw` using 5 progressively looser strategies.
        Returns ChatResult(ok=True, data=dict) or ChatResult(ok=False, error=...).
        Never raises.
        """
        # Rung 0: empty completion
        if not raw.strip():
            return ChatResult(ok=False, error="empty completion from LLM", provider=provider)

        # Rung 1: direct json.loads on raw
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return ChatResult(ok=True, data=data, provider=provider)
        except (json.JSONDecodeError, ValueError):
            pass

        # Rung 2: strip ```json / ``` fences then json.loads
        fence_stripped = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            data = json.loads(fence_stripped)
            if isinstance(data, dict):
                return ChatResult(ok=True, data=data, provider=provider)
        except (json.JSONDecodeError, ValueError):
            pass

        # Rung 3: first {...} match on raw (handles prose prefix)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    return ChatResult(ok=True, data=data, provider=provider)
            except (json.JSONDecodeError, ValueError):
                pass

        # Rung 4: first {...} match on fence-stripped string
        m2 = re.search(r"\{.*\}", fence_stripped, re.DOTALL)
        if m2:
            try:
                data = json.loads(m2.group(0))
                if isinstance(data, dict):
                    return ChatResult(ok=True, data=data, provider=provider)
            except (json.JSONDecodeError, ValueError):
                pass

        # Rung 5: total failure — log truncated raw (model output, not the key)
        logger.warning("parse ladder exhausted on raw[:200]=%r", raw[:200])
        return ChatResult(
            ok=False,
            error="parse failed: no valid JSON dict found",
            provider=provider,
        )

    # ------------------------------------------------------------------
    # Error taxonomy (RESEARCH.md Pattern 5)
    # ------------------------------------------------------------------

    def _handle_provider_error(self, exc: Exception, provider: str) -> ChatResult:
        """
        Map provider exceptions to ChatResult(ok=False).
        Logs type(exc).__name__ ONLY — never str(exc) (it can embed the key).
        """
        exc_name = type(exc).__name__
        exc_str = str(exc)  # used only for substring checks, never logged or returned

        logger.error("provider=%s error_type=%s", provider, exc_name)

        # 401 / auth / unauthorized
        if "401" in exc_str or "auth" in exc_str.lower() or "unauthorized" in exc_str.lower():
            return ChatResult(ok=False, error="401 unauthorized", provider=provider)

        # 429 / rate limit
        if "429" in exc_str or "rate" in exc_str.lower():
            return ChatResult(ok=False, error="rate limit", provider=provider)

        # 5xx server error
        if any(code in exc_str for code in ("500", "502", "503", "504")):
            return ChatResult(ok=False, error="server error", provider=provider)

        # Timeout — check class name (e.g. APITimeoutError, TimeoutError, ReadTimeout)
        if "timeout" in exc_name.lower() or "timeout" in exc_str.lower():
            return ChatResult(ok=False, error="timeout", provider=provider)

        # Connection error — check both class name and message
        if "connection" in exc_name.lower() or "connection" in exc_str.lower():
            return ChatResult(ok=False, error="connection error", provider=provider)

        # Catch-all — only surface the type name, never the message (may contain key)
        return ChatResult(
            ok=False,
            error=f"provider error ({exc_name})",
            provider=provider,
        )
