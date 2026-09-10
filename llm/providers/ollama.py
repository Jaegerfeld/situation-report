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
import os
import time
import urllib.error
import urllib.request
from typing import Any

from llm.base import DEPLOYMENT_LOCAL, LlmResult

_DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT_SECONDS = 300  # lokale CPU-Inferenz darf dauern
_LIST_TIMEOUT_SECONDS = 3  # nur ein Verzeichnis abfragen — darf nie haengen

#: Environment variable Ollama itself uses to name its host.
_HOST_ENV = "OLLAMA_HOST"

#: Patchable in tests.
_urlopen = urllib.request.urlopen


def resolve_base_url(config: dict[str, Any] | None = None) -> str:
    """
    Decide which Ollama to talk to, in one place.

    Precedence: explicit config (CLI flag or GUI field) → the OLLAMA_HOST
    environment variable → localhost. Both ``complete`` and ``list_models``
    call this, so the model list and the completions always come from the
    same host — a dropdown filled from localhost while the completion goes
    elsewhere would be two populations pretending to be one.

    Ollama sets OLLAMA_HOST as a bare ``host:port`` without a scheme, which
    urllib cannot open, so a missing scheme is filled in.

    Args:
        config: Provider config; only ``base_url`` is read.

    Returns:
        A base URL with a scheme and without a trailing slash.
    """
    raw = str((config or {}).get("base_url") or os.environ.get(_HOST_ENV) or "").strip()
    if not raw:
        return _DEFAULT_BASE_URL
    if "://" not in raw:
        raw = f"http://{raw}"
    return raw.rstrip("/")


def normalise_model(name: str) -> str:
    """
    Give a model name its tag, the way Ollama itself does.

    ``ollama list`` prints 'mistral-nemo:latest' while a pull or an API call
    accepts the bare 'mistral-nemo' — same model, two spellings. Comparing
    the raw strings would make a chooser fail to recognise its own default
    in the list it just fetched.

    Args:
        name: A model name with or without a tag.

    Returns:
        The name with an explicit tag.
    """
    return name if ":" in name else f"{name}:latest"


class OllamaProvider:
    """Local models via Ollama's native chat API."""

    provider_id = "ollama"
    deployment_class = DEPLOYMENT_LOCAL
    default_model = "mistral-nemo"  # Entscheidung Robert 03.09.2026

    def list_models(self, config: dict[str, Any] | None = None) -> list[str]:
        """
        Name the models this Ollama has pulled, for a chooser to offer.

        Optional capability, not part of the LlmProvider protocol: a caller
        asks for it with ``hasattr``. Not every backend can enumerate its
        models without credentials, and widening the contract would break
        provider discovery for the ones that cannot.

        Never raises and never blocks for long — a chooser that hangs when
        Ollama is not running is worse than one that offers nothing. Callers
        get an empty list and are expected to stay usable with it.

        Args:
            config: Provider config; only ``base_url`` is read.

        Returns:
            Model names including their tag (e.g. 'llama3.1:8b'), sorted;
            empty when Ollama could not be reached or answered oddly.
        """
        request = urllib.request.Request(
            f"{resolve_base_url(config)}/api/tags", method="GET")
        try:
            with _urlopen(request, timeout=_LIST_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            names = [str(m["name"]) for m in data.get("models", []) if m.get("name")]
        except Exception:  # noqa: BLE001 - a chooser must survive any failure
            return []
        return sorted(names)

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """
        One non-streaming chat completion against the local Ollama.

        Config: {"base_url"?, "model"?, "temperature"?}. An empty or missing
        ``model`` means the provider default, so a stored blank keeps working
        when that default changes.

        Raises:
            RuntimeError: With an actionable hint — connection refused
                          means Ollama is not running; a 404 on the model
                          means it was not pulled yet.
        """
        base_url = resolve_base_url(config)
        model = str(config.get("model") or self.default_model)
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
