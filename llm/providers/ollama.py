# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Ollama-Provider — der LOKALE Weg (PoC-Priorität 1, Mistral): Ollama
#   betreibt Modelle wie mistral-nemo vollständig auf dem eigenen
#   Rechner (deployment_class "local" — keine Daten verlassen das
#   System, kein Token nötig). Native API: POST /api/chat auf
#   localhost:11434, nur Standardbibliothek. Installationsanleitung:
#   docs/ollama_Installationsanleitung_DE.pdf bzw. Doku-Site →
#   Tutorials.
# =============================================================================

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from llm.base import DEPLOYMENT_LOCAL, LlmResult

_DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT_SECONDS = 300  # lokale CPU-Inferenz darf dauern

#: Patchable in tests.
_urlopen = urllib.request.urlopen


class OllamaProvider:
    """Local models via Ollama's native chat API."""

    provider_id = "ollama"
    deployment_class = DEPLOYMENT_LOCAL
    default_model = "mistral-nemo"  # Entscheidung Robert 03.09.2026

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """
        One non-streaming chat completion against the local Ollama.

        Config: {"base_url"?, "model"?, "temperature"?}.

        Raises:
            RuntimeError: With an actionable hint — connection refused
                          means Ollama is not running; a 404 on the model
                          means it was not pulled yet.
        """
        base_url = str(config.get("base_url", _DEFAULT_BASE_URL)).rstrip("/")
        model = str(config.get("model", self.default_model))
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": float(config.get("temperature", 0.2))},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/api/chat", data=body, method="POST")
        request.add_header("Content-Type", "application/json")

        started = time.monotonic()
        try:
            with _urlopen(request, timeout=_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            if exc.code == 404:
                raise RuntimeError(
                    f"Ollama does not know model '{model}' — run "
                    f"'ollama pull {model}' first (see the installation "
                    f"guide). {detail}") from exc
            raise RuntimeError(
                f"Ollama request failed (HTTP {exc.code}). {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Ollama at {base_url}: {exc.reason}. "
                f"Is Ollama installed and running? See the installation "
                f"guide (docs/ollama_Installationsanleitung_DE.pdf).") from exc

        text = str(data.get("message", {}).get("content", "")).strip()
        if not text:
            raise RuntimeError("Ollama returned an empty completion.")
        return LlmResult(text=text, provider_id=self.provider_id,
                         model=model, deployment_class=self.deployment_class,
                         duration_s=time.monotonic() - started)


PROVIDER = OllamaProvider()
