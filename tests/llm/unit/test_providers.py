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

from llm.providers.claude import PROVIDER as CLAUDE
from llm.providers.mock import PROVIDER as MOCK
from llm.providers.ollama import PROVIDER as OLLAMA


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
