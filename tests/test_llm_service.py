"""
SAFETY-04 offline test suite for LLMService.

All 14 branches are OFFLINE and KEYLESS.
- Provider clients are mocked via unittest.mock.patch
- API keys are set/unset via monkeypatch.setenv
- No network calls, no real keys required
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: build a mock OpenAI-style response with the given content string
# ---------------------------------------------------------------------------

def make_mock_openai_response(content: str) -> MagicMock:
    """Build a mock that mimics openai.ChatCompletion response structure.

    resp.choices[0].message.content = content
    """
    msg = MagicMock()
    msg.content = content

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Fake exception classes for taxonomy tests (no real openai instances needed)
# ---------------------------------------------------------------------------

class APITimeoutError(Exception):
    """Fake timeout error whose class name contains 'Timeout'."""
    pass


# ---------------------------------------------------------------------------
# class TestLLMServiceKeyless
# ---------------------------------------------------------------------------

class TestLLMServiceKeyless:
    """With no key set, LLMService must construct without raising and available must be False."""

    def test_no_key_constructs_without_raise(self, monkeypatch):
        monkeypatch.delenv("ASI1_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from app.services.llm_service import LLMService
        svc = LLMService()
        assert svc is not None

    def test_no_key_available_is_false(self, monkeypatch):
        monkeypatch.delenv("ASI1_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from app.services.llm_service import LLMService
        svc = LLMService()
        assert svc.available is False


# ---------------------------------------------------------------------------
# class TestLLMServiceKeyed
# ---------------------------------------------------------------------------

class TestLLMServiceKeyed:
    """With a key and a mocked client, chat_json returns ok=True and the parsed dict."""

    def test_keyed_returns_ok_true_and_parsed_dict(self, monkeypatch):
        monkeypatch.setenv("ASI1_API_KEY", "fake-key-123")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        mock_resp = make_mock_openai_response('{"category":"sports"}')

        with patch("openai.OpenAI") as MockOpenAI:
            instance = MockOpenAI.return_value
            instance.chat.completions.create.return_value = mock_resp

            from app.services.llm_service import LLMService
            svc = LLMService()
            result = svc.chat_json("sys", "user")

        assert result.ok is True
        assert result.data == {"category": "sports"}


# ---------------------------------------------------------------------------
# class TestParseLadder
# ---------------------------------------------------------------------------

class TestParseLadder:
    """Drive the 5-rung parse ladder via a mocked ASI:One client."""

    def _call_with_raw(self, monkeypatch, raw: str):
        """Helper: set key, mock OpenAI to return `raw`, call chat_json, return ChatResult."""
        monkeypatch.setenv("ASI1_API_KEY", "fake-key-123")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        mock_resp = make_mock_openai_response(raw)

        with patch("openai.OpenAI") as MockOpenAI:
            instance = MockOpenAI.return_value
            instance.chat.completions.create.return_value = mock_resp

            from app.services.llm_service import LLMService
            svc = LLMService()
            return svc.chat_json("sys", "user")

    def test_clean_json(self, monkeypatch):
        """Rung 1: direct json.loads on clean JSON."""
        result = self._call_with_raw(monkeypatch, '{"a":1}')
        assert result.ok is True
        assert result.data == {"a": 1}

    def test_fenced_json(self, monkeypatch):
        """Rung 2: strip ```json``` fences then parse."""
        result = self._call_with_raw(monkeypatch, '```json\n{"a":1}\n```')
        assert result.ok is True
        assert result.data == {"a": 1}

    def test_prose_prefix(self, monkeypatch):
        """Rung 3: first {...} extraction from prose-prefixed response."""
        result = self._call_with_raw(monkeypatch, 'Sure, here you go: {"a":1} done')
        assert result.ok is True
        assert result.data == {"a": 1}

    def test_key_renamed(self, monkeypatch):
        """Rung 1 or 3: JSON with different keys — must parse and return those keys."""
        result = self._call_with_raw(monkeypatch, '{"intent":"sports","q":"x"}')
        assert result.ok is True
        assert result.data == {"intent": "sports", "q": "x"}

    def test_garbage(self, monkeypatch):
        """Rung 5: totally unparseable response — ok=False, error contains 'parse failed', no raise."""
        result = self._call_with_raw(monkeypatch, 'not json at all <<<>>>')
        assert result.ok is False
        assert "parse failed" in result.error
        # Must not raise — reaching here proves that

    def test_empty(self, monkeypatch):
        """Rung 0: empty completion — ok=False, error contains 'empty', no raise."""
        result = self._call_with_raw(monkeypatch, '')
        assert result.ok is False
        assert "empty" in result.error


# ---------------------------------------------------------------------------
# class TestErrorBranches
# ---------------------------------------------------------------------------

class TestErrorBranches:
    """Mock .create to raise provider errors; verify taxonomy mapping and retry behaviour."""

    def _call_with_exc(self, monkeypatch, exc, provider="asi1"):
        """Set key, mock .create to raise exc, return ChatResult."""
        if provider == "asi1":
            monkeypatch.setenv("ASI1_API_KEY", "fake-key-123")
            monkeypatch.delenv("LLM_PROVIDER", raising=False)
        else:
            monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anth-key")
            monkeypatch.setenv("LLM_PROVIDER", "anthropic")

        if provider == "asi1":
            with patch("openai.OpenAI") as MockOpenAI:
                instance = MockOpenAI.return_value
                instance.chat.completions.create.side_effect = exc

                from app.services.llm_service import LLMService
                svc = LLMService()
                return svc.chat_json("sys", "user"), instance.chat.completions.create
        else:
            with patch("anthropic.Anthropic") as MockAnth:
                instance = MockAnth.return_value
                instance.messages.create.side_effect = exc

                from app.services.llm_service import LLMService
                svc = LLMService(provider="anthropic")
                return svc.chat_json("sys", "user"), instance.messages.create

    def test_401(self, monkeypatch):
        """401/auth error maps to ok=False with '401' in error string."""
        exc = Exception("Error code: 401 - unauthorized")
        result, _ = self._call_with_exc(monkeypatch, exc)
        assert result.ok is False
        assert "401" in result.error

    def test_429(self, monkeypatch):
        """Rate-limit triggers exactly ONE retry (create called twice), then ok=False with 'rate' in error."""
        monkeypatch.setenv("ASI1_API_KEY", "fake-key-123")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        rate_exc = Exception("Error code: 429 - rate limit exceeded")

        with patch("openai.OpenAI") as MockOpenAI:
            instance = MockOpenAI.return_value
            # Raise on every call — both initial and retry should fail
            instance.chat.completions.create.side_effect = rate_exc

            from app.services.llm_service import LLMService
            svc = LLMService()

            with patch("time.sleep"):  # avoid actual sleep in tests
                result = svc.chat_json("sys", "user")

        assert result.ok is False
        assert "rate" in result.error
        # ONE retry = create called exactly TWICE
        assert instance.chat.completions.create.call_count == 2

    def test_timeout(self, monkeypatch):
        """Timeout error maps to ok=False with 'timeout' in error string."""
        exc = APITimeoutError("Request timed out")
        result, _ = self._call_with_exc(monkeypatch, exc)
        assert result.ok is False
        assert "timeout" in result.error

    def test_connection(self, monkeypatch):
        """Connection error maps to ok=False with 'connection' in error string."""
        exc = Exception("Connection error: failed to connect")
        result, _ = self._call_with_exc(monkeypatch, exc)
        assert result.ok is False
        assert "connection" in result.error


# ---------------------------------------------------------------------------
# class TestProviderSwap
# ---------------------------------------------------------------------------

class TestProviderSwap:
    """LLM_PROVIDER=anthropic routes to claude-haiku-4-5 behind the same chat_json interface."""

    def test_anthropic_provider_returns_ok_true(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anth-key")

        # Build a mock Anthropic response with .content[0].text = '{"a":1}'
        block = MagicMock()
        block.text = '{"a":1}'

        mock_resp = MagicMock()
        mock_resp.content = [block]

        with patch("anthropic.Anthropic") as MockAnth:
            instance = MockAnth.return_value
            instance.messages.create.return_value = mock_resp

            from app.services.llm_service import LLMService
            svc = LLMService()
            result = svc.chat_json("sys", "user")

        assert result.ok is True
        assert result.provider == "anthropic"
        assert result.data == {"a": 1}


# ---------------------------------------------------------------------------
# class TestNoKeyLeak
# ---------------------------------------------------------------------------

class TestNoKeyLeak:
    """API key must never appear in result.error even if the exception message embeds it."""

    def test_key_not_in_error(self, monkeypatch):
        fake_key = "sk-SECRET123"
        monkeypatch.setenv("ASI1_API_KEY", fake_key)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        # Exception whose str() embeds the fake key (simulates sdk leaking key in exc message)
        exc = Exception(f"Error code: 401 - auth failed, key={fake_key}")

        with patch("openai.OpenAI") as MockOpenAI:
            instance = MockOpenAI.return_value
            instance.chat.completions.create.side_effect = exc

            from app.services.llm_service import LLMService
            svc = LLMService()
            result = svc.chat_json("sys", "user")

        assert result.ok is False
        assert fake_key not in result.error, (
            f"API key leaked into result.error: {result.error!r}"
        )
