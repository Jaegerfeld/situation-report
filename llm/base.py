# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       11.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   KI-Provider-Framework (Phase D): das sources-Muster, auf LLMs
#   übertragen. Ein schmaler Provider-Contract (complete(system, prompt,
#   config) → LlmResult) entkoppelt das Lagebild von jedem Anbieter;
#   Provider sind austauschbar (lokal wie extern), und eine neue
#   Anbindung ist EINE Datei in llm/providers/ mit PROVIDER-Objekt —
#   Auto-Discovery, kein Register. Jedes Ergebnis trägt seine
#   deployment_class (local / remote / external_api) für Kennzeichnung
#   und Betreiber-Nachweis — seit D9 (11.10.2026) je Aufruf nach der
#   tatsächlichen Adresse bestimmt, nicht nach dem Anbieternamen.
#   Grundsatz bleibt: Das LLM textet, es rechnet nicht — durchgesetzt in
#   llm/guard.py, nicht hier behauptet.
# =============================================================================

from __future__ import annotations

import importlib
import ipaddress
import pkgutil
import urllib.parse
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

DEPLOYMENT_LOCAL = "local"
DEPLOYMENT_REMOTE = "remote"
DEPLOYMENT_EXTERNAL = "external_api"
DEPLOYMENT_MOCK = "mock"
#: No model at all: the prompt bundle was written to a file (provider "export").
DEPLOYMENT_EXPORT = "export"
#: An answer a human brought back from a model the tool never called
#: (llm check, 0.45.0): address unknown, model name as the operator says.
DEPLOYMENT_EXTERNAL_ANSWER = "external_answer"


def classify_endpoint(url: str) -> str:
    """
    Say where a self-operated backend address leads: this machine or another.

    Only a loopback host counts as ``local`` — ``localhost``, ``127.0.0.0/8``,
    ``::1``. Everything else is ``remote``: a box in the same building, a
    VPN endpoint, a cloud VM — from here they are indistinguishable, and the
    label must not claim more than the tool can know. Deliberately no DNS
    lookup: the class has to follow from the configuration alone so the
    operator-evidence log stays reproducible without a network.

    Args:
        url: A base URL; a bare ``host:port`` without a scheme is accepted.

    Returns:
        DEPLOYMENT_LOCAL or DEPLOYMENT_REMOTE.
    """
    raw = url.strip()
    if "://" not in raw:
        raw = f"http://{raw}"
    host = (urllib.parse.urlsplit(raw).hostname or "").strip("[]").lower()
    if host == "localhost":
        return DEPLOYMENT_LOCAL
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        return DEPLOYMENT_REMOTE
    return DEPLOYMENT_LOCAL if is_loopback else DEPLOYMENT_REMOTE


@dataclass
class LlmResult:
    """One completion, with the metadata the audit trail needs."""
    text: str
    provider_id: str
    model: str
    deployment_class: str
    duration_s: float = 0.0
    #: Where the request went (base URL or API address). Hashed into the
    #: audit log, never written there in clear. Empty = provider predates D9.
    endpoint: str = ""


@runtime_checkable
class LlmProvider(Protocol):
    """
    Contract every LLM backend implements.

    ``provider_id`` names the backend in configs and CLI flags;
    ``deployment_class`` is the class for the provider's *default*
    address (what a listing shows); the class that counts is the one on
    each ``LlmResult``, decided per call from the address actually used.
    ``default_model`` is used when the caller does not override it. ``complete`` returns the generated text —
    providers never judge, never label, never log; that happens centrally.
    """
    provider_id: str
    deployment_class: str
    default_model: str

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """Generate a completion; may raise RuntimeError with a clear hint."""
        ...  # pragma: no cover - protocol signature


def provider_config(model: str | None = None,
                    base_url: str | None = None) -> dict[str, str] | None:
    """
    Turn caller overrides into a provider config, or None when there are none.

    Every entry point that lets a user name a model or an address builds the
    same dict, and each one used to build it inline — which is how the model
    override reached the CLI but never the GUI. One helper keeps the two
    knobs together and returns None for "nothing overridden", so a provider
    falls back to its own defaults instead of receiving empty strings.

    Args:
        model:    Model name, or None/empty for the provider default.
        base_url: Backend address, or None/empty for the provider default.

    Returns:
        A config dict, or None when nothing was given.
    """
    config = {k: v for k, v in (("model", model), ("base_url", base_url)) if v}
    return config or None


def discover_providers() -> dict[str, LlmProvider]:
    """
    Find every provider in llm.providers (one file = one backend).

    Returns:
        {provider_id: provider}, sorted by id for stable listings.
    """
    from . import providers as providers_pkg

    found: dict[str, LlmProvider] = {}
    for module_info in pkgutil.iter_modules(providers_pkg.__path__):
        module = importlib.import_module(
            f"{providers_pkg.__name__}.{module_info.name}")
        provider = getattr(module, "PROVIDER", None)
        if provider is None:
            continue
        if not isinstance(provider, LlmProvider):
            raise TypeError(
                f"llm.providers.{module_info.name}.PROVIDER does not "
                f"satisfy the LlmProvider protocol.")
        if provider.provider_id in found:
            raise ValueError(
                f"Duplicate llm provider id '{provider.provider_id}'.")
        found[provider.provider_id] = provider
    return dict(sorted(found.items()))
