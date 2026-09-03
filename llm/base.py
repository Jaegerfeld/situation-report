# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   KI-Provider-Framework (Phase D): das sources-Muster, auf LLMs
#   übertragen. Ein schmaler Provider-Contract (complete(system, prompt,
#   config) → LlmResult) entkoppelt das Lagebild von jedem Anbieter;
#   Provider sind austauschbar (lokal wie extern), und eine neue
#   Anbindung ist EINE Datei in llm/providers/ mit PROVIDER-Objekt —
#   Auto-Discovery, kein Register. Jedes Ergebnis trägt seine
#   deployment_class (local / external_api) für Kennzeichnung und
#   Betreiber-Nachweis. Grundsatz bleibt: Das LLM textet, es rechnet
#   nicht — durchgesetzt in llm/guard.py, nicht hier behauptet.
# =============================================================================

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

DEPLOYMENT_LOCAL = "local"
DEPLOYMENT_EXTERNAL = "external_api"
DEPLOYMENT_MOCK = "mock"


@dataclass
class LlmResult:
    """One completion, with the metadata the audit trail needs."""
    text: str
    provider_id: str
    model: str
    deployment_class: str
    duration_s: float = 0.0


@runtime_checkable
class LlmProvider(Protocol):
    """
    Contract every LLM backend implements.

    ``provider_id`` names the backend in configs and CLI flags;
    ``deployment_class`` states where the data goes (shown in the AI
    banner and the audit log); ``default_model`` is used when the caller
    does not override it. ``complete`` returns the generated text —
    providers never judge, never label, never log; that happens centrally.
    """
    provider_id: str
    deployment_class: str
    default_model: str

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """Generate a completion; may raise RuntimeError with a clear hint."""
        ...  # pragma: no cover - protocol signature


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
