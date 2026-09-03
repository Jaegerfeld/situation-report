# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   GitHub-Provider (C2, DORA) — die Referenz-Quelle auf Wunsch Robert:
#   GitHub ist die größte Plattform, hat aber KEINE native DORA-API; die
#   vier Kennzahlen werden deshalb aus Standard-Endpoints ABGELEITET und
#   die Näherungen sind dokumentiert und konfigurierbar:
#     - Deployment Frequency: Deployments im Fenster (optional je
#       Environment, Standard "production") / Tage.
#     - Lead Time for Changes: Median (merged_at - created_at) der im
#       Fenster gemergten Pull Requests — Näherung an Commit→Production.
#     - Change Failure Rate: Anteil der Deployments, deren jüngster
#       Status failure/error ist (gekappt auf max_deployments Abrufe).
#     - Time to Restore: Median (closed_at - created_at) geschlossener
#       Issues mit dem Incident-Label (Standard "incident").
#   Auth per Bearer-Token aus einer Umgebungsvariable (GITHUB_TOKEN).
# =============================================================================

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sources.base import KIND_DORA, DoraRecord, Record
from sources.http import bearer, get_json, token_from_env

_API_HEADERS = {"X-GitHub-Api-Version": "2022-11-28"}
_PER_PAGE = 100


class GithubDoraSource:
    """The four DORA keys derived from GitHub deployments, PRs and issues."""

    provider_id = "github"
    kinds = (KIND_DORA,)

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Derive DORA metrics for one repository.

        Config: {"owner", "repo", "unit"?, "token_env"? (GITHUB_TOKEN),
                 "window_days"?, "environment"? ("production", "" = all),
                 "incident_label"? ("incident"), "max_deployments"? (50),
                 "base_url"? (github.com API by default, for GHE)}.
        """
        owner = str(config.get("owner", ""))
        repo = str(config.get("repo", ""))
        if not owner or not repo:
            raise RuntimeError(
                "GitHub source: 'owner' and 'repo' are required.")
        base_url = str(config.get("base_url",
                                  "https://api.github.com")).rstrip("/")
        headers = dict(_API_HEADERS)
        headers.update(bearer(token_from_env(config, "GITHUB_TOKEN")))
        window_days = int(config.get("window_days", 30))
        since = datetime.now(UTC) - timedelta(days=window_days)
        environment = str(config.get("environment", "production"))
        repo_url = f"{base_url}/repos/{owner}/{repo}"

        deployments = self._deployments(repo_url, headers, environment, since)
        per_day = len(deployments) / window_days if deployments else 0.0
        log(f"  github: {len(deployments)} deployments in {window_days}d")

        cfr = self._change_failure_rate(
            repo_url, headers, deployments,
            int(config.get("max_deployments", 50)), log)
        lead_time = self._lead_time_hours(repo_url, headers, since, log)
        restore = self._time_to_restore_hours(
            repo_url, headers, since,
            str(config.get("incident_label", "incident")), log)

        return [DoraRecord(
            unit=str(config.get("unit", f"{owner}/{repo}")),
            deployments_per_day=round(per_day, 3),
            lead_time_hours=lead_time,
            change_failure_rate_pct=cfr,
            time_to_restore_hours=restore,
            window=f"{window_days}d",
            source=f"github:{owner}/{repo}",
            fetched_at=datetime.now().isoformat(timespec="seconds"),
        )]

    def _deployments(self, repo_url: str, headers: dict[str, str],
                     environment: str, since: datetime) -> list[dict]:
        """Deployments inside the window (newest first, one page)."""
        params: dict[str, Any] = {"per_page": _PER_PAGE}
        if environment:
            params["environment"] = environment
        url = f"{repo_url}/deployments?" + urllib.parse.urlencode(params)
        data = get_json(url, headers, "GitHub")
        if not isinstance(data, list):
            return []
        return [d for d in data
                if (ts := _ts(d.get("created_at"))) is not None
                and ts >= since]

    def _change_failure_rate(self, repo_url: str, headers: dict[str, str],
                             deployments: list[dict], cap: int,
                             log: Callable[[str], None]) -> float | None:
        """Share of deployments whose latest status is failure/error."""
        sample = deployments[:cap]
        if not sample:
            return None
        failed = 0
        for dep in sample:
            url = (f"{repo_url}/deployments/{dep.get('id')}/statuses?"
                   + urllib.parse.urlencode({"per_page": 1}))
            statuses = get_json(url, headers, "GitHub")
            state = (statuses[0].get("state", "")
                     if isinstance(statuses, list) and statuses else "")
            if state in ("failure", "error"):
                failed += 1
        return round(failed / len(sample) * 100, 1)

    def _lead_time_hours(self, repo_url: str, headers: dict[str, str],
                         since: datetime,
                         log: Callable[[str], None]) -> float | None:
        """Median created→merged of PRs merged inside the window."""
        url = (f"{repo_url}/pulls?" + urllib.parse.urlencode(
            {"state": "closed", "sort": "updated", "direction": "desc",
             "per_page": _PER_PAGE}))
        data = get_json(url, headers, "GitHub")
        if not isinstance(data, list):
            return None
        hours = []
        for pr in data:
            merged = _ts(pr.get("merged_at"))
            created = _ts(pr.get("created_at"))
            if merged and created and merged >= since:
                hours.append((merged - created).total_seconds() / 3600)
        log(f"  github: {len(hours)} merged PRs in window")
        return round(median(hours), 1) if hours else None

    def _time_to_restore_hours(self, repo_url: str, headers: dict[str, str],
                               since: datetime, label: str,
                               log: Callable[[str], None]) -> float | None:
        """Median open→closed of incident-labelled issues in the window."""
        url = (f"{repo_url}/issues?" + urllib.parse.urlencode(
            {"state": "closed", "labels": label,
             "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "per_page": _PER_PAGE}))
        data = get_json(url, headers, "GitHub")
        if not isinstance(data, list):
            return None
        hours = []
        for issue in data:
            if "pull_request" in issue:
                continue
            closed = _ts(issue.get("closed_at"))
            created = _ts(issue.get("created_at"))
            if closed and created and closed >= since:
                hours.append((closed - created).total_seconds() / 3600)
        log(f"  github: {len(hours)} closed '{label}' issues in window")
        return round(median(hours), 1) if hours else None


def _ts(value: Any) -> datetime | None:
    """Parse a GitHub ISO timestamp ('...Z') into an aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


PROVIDER = GithubDoraSource()
