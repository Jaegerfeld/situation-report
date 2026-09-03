# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   GitLab-Provider (C2, DORA): Referenz-Anbindung an das einzige
#   marktübliche System mit NATIVER DORA-API
#   (/api/v4/projects/:id/dora/metrics, Ultimate-Tier) — GitHub u. a.
#   brauchen Drittableitungen. Je Kennzahl ein Abruf über das
#   konfigurierte Fenster; Tageswerte werden gemittelt, Zeiten von
#   Sekunden auf Stunden normiert. Auth per PRIVATE-TOKEN aus einer
#   Umgebungsvariable.
# =============================================================================

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from sources.base import KIND_DORA, DoraRecord, Record
from sources.http import get_json, token_from_env

#: GitLab metric id → (record field, seconds→hours conversion).
_METRICS = {
    "deployment_frequency": ("deployments_per_day", False),
    "lead_time_for_changes": ("lead_time_hours", True),
    "change_failure_rate": ("change_failure_rate_pct", False),
    "time_to_restore_service": ("time_to_restore_hours", True),
}


class GitlabDoraSource:
    """The four DORA keys from GitLab's native DORA metrics API."""

    provider_id = "gitlab"
    kinds = (KIND_DORA,)

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Fetch all four DORA metrics for one project/group.

        Config: {"base_url", "project_id", "unit"?, "token_env"?,
                 "window_days"?}. Requires GitLab Ultimate (the API tier).
        """
        base_url = str(config.get("base_url", "")).rstrip("/")
        project_id = str(config.get("project_id", ""))
        if not base_url or not project_id:
            raise RuntimeError(
                "GitLab source: 'base_url' and 'project_id' are required.")
        token = token_from_env(config, "GITLAB_TOKEN")
        headers = {"PRIVATE-TOKEN": token} if token else {}
        window_days = int(config.get("window_days", 30))
        since = (date.today() - timedelta(days=window_days)).isoformat()
        project = urllib.parse.quote(project_id, safe="")

        record = DoraRecord(
            unit=str(config.get("unit", project_id)),
            window=f"{window_days}d",
            source=f"gitlab:{urllib.parse.urlsplit(base_url).netloc}"
                   f"/{project_id}",
            fetched_at=datetime.now().isoformat(timespec="seconds"),
        )
        for metric, (field_name, to_hours) in _METRICS.items():
            url = (f"{base_url}/api/v4/projects/{project}/dora/metrics?"
                   + urllib.parse.urlencode(
                       {"metric": metric, "start_date": since}))
            data = get_json(url, headers, "GitLab")
            value = _average(data)
            if value is not None and to_hours:
                value /= 3600.0
            setattr(record, field_name, value)
            log(f"  gitlab: {metric}="
                f"{'n/a' if value is None else f'{value:.2f}'}")
        return [record]


def _average(data: Any) -> float | None:
    """Mean over the daily values GitLab returns (ignoring null days)."""
    if not isinstance(data, list):
        return None
    values = [float(e["value"]) for e in data
              if isinstance(e, dict) and e.get("value") is not None]
    return sum(values) / len(values) if values else None


PROVIDER = GitlabDoraSource()
