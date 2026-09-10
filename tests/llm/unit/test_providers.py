# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der LLM-Provider — alle HTTP-Aufrufe gemockt (dasselbe
#   _urlopen-Recorder-Muster wie bei den sources-Providern): Ollama
#   (Payload, /api/chat, 404→„ollama pull", nicht erreichbar→Hinweis auf
#   die Installationsanleitung), Claude (Schlüssel NUR aus ENV, Header,
#   401/403→Freigabe-Hinweis inkl. lokalem Ausweg) und der Mock.
# =============================================================================

from __future__ import annotations

import io
import json
import urllib.error
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from llm.base import discover_providers, provider_config
from llm.providers.claude import PROVIDER as CLAUDE
from llm.providers.mock import PROVIDER as MOCK
from llm.providers.ollama import PROVIDER as OLLAMA
from llm.providers.ollama import normalise_model, resolve_base_url


@contextmanager
def _mock_urlopen(target: str, payload=None, error: Exception | None = None):
    """Patch a provider's _urlopen; records requests, serves one payload."""
    calls: list = []

    def fake_urlopen(req, timeout=0):
        calls.append(req)
        if error is not None:
            raise error
        body = json.dumps(payload).encode("utf-8")

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()

        return _Resp(body)

    with patch(target, side_effect=fake_urlopen):
        yield calls


def _http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", code, "err", None,
                                  io.BytesIO(body))


class TestOllama:
    def test_payload_endpoint_and_result(self) -> None:
        payload = {"message": {"role": "assistant",
                               "content": "  Alles ruhig.  "}}
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           payload) as calls:
            result = OLLAMA.complete("SYS", "BRIEFING", {})
        [req] = calls
        assert req.get_full_url() == "http://localhost:11434/api/chat"
        sent = json.loads(req.data.decode("utf-8"))
        assert sent["model"] == "mistral-nemo"
        assert sent["stream"] is False
        assert sent["messages"] == [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "BRIEFING"}]
        assert result.text == "Alles ruhig."
        assert result.provider_id == "ollama"
        assert result.deployment_class == "local"
        assert result.duration_s >= 0

    def test_config_overrides_base_url_and_model(self) -> None:
        payload = {"message": {"content": "ok"}}
        cfg = {"base_url": "http://gpu-box:11434/", "model": "llama3.1"}
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           payload) as calls:
            result = OLLAMA.complete("s", "p", cfg)
        assert calls[0].get_full_url() == "http://gpu-box:11434/api/chat"
        assert json.loads(calls[0].data)["model"] == "llama3.1"
        assert result.model == "llama3.1"

    def test_missing_model_hints_at_ollama_pull(self) -> None:
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           error=_http_error(404, b"model not found")):
            with pytest.raises(RuntimeError, match="ollama pull mistral-nemo"):
                OLLAMA.complete("s", "p", {})

    def test_unreachable_hints_at_installation_guide(self) -> None:
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           error=urllib.error.URLError("refused")):
            with pytest.raises(RuntimeError,
                               match="Is Ollama installed and running"):
                OLLAMA.complete("s", "p", {})

    def test_empty_completion_is_an_error(self) -> None:
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           {"message": {"content": "   "}}):
            with pytest.raises(RuntimeError, match="empty completion"):
                OLLAMA.complete("s", "p", {})


class TestClaude:
    def test_key_only_from_env_and_headers(self, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
        payload = {"model": "claude-sonnet-5-20260901",
                   "content": [{"type": "text", "text": "Teil 1. "},
                               {"type": "text", "text": "Teil 2."}]}
        with _mock_urlopen("llm.providers.claude._urlopen",
                           payload) as calls:
            result = CLAUDE.complete("SYS", "BRIEFING", {})
        [req] = calls
        assert req.get_full_url() == "https://api.anthropic.com/v1/messages"
        assert req.get_header("X-api-key") == "sk-test-123"
        assert req.get_header("Anthropic-version") == "2023-06-01"
        sent = json.loads(req.data.decode("utf-8"))
        assert sent["system"] == "SYS"
        assert sent["messages"] == [{"role": "user", "content": "BRIEFING"}]
        assert sent["model"] == "claude-sonnet-5"
        assert result.text == "Teil 1. Teil 2."
        # Das Audit sieht das tatsaechlich servierte Modell, nicht den Alias.
        assert result.model == "claude-sonnet-5-20260901"
        assert result.deployment_class == "external_api"

    def test_missing_env_key_fails_with_local_alternative(
            self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is empty"):
            CLAUDE.complete("s", "p", {})
        with pytest.raises(RuntimeError, match="'ollama'"):
            CLAUDE.complete("s", "p", {})

    def test_custom_token_env(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("MY_CLAUDE_KEY", "sk-alt")
        payload = {"content": [{"type": "text", "text": "ok"}]}
        with _mock_urlopen("llm.providers.claude._urlopen",
                           payload) as calls:
            CLAUDE.complete("s", "p", {"token_env": "MY_CLAUDE_KEY"})
        assert calls[0].get_header("X-api-key") == "sk-alt"

    def test_auth_error_hints_at_approval_and_ollama(
            self, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-bad")
        with _mock_urlopen("llm.providers.claude._urlopen",
                           error=_http_error(401)):
            with pytest.raises(RuntimeError,
                               match="local provider 'ollama' needs no "
                                     "approval"):
                CLAUDE.complete("s", "p", {})


class TestMock:
    def test_deterministic_labeled_and_number_free(self) -> None:
        de = MOCK.complete("s", "p", {"lang": "de"})
        en = MOCK.complete("s", "p", {"lang": "en"})
        assert "ATTRAPPE" in de.text
        assert "MOCK" in en.text
        # Bewusst zahlenfrei: der Zahlen-Waechter kann strukturell nie
        # anschlagen — Demo-Weg ohne Ollama-Installation.
        from llm.guard import extract_numbers
        assert extract_numbers(de.text) == set()
        assert extract_numbers(en.text) == set()
        assert de.deployment_class == "mock"


# ---------------------------------------------------------------------------
# Modellwahl und Adresse (Ollama)
# ---------------------------------------------------------------------------

class TestResolveBaseUrl:
    """Where the requests go, decided in one place for complete() and list_models()."""

    def test_default_without_config_or_environment(self, monkeypatch) -> None:
        """Nothing given means localhost."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        assert resolve_base_url({}) == "http://localhost:11434"
        assert resolve_base_url(None) == "http://localhost:11434"

    def test_config_wins_over_environment(self, monkeypatch) -> None:
        """An explicit flag or GUI field beats an inherited environment."""
        monkeypatch.setenv("OLLAMA_HOST", "http://from-env:1")
        assert resolve_base_url({"base_url": "http://explicit:2"}) == \
            "http://explicit:2"

    def test_environment_is_used_when_nothing_explicit(self, monkeypatch) -> None:
        """OLLAMA_HOST is the variable Ollama itself uses, so it is honoured."""
        monkeypatch.setenv("OLLAMA_HOST", "http://from-env:11434")
        assert resolve_base_url({}) == "http://from-env:11434"

    def test_bare_host_port_gets_a_scheme(self, monkeypatch) -> None:
        """Ollama writes OLLAMA_HOST without a scheme; urllib cannot open that.

        Without this, the environment variable would produce a URL that fails
        with an opaque error instead of working.
        """
        monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
        assert resolve_base_url({}) == "http://127.0.0.1:11434"

    def test_trailing_slash_is_dropped(self, monkeypatch) -> None:
        """The path is appended directly, so a trailing slash would double up."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        assert resolve_base_url({"base_url": "http://box:11434/"}) == \
            "http://box:11434"

    def test_empty_config_value_falls_through(self, monkeypatch) -> None:
        """An empty GUI field means 'not set', not 'the empty address'."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        assert resolve_base_url({"base_url": "   "}) == "http://localhost:11434"


class TestNormaliseModel:
    """'mistral-nemo' and 'mistral-nemo:latest' are one model with two spellings."""

    def test_bare_name_gets_latest(self) -> None:
        assert normalise_model("mistral-nemo") == "mistral-nemo:latest"

    def test_tagged_name_is_left_alone(self) -> None:
        assert normalise_model("llama3.1:8b") == "llama3.1:8b"


class TestListModels:
    """The chooser's source — must never raise and never block for long."""

    def test_lists_names_sorted(self) -> None:
        payload = {"models": [{"name": "qwen3.8:latest"},
                              {"name": "mistral-nemo:latest"}]}
        with _mock_urlopen("llm.providers.ollama._urlopen", payload) as calls:
            models = OLLAMA.list_models({})
        assert models == ["mistral-nemo:latest", "qwen3.8:latest"]
        assert calls[0].get_full_url() == "http://localhost:11434/api/tags"
        assert calls[0].get_method() == "GET"

    def test_uses_the_same_base_url_as_complete(self) -> None:
        """A dropdown from localhost with completions elsewhere would be two systems."""
        payload = {"models": [{"name": "a:latest"}]}
        cfg = {"base_url": "http://gpu-box:11434"}
        with _mock_urlopen("llm.providers.ollama._urlopen", payload) as calls:
            OLLAMA.list_models(cfg)
        assert calls[0].get_full_url() == "http://gpu-box:11434/api/tags"

    def test_unreachable_returns_empty_instead_of_raising(self) -> None:
        """Ollama not running must leave a usable chooser, not an error dialog."""
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           error=urllib.error.URLError("refused")):
            assert OLLAMA.list_models({}) == []

    def test_unexpected_payload_returns_empty(self) -> None:
        """Anything but the documented shape counts as 'nothing to offer'."""
        with _mock_urlopen("llm.providers.ollama._urlopen", {"nope": 1}):
            assert OLLAMA.list_models({}) == []

    def test_entries_without_a_name_are_skipped(self) -> None:
        payload = {"models": [{"name": "a:latest"}, {"size": 1}, {"name": ""}]}
        with _mock_urlopen("llm.providers.ollama._urlopen", payload):
            assert OLLAMA.list_models({}) == ["a:latest"]

    def test_short_timeout_so_a_chooser_never_hangs(self) -> None:
        """The 300s completion timeout must not be reused for a directory call."""
        timeouts: list = []

        def fake_urlopen(req, timeout=0):
            timeouts.append(timeout)
            raise urllib.error.URLError("refused")

        with patch("llm.providers.ollama._urlopen", side_effect=fake_urlopen):
            OLLAMA.list_models({})
        assert timeouts and timeouts[0] <= 5

    def test_empty_model_means_the_provider_default(self) -> None:
        """A blank stored choice keeps working when the default changes."""
        with _mock_urlopen("llm.providers.ollama._urlopen",
                           {"message": {"content": "ok"}}) as calls:
            OLLAMA.complete("s", "p", {"model": ""})
        assert json.loads(calls[0].data)["model"] == "mistral-nemo"


class TestProviderConfig:
    """One helper builds the override dict everywhere, so no entry point forgets one."""

    def test_none_when_nothing_is_overridden(self) -> None:
        assert provider_config() is None
        assert provider_config("", "") is None

    def test_only_the_given_keys_appear(self) -> None:
        assert provider_config("m") == {"model": "m"}
        assert provider_config(base_url="u") == {"base_url": "u"}
        assert provider_config("m", "u") == {"model": "m", "base_url": "u"}


class TestOptionalCapability:
    """list_models stays outside the protocol; discovery must not require it."""

    def test_providers_without_list_models_still_discover(self) -> None:
        providers = discover_providers()
        assert set(providers) >= {"ollama", "claude", "mock"}
        assert hasattr(providers["ollama"], "list_models")
        assert not hasattr(providers["claude"], "list_models")
