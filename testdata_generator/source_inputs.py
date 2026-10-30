# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Provider-Rohdaten des Demo-Datenraums (Beta, Schnitt 1c, Entscheidung
#   E4 vom 26.10.2026): Für jede Solution schreibt der Generator, was die
#   echten Systeme liefern würden — Prometheus-Instant-Query-Antworten,
#   GitHub-Deployments/-Statuses/-PRs/-Issues, GitLab-DORA-Tageswerte,
#   SonarQube-Measures und eine SLO-CSV — als Replay-Dateien im Format des
#   jeweiligen Systems, dazu die passenden `sources`-Configs. Damit läuft
#   `python -m sources fetch` im Datenraum ohne Netz, und ein Test
#   vergleicht, was der Provider liest, mit dem direkt erzeugten Register.
#
#   Die Rohdaten werden aus den Registern abgeleitet (nicht umgekehrt):
#   die Register bleiben die Wahrheit der Geschichte; die Rohdaten sind so
#   gebaut, dass der Provider daraus dieselben Werte rechnet. Wo ein
#   Provider nur näherungsweise rechnet (GitHub leitet DORA aus Zählungen
#   ab), nennt `github_expected()` die Werte, die er liefern wird.
# =============================================================================

from __future__ import annotations

import csv
import json
import re
import urllib.parse
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from portfolio.dora_config import DeliveryRegister
from portfolio.slo_config import SloRegister
from sources.base import DoraRecord
from sources.replay import REPLAY_SCHEMA

from .i18n import DEFAULT_LANG
from .i18n import t as _t
from .structure import PortfolioSpec

#: Fictitious hosts — `.invalid` is reserved and never resolves (RFC 2606).
HOSTS = {
    "prometheus": "https://prometheus.demo.invalid",
    "github": "https://api.github.demo.invalid",
    "gitlab": "https://gitlab.demo.invalid",
    "sonarqube": "https://sonarqube.demo.invalid",
}
GITHUB_OWNER = "demo"
#: 100 days make every demo deployment frequency an integer count
#: (0.02/day -> 2, 1.4/day -> 140); the provider computes count / window.
GITHUB_WINDOW_DAYS = 100
#: The provider samples at most this many deployments for the failure rate.
GITHUB_SAMPLE_CAP = 50
GITLAB_WINDOW_DAYS = 30
INCIDENT_LABEL = "incident"
_RATING_CODES = {"A": "1.0", "B": "2.0", "C": "3.0", "D": "4.0", "E": "5.0"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unit"


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _end_of_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=UTC)


def _write_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _replay(system: str, responses: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": REPLAY_SCHEMA, "system": system,
            "note": f"Recorded responses in {system}'s own format; served by "
                    f"sources.replay instead of HTTP.",
            "responses": responses}


# --- Prometheus + CSV (SLO) ---------------------------------------------------

def _prometheus_inputs(slo: SloRegister, reference: date) -> tuple[list[dict], list[dict]]:
    ts = int(_end_of_day(reference).timestamp())
    responses: list[dict] = []
    services: list[dict] = []
    for r in slo.records:
        query = f"avg_over_time(sli:{_slug(r.service)}:ratio[{r.window or '30d'}])"
        result = ([{"metric": {"__name__": "sli", "service": r.service},
                    "value": [ts, str(r.sli_pct)]}]
                  if r.sli_pct is not None else [])
        responses.append({"path": "/api/v1/query", "params": {"query": query},
                          "body": {"status": "success",
                                   "data": {"resultType": "vector", "result": result}}})
        services.append({"service": r.service, "slo": r.slo,
                         "target_pct": r.target_pct, "sli_query": query, "scale": 1})
    return responses, services


def _write_slo_csv(path: Path, slo: SloRegister) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["service", "slo", "target_pct", "sli_pct", "window"])
        for r in slo.records:
            writer.writerow([r.service, r.slo, f"{r.target_pct:g}".replace(".", ","),
                             "" if r.sli_pct is None else f"{r.sli_pct:g}".replace(".", ","),
                             r.window or "30d"])
    return path


# --- GitHub (DORA, derived) ---------------------------------------------------

def github_expected(record: DoraRecord, window_days: int = GITHUB_WINDOW_DAYS,
                    cap: int = GITHUB_SAMPLE_CAP) -> DoraRecord:
    """
    The values the GitHub provider will derive from the written raw data.

    Deployments per day come out exact whenever ``rate × window`` is an
    integer (true for every demo anchor at 100 days); the failure rate is a
    count over at most ``cap`` deployments, so small units show coarse
    steps (1 of 5 = 20 %); lead time and restore time are medians of three
    recorded durations around the register value and come out exact.
    """
    n = round((record.deployments_per_day or 0.0) * window_days)
    sample = min(n, cap)
    cfr: float | None = None
    if record.change_failure_rate_pct is not None and sample:
        failed = round(record.change_failure_rate_pct / 100 * sample)
        cfr = round(failed / sample * 100, 1)
    return DoraRecord(
        unit=record.unit,
        deployments_per_day=round(n / window_days, 3),
        lead_time_hours=(None if record.lead_time_hours is None
                         else round(record.lead_time_hours, 1)),
        change_failure_rate_pct=cfr,
        time_to_restore_hours=(None if record.time_to_restore_hours is None
                               else round(record.time_to_restore_hours, 1)),
        window=f"{window_days}d",
    )


def _github_inputs(dora: DeliveryRegister, reference: date) -> tuple[list[dict], list[dict]]:
    as_of = _end_of_day(reference)
    window = timedelta(days=GITHUB_WINDOW_DAYS)
    responses: list[dict] = []
    sources: list[dict] = []
    next_id = 1000
    for r in dora.dora:
        repo = _slug(r.unit)
        base = f"/repos/{GITHUB_OWNER}/{repo}"
        n = round((r.deployments_per_day or 0.0) * GITHUB_WINDOW_DAYS)
        spacing = window / (n + 1)
        deployments = []
        for i in range(n):
            next_id += 1
            deployments.append({"id": next_id, "environment": "production",
                                "ref": "main", "task": "deploy",
                                "created_at": _iso_z(as_of - spacing * (i + 1))})
        responses.append({"path": f"{base}/deployments",
                          "params": {"environment": "production"}, "body": deployments})
        sample = min(n, GITHUB_SAMPLE_CAP)
        failed = (round(r.change_failure_rate_pct / 100 * sample)
                  if r.change_failure_rate_pct is not None and sample else 0)
        for i, dep in enumerate(deployments):
            state = "failure" if i < failed else "success"
            responses.append({"path": f"{base}/deployments/{dep['id']}/statuses",
                              "body": [{"state": state, "environment": "production",
                                        "created_at": dep["created_at"]}]})
        pulls = []
        if r.lead_time_hours is not None:
            for j, factor in enumerate((0.9, 1.0, 1.1)):
                merged = as_of - timedelta(hours=1 + j)
                created = merged - timedelta(hours=r.lead_time_hours * factor)
                pulls.append({"number": 100 + j, "state": "closed",
                              "created_at": _iso_z(created), "merged_at": _iso_z(merged)})
        responses.append({"path": f"{base}/pulls", "params": {"state": "closed"},
                          "body": pulls})
        issues = []
        if r.time_to_restore_hours is not None:
            for j, factor in enumerate((0.9, 1.0, 1.1)):
                closed = as_of - timedelta(hours=1 + j)
                created = closed - timedelta(hours=r.time_to_restore_hours * factor)
                issues.append({"number": 200 + j, "state": "closed",
                               "labels": [{"name": INCIDENT_LABEL}],
                               "created_at": _iso_z(created), "closed_at": _iso_z(closed)})
        responses.append({"path": f"{base}/issues",
                          "params": {"labels": INCIDENT_LABEL, "state": "closed"},
                          "body": issues})
        sources.append({"provider": "github", "owner": GITHUB_OWNER, "repo": repo,
                        "unit": r.unit, "window_days": GITHUB_WINDOW_DAYS,
                        "as_of": reference.isoformat(), "environment": "production",
                        "incident_label": INCIDENT_LABEL,
                        "max_deployments": GITHUB_SAMPLE_CAP,
                        "base_url": HOSTS["github"], "replay": "github_responses.json"})
    return responses, sources


# --- GitLab (DORA, native API) -------------------------------------------------

_GITLAB_METRICS = (("deployment_frequency", "deployments_per_day", 1.0),
                   ("lead_time_for_changes", "lead_time_hours", 3600.0),
                   ("change_failure_rate", "change_failure_rate_pct", 1.0),
                   ("time_to_restore_service", "time_to_restore_hours", 3600.0))


def _gitlab_inputs(dora: DeliveryRegister, reference: date) -> tuple[list[dict], list[dict]]:
    responses: list[dict] = []
    sources: list[dict] = []
    days = [reference - timedelta(days=d) for d in (2, 1, 0)]
    for r in dora.dora:
        project_id = f"{GITHUB_OWNER}/{_slug(r.unit)}"
        path = f"/api/v4/projects/{urllib.parse.quote(project_id, safe='')}/dora/metrics"
        for metric, field_name, factor in _GITLAB_METRICS:
            value = getattr(r, field_name)
            native = None if value is None else value * factor
            responses.append({"path": path, "params": {"metric": metric},
                              "body": [{"date": d.isoformat(), "value": native}
                                       for d in days]})
        sources.append({"provider": "gitlab", "base_url": HOSTS["gitlab"],
                        "project_id": project_id, "unit": r.unit,
                        "window_days": GITLAB_WINDOW_DAYS,
                        "as_of": reference.isoformat(), "replay": "gitlab_responses.json"})
    return responses, sources


# --- SonarQube (quality) ---------------------------------------------------------

def _sonarqube_inputs(dora: DeliveryRegister) -> tuple[list[dict], list[dict]]:
    responses: list[dict] = []
    components: list[dict] = []
    for q in dora.quality:
        component = f"{GITHUB_OWNER}:{_slug(q.unit)}"
        measures = []
        if q.coverage_pct is not None:
            measures.append({"metric": "coverage", "value": f"{q.coverage_pct:g}"})
        code = _RATING_CODES.get(str(q.maintainability).upper())
        if code:
            measures.append({"metric": "sqale_rating", "value": code})
        if q.critical_issues is not None:
            measures.append({"metric": "critical_violations", "value": str(q.critical_issues)})
            measures.append({"metric": "violations", "value": str(q.critical_issues * 9 + 3)})
        responses.append({"path": "/api/measures/component",
                          "params": {"component": component},
                          "body": {"component": {"key": component, "name": q.unit,
                                                 "qualifier": "TRK", "measures": measures}}})
        components.append({"component": component, "unit": q.unit})
    return responses, components


# --- Entry point -------------------------------------------------------------------

def write_source_inputs(
    out: Path,
    spec: PortfolioSpec,
    registers: dict[str, dict[str, object]],
    reference: date,
    log: Callable[[str], None] = print,
    lang: str = DEFAULT_LANG,
) -> dict[str, dict[str, Any]]:
    """
    Write the provider raw data and source configs of every solution into
    ``out/sources/<solution_key>/``.

    Per solution (only for registers that carry records):
      slo      -> prometheus_responses.json + slo_sources.json,
                  slo.csv + slo_sources_csv.json (the manual way)
      dora     -> even positions: github_responses.json + dora_sources.json
                  odd positions:  gitlab_responses.json + dora_sources.json
      quality  -> sonarqube_responses.json + quality_sources.json

    Returns {solution_key: {"dir": Path, "configs": {kind: Path}, "raw": [Path],
    "dora_provider": "github"|"gitlab"|None}}.
    """
    result: dict[str, dict[str, Any]] = {}
    for index, solution in enumerate(spec.solutions):
        regs = registers.get(solution.key, {})
        slo = regs.get("slo")
        dora = regs.get("dora")
        sdir = out / "sources" / solution.key
        info: dict[str, Any] = {"dir": sdir, "configs": {}, "raw": [], "dora_provider": None}
        if isinstance(slo, SloRegister) and slo.records:
            sdir.mkdir(parents=True, exist_ok=True)
            responses, services = _prometheus_inputs(slo, reference)
            info["raw"].append(_write_json(sdir / "prometheus_responses.json",
                                           _replay("prometheus", responses)))
            info["configs"]["slo"] = _write_json(sdir / "slo_sources.json", {"sources": [
                {"provider": "prometheus", "base_url": HOSTS["prometheus"],
                 "window": slo.records[0].window or "30d",
                 "replay": "prometheus_responses.json", "services": services}]})
            info["raw"].append(_write_slo_csv(sdir / "slo.csv", slo))
            info["configs"]["slo_csv"] = _write_json(sdir / "slo_sources_csv.json", {
                "sources": [{"provider": "csv", "path": "slo.csv"}]})
        if isinstance(dora, DeliveryRegister) and dora.dora:
            sdir.mkdir(parents=True, exist_ok=True)
            if index % 2 == 0:
                responses, sources = _github_inputs(dora, reference)
                info["raw"].append(_write_json(sdir / "github_responses.json",
                                               _replay("github", responses)))
                info["dora_provider"] = "github"
            else:
                responses, sources = _gitlab_inputs(dora, reference)
                info["raw"].append(_write_json(sdir / "gitlab_responses.json",
                                               _replay("gitlab", responses)))
                info["dora_provider"] = "gitlab"
            info["configs"]["dora"] = _write_json(sdir / "dora_sources.json",
                                                  {"sources": sources})
        if isinstance(dora, DeliveryRegister) and dora.quality:
            sdir.mkdir(parents=True, exist_ok=True)
            responses, components = _sonarqube_inputs(dora)
            info["raw"].append(_write_json(sdir / "sonarqube_responses.json",
                                           _replay("sonarqube", responses)))
            info["configs"]["quality"] = _write_json(sdir / "quality_sources.json", {
                "sources": [{"provider": "sonarqube", "base_url": HOSTS["sonarqube"],
                             "replay": "sonarqube_responses.json",
                             "components": components}]})
        if info["configs"]:
            kinds = ", ".join(sorted(info["configs"]))
            dora = (_t("rm.sources_dora", lang, provider=info["dora_provider"])
                    if info["dora_provider"] else "")
            log(_t("log.sources", lang, key=solution.key, kinds=kinds, dora=dora))
        else:
            log(_t("log.sources_none", lang, key=solution.key))
        result[solution.key] = info
    return result
