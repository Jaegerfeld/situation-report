# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prometheus-Provider (C1, SLO/SLI): Referenz-Anbindung an den
#   De-facto-Standard des Open-Source-Monitorings (~77 % Produktionsnutzung;
#   liegt auch hinter vielen Grafana-Installationen). Je konfiguriertem
#   Service wird eine PromQL-Instant-Query (/api/v1/query) ausgeführt,
#   deren Ergebnis der aktuelle SLI in Prozent ist (optional skaliert,
#   wenn die Query 0–1 liefert). Auth optional per Bearer-Token aus einer
#   Umgebungsvariable.
# =============================================================================

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sources.base import KIND_SLO, Record, SloRecord
from sources.http import bearer, get_json, token_from_env


class PrometheusSource:
    """SLO/SLI records from Prometheus instant queries."""

    provider_id = "prometheus"
    kinds = (KIND_SLO,)

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Query one SLI per configured service.

        Config: {"base_url", "token_env"?, "window"?, "services": [
                 {"service", "slo", "target_pct", "sli_query", "scale"?}]}
        ``scale`` multiplies the query result (100 for 0–1 ratios).
        """
        base_url = str(config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise RuntimeError("Prometheus source: 'base_url' is required.")
        headers = bearer(token_from_env(config, "PROMETHEUS_TOKEN"))
        window = str(config.get("window", "30d"))
        fetched_at = datetime.now().isoformat(timespec="seconds")

        records: list[Record] = []
        for svc in config.get("services", []):
            query = str(svc.get("sli_query", ""))
            if not query:
                raise RuntimeError(
                    f"Prometheus source: service "
                    f"'{svc.get('service', '?')}' has no 'sli_query'.")
            url = (f"{base_url}/api/v1/query?"
                   + urllib.parse.urlencode({"query": query}))
            data = get_json(url, headers, "Prometheus")
            sli = _first_value(data)
            if sli is not None:
                sli *= float(svc.get("scale", 1))
            record = SloRecord(
                service=str(svc.get("service", "")),
                slo=str(svc.get("slo", "")),
                target_pct=float(svc.get("target_pct", 0)),
                sli_pct=sli,
                window=window,
                source=f"prometheus:{urllib.parse.urlsplit(base_url).netloc}",
                fetched_at=fetched_at,
            )
            records.append(record)
            log(f"  prometheus: {record.service} sli="
                f"{'n/a' if sli is None else f'{sli:.3f}'}")
        return records


def _first_value(data: Any) -> float | None:
    """Extract the first sample value of an instant-query response."""
    try:
        result = data["data"]["result"]
        if not result:
            return None
        return float(result[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


PROVIDER = PrometheusSource()
