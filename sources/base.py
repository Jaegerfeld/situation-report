# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Generisches Quellen-Framework für externe Kennzahlen (Roadmap C1/C2).
#   Kern der Flexibilität: normierte Record-Contracts (SLO, DORA, Qualität)
#   trennen das Lagebild von jedem konkreten System — Provider sind
#   austauschbar, kombinierbar (mehrere Quellen füllen dasselbe Register)
#   und leicht erweiterbar: Eine neue Quelle ist EINE Datei in
#   sources/providers/ mit einem PROVIDER-Objekt; die Discovery findet sie
#   automatisch. Jeder Record trägt seine Herkunft (source, fetched_at).
# =============================================================================

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

KIND_SLO = "slo"
KIND_DORA = "dora"
KIND_QUALITY = "quality"
KINDS = (KIND_SLO, KIND_DORA, KIND_QUALITY)


@dataclass
class SloRecord:
    """
    One service-level objective with its current indicator (C1).

    ``target_pct``/``sli_pct`` are percentages (e.g. 99.9). The error budget
    and the status are NOT provider fields — they are derived centrally
    (portfolio.slo_config) so every source is judged by the same rule.
    """
    service: str
    slo: str                     # human-readable objective, e.g. "p95 < 200 ms"
    target_pct: float
    sli_pct: float | None = None
    window: str = "30d"
    source: str = ""
    fetched_at: str = ""


@dataclass
class DoraRecord:
    """The four DORA keys for one delivery unit (C2)."""
    unit: str
    deployments_per_day: float | None = None
    lead_time_hours: float | None = None
    change_failure_rate_pct: float | None = None
    time_to_restore_hours: float | None = None
    window: str = "30d"
    source: str = ""
    fetched_at: str = ""


@dataclass
class QualityRecord:
    """Static-quality figures for one unit/component (C2)."""
    unit: str
    coverage_pct: float | None = None
    maintainability: str = ""    # rating letter (A-E) or free text
    critical_issues: int | None = None
    source: str = ""
    fetched_at: str = ""


#: Record class per kind — the normalisation contract of the framework.
RECORD_TYPES = {KIND_SLO: SloRecord, KIND_DORA: DoraRecord,
                KIND_QUALITY: QualityRecord}

Record = SloRecord | DoraRecord | QualityRecord


@runtime_checkable
class SourceProvider(Protocol):
    """
    Contract every source implements.

    ``provider_id`` names the source in configs ("prometheus"),
    ``kinds`` lists what it can deliver, ``fetch`` returns normalised
    records for one kind. Providers never render and never judge status —
    they only translate a foreign system into the record contract.
    """
    provider_id: str
    kinds: tuple[str, ...]

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """Fetch records of ``kind`` as configured; may raise RuntimeError."""
        ...  # pragma: no cover - protocol signature


def discover_providers() -> dict[str, SourceProvider]:
    """
    Find every provider in sources.providers.

    A provider registers itself by being a module in ``sources/providers/``
    that defines a module-level ``PROVIDER`` object satisfying
    SourceProvider — adding a new source needs no registry edit anywhere.

    Returns:
        {provider_id: provider}, sorted by id for stable listings.
    """
    from . import providers as providers_pkg

    found: dict[str, SourceProvider] = {}
    for module_info in pkgutil.iter_modules(providers_pkg.__path__):
        module = importlib.import_module(
            f"{providers_pkg.__name__}.{module_info.name}")
        provider = getattr(module, "PROVIDER", None)
        if provider is None:
            continue
        if not isinstance(provider, SourceProvider):
            raise TypeError(
                f"sources.providers.{module_info.name}.PROVIDER does not "
                f"satisfy the SourceProvider protocol.")
        if provider.provider_id in found:
            raise ValueError(
                f"Duplicate provider id '{provider.provider_id}'.")
        found[provider.provider_id] = provider
    return dict(sorted(found.items()))


def record_to_dict(record: Record) -> dict[str, Any]:
    """Serialise a record, dropping empty optionals for clean JSON."""
    return {k: v for k, v in asdict(record).items()
            if v not in (None, "")}


def record_from_dict(kind: str, data: dict[str, Any]) -> Record:
    """
    Build a record of ``kind`` from a plain dict (file provider, registers).

    Unknown keys are ignored (forward compatibility); missing required keys
    raise ValueError with the field name.
    """
    import dataclasses

    cls = RECORD_TYPES[kind]
    names = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in names}
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise ValueError(f"Invalid {kind} record: {exc}") from exc


@dataclass
class FetchResult:
    """Merged records of one kind, possibly from several providers."""
    kind: str
    records: list[Record] = field(default_factory=list)
