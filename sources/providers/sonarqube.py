# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   SonarQube-Provider (C2, Qualität): Referenz-Anbindung an den
#   De-facto-Standard der statischen Code-Qualität (von der Roadmap
#   ausdrücklich benannt). Liest je Komponente Coverage, Maintainability-
#   Rating und die Zahl kritischer Verstöße über /api/measures/component.
#   Auth per Token als HTTP-Basic (Token als Benutzer, leeres Passwort —
#   die Sonar-Konvention), aus einer Umgebungsvariable.
# =============================================================================

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sources.base import KIND_QUALITY, QualityRecord, Record
from sources.http import basic, get_json, token_from_env

_METRIC_KEYS = "coverage,sqale_rating,violations,critical_violations"
#: Sonar sqale_rating numeric value → letter.
_RATINGS = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}


class SonarqubeSource:
    """Quality figures from SonarQube component measures."""

    provider_id = "sonarqube"
    kinds = (KIND_QUALITY,)

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Fetch measures for the configured components.

        Config: {"base_url", "token_env"?, "components": [
                 {"component", "unit"?}]}.
        """
        base_url = str(config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise RuntimeError("SonarQube source: 'base_url' is required.")
        token = token_from_env(config, "SONAR_TOKEN")
        headers = basic(token, "") if token else {}
        fetched_at = datetime.now().isoformat(timespec="seconds")

        records: list[Record] = []
        for comp in config.get("components", []):
            component = str(comp.get("component", ""))
            if not component:
                raise RuntimeError(
                    "SonarQube source: entry without 'component' key.")
            url = (f"{base_url}/api/measures/component?"
                   + urllib.parse.urlencode(
                       {"component": component,
                        "metricKeys": _METRIC_KEYS}))
            data = get_json(url, headers, "SonarQube")
            measures = _measures(data)
            record = QualityRecord(
                unit=str(comp.get("unit", component)),
                coverage_pct=_as_float(measures.get("coverage")),
                maintainability=_RATINGS.get(
                    str(measures.get("sqale_rating", "")),
                    str(measures.get("sqale_rating", ""))),
                critical_issues=_as_int(measures.get("critical_violations")),
                source=f"sonarqube:{urllib.parse.urlsplit(base_url).netloc}",
                fetched_at=fetched_at,
            )
            records.append(record)
            log(f"  sonarqube: {record.unit} coverage={record.coverage_pct}")
        return records


def _measures(data: Any) -> dict[str, str]:
    """Flatten the measures array into {metric: value}."""
    try:
        return {m["metric"]: m.get("value", "")
                for m in data["component"]["measures"]}
    except (KeyError, TypeError):
        return {}


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


PROVIDER = SonarqubeSource()
