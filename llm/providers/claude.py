# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Claude-Provider — der EXTERNE Weg (Priorität 2): Anthropic Messages
#   API. deployment_class "external_api" steht sichtbar in Kennzeichnung
#   und Audit — die Deployment-Entscheidung ist Konfiguration, nicht
#   Nutzerlaune (Rechts-Leitplanke c). Der API-Schlüssel kommt
#   AUSSCHLIESSLICH aus einer Umgebungsvariable (Standard
#   ANTHROPIC_API_KEY), wird nie gespeichert und nie geloggt — die
#   C3-Token-Regeln gelten identisch. Nur Standardbibliothek.
# =============================================================================

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from llm.base import DEPLOYMENT_EXTERNAL, LlmResult

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 120

#: Patchable in tests.
_urlopen = urllib.request.urlopen


class ClaudeProvider:
    """Anthropic Claude via the Messages API."""

    provider_id = "claude"
    deployment_class = DEPLOYMENT_EXTERNAL
    default_model = "claude-sonnet-5"  # Entscheidung Robert 03.09.2026

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """
        One completion via the Messages API.

        Config: {"model"?, "token_env"? (default ANTHROPIC_API_KEY),
        "max_tokens"?, "temperature"?}.

        Raises:
            RuntimeError: Missing key, auth failure (with the corporate
                          hint and the local fallback), or API errors.
        """
        token_env = str(config.get("token_env", "ANTHROPIC_API_KEY"))
        api_key = os.environ.get(token_env, "")
        if not api_key:
            raise RuntimeError(
                f"Environment variable {token_env} is empty — set it to "
                f"your Anthropic API key (never in configs or code). "
                f"Until then, the local provider 'ollama' is the "
                f"first-class alternative.")
        model = str(config.get("model", self.default_model))
        body = json.dumps({
            "model": model,
            "max_tokens": int(config.get("max_tokens", 1024)),
            "temperature": float(config.get("temperature", 0.2)),
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        request = urllib.request.Request(_API_URL, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("x-api-key", api_key)
        request.add_header("anthropic-version", _API_VERSION)

        started = time.monotonic()
        try:
            with _urlopen(request, timeout=_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if exc.code in (401, 403):
                raise RuntimeError(
                    f"Anthropic refused the request (HTTP {exc.code}): "
                    f"check the API key in {token_env} — or external API "
                    f"use is not approved in your organisation; the local "
                    f"provider 'ollama' needs no approval. {detail}") from exc
            raise RuntimeError(
                f"Anthropic request failed (HTTP {exc.code}). "
                f"{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach the Anthropic API: {exc.reason}") from exc

        parts = data.get("content", [])
        text = "".join(p.get("text", "") for p in parts
                       if isinstance(p, dict)).strip()
        if not text:
            raise RuntimeError("Anthropic returned an empty completion.")
        return LlmResult(text=text, provider_id=self.provider_id,
                         model=str(data.get("model", model)),
                         deployment_class=self.deployment_class,
                         duration_s=time.monotonic() - started)


PROVIDER = ClaudeProvider()
