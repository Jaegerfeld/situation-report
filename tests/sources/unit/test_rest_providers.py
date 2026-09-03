# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der REST-Referenz-Provider (C1/C2): Prometheus (Query-URL,
#   Skalierung, leere Ergebnisse), GitHub (DORA-Ableitung: Fenster-Filter,
#   CFR aus Deployment-Statuses, Median-Lead-Time, Incident-MTTR),
#   GitLab (vier Metriken, Sekunden→Stunden, PRIVATE-TOKEN) und SonarQube
#   (Basic-Auth, Rating-Mapping). Alle HTTP-Aufrufe gemockt; zusätzlich
#   der 401-Freigabe-Hinweis des gemeinsamen HTTP-Bausteins.
# =============================================================================

from __future__ import annotations

import io
import json
import urllib.error
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from sources.base import KIND_DORA, KIND_QUALITY, KIND_SLO
from sources.providers.github_dora import PROVIDER as GITHUB
from sources.providers.gitlab_dora import PROVIDER as GITLAB
from sources.providers.prometheus import PROVIDER as PROMETHEUS
from sources.providers.sonarqube import PROVIDER as SONARQUBE

_NOW = datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _mock_responses(responses: list):
    """Patch sources.http._urlopen; responses served in call order."""
    calls: list = []

    def fake_urlopen(req, timeout=0):
        calls.append(req)
        body = json.dumps(responses[len(calls) - 1]).encode("utf-8")

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()

        return _Resp(body)

    with patch("sources.http._urlopen", side_effect=fake_urlopen):
        yield calls


class TestPrometheus:
    def test_query_scaling_and_source_label(self) -> None:
        resp = {"data": {"result": [{"value": [0, "0.9995"]}]}}
        cfg = {"base_url": "https://prom.example.com",
               "services": [{"service": "API", "slo": "avail",
                             "target_pct": 99.9,
                             "sli_query": "avg_over_time(up[30d])",
                             "scale": 100}]}
        with _mock_responses([resp]) as calls:
            [record] = PROMETHEUS.fetch(KIND_SLO, cfg, lambda m: None)
        assert record.sli_pct == pytest.approx(99.95)
        assert record.source == "prometheus:prom.example.com"
        assert "/api/v1/query?" in calls[0].get_full_url()
        assert "avg_over_time" in calls[0].get_full_url()

    def test_empty_result_yields_none_sli(self) -> None:
        cfg = {"base_url": "https://p.example.com",
               "services": [{"service": "A", "slo": "x", "target_pct": 99,
                             "sli_query": "q"}]}
        with _mock_responses([{"data": {"result": []}}]):
            [record] = PROMETHEUS.fetch(KIND_SLO, cfg, lambda m: None)
        assert record.sli_pct is None

    def test_requires_base_url_and_query(self) -> None:
        with pytest.raises(RuntimeError, match="base_url"):
            PROMETHEUS.fetch(KIND_SLO, {}, lambda m: None)
        with pytest.raises(RuntimeError, match="sli_query"):
            PROMETHEUS.fetch(KIND_SLO, {
                "base_url": "https://p", "services": [{"service": "A"}]},
                lambda m: None)


class TestGithub:
    def _responses(self) -> list:
        deployments = [
            {"id": 1, "created_at": _iso(_NOW - timedelta(days=2))},
            {"id": 2, "created_at": _iso(_NOW - timedelta(days=5))},
            {"id": 3, "created_at": _iso(_NOW - timedelta(days=90))},  # alt
        ]
        status_ok = [{"state": "success"}]
        status_fail = [{"state": "failure"}]
        pulls = [
            {"created_at": _iso(_NOW - timedelta(days=4)),
             "merged_at": _iso(_NOW - timedelta(days=3))},          # 24 h
            {"created_at": _iso(_NOW - timedelta(days=10)),
             "merged_at": _iso(_NOW - timedelta(days=7))},          # 72 h
            {"created_at": _iso(_NOW - timedelta(days=9)),
             "merged_at": None},                                    # nicht gemergt
        ]
        issues = [
            {"created_at": _iso(_NOW - timedelta(days=3)),
             "closed_at": _iso(_NOW - timedelta(days=2, hours=18))},  # 6 h
            {"created_at": _iso(_NOW - timedelta(days=2)),
             "closed_at": _iso(_NOW - timedelta(days=1)),
             "pull_request": {}},                                   # PR: raus
        ]
        return [deployments, status_ok, status_fail, pulls, issues]

    def test_derives_all_four_metrics(self) -> None:
        cfg = {"owner": "acme", "repo": "shop", "window_days": 30}
        with _mock_responses(self._responses()) as calls:
            [record] = GITHUB.fetch(KIND_DORA, cfg, lambda m: None)
        # 2 Deployments im Fenster (das dritte ist 90 Tage alt).
        assert record.deployments_per_day == pytest.approx(2 / 30, abs=1e-3)
        # 1 von 2 Status failure -> 50 %.
        assert record.change_failure_rate_pct == 50.0
        # Median aus 24 h und 72 h = 48 h.
        assert record.lead_time_hours == 48.0
        # Ein echtes Incident-Issue: 6 h.
        assert record.time_to_restore_hours == 6.0
        assert record.source == "github:acme/shop"
        assert "environment=production" in calls[0].get_full_url()
        assert "labels=incident" in calls[4].get_full_url()

    def test_requires_owner_and_repo(self) -> None:
        with pytest.raises(RuntimeError, match="owner"):
            GITHUB.fetch(KIND_DORA, {"repo": "x"}, lambda m: None)


class TestGitlab:
    def test_four_calls_units_and_token_header(self, monkeypatch) -> None:
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
        daily = [{"value": 2}, {"value": 4}]
        lead = [{"value": 7200}, {"value": None}]
        with _mock_responses([daily, lead, daily, lead]) as calls:
            [record] = GITLAB.fetch(KIND_DORA, {
                "base_url": "https://gitlab.example.com",
                "project_id": "group/proj", "unit": "ART X"},
                lambda m: None)
        assert len(calls) == 4
        assert record.deployments_per_day == 3.0
        assert record.lead_time_hours == pytest.approx(2.0)  # 7200 s -> h
        assert record.unit == "ART X"
        assert calls[0].get_header("Private-token") == "glpat-test"
        assert "group%2Fproj" in calls[0].get_full_url()

    def test_requires_base_url_and_project(self) -> None:
        with pytest.raises(RuntimeError, match="project_id"):
            GITLAB.fetch(KIND_DORA, {"base_url": "https://g"}, lambda m: None)


class TestSonarqube:
    def test_measures_mapping_and_basic_auth(self, monkeypatch) -> None:
        monkeypatch.setenv("SONAR_TOKEN", "squ_test")
        resp = {"component": {"measures": [
            {"metric": "coverage", "value": "72.4"},
            {"metric": "sqale_rating", "value": "3.0"},
            {"metric": "critical_violations", "value": "5"},
        ]}}
        with _mock_responses([resp]) as calls:
            [record] = SONARQUBE.fetch(KIND_QUALITY, {
                "base_url": "https://sonar.example.com",
                "components": [{"component": "acme:shop", "unit": "Shop"}]},
                lambda m: None)
        assert record.coverage_pct == 72.4
        assert record.maintainability == "C"
        assert record.critical_issues == 5
        header = calls[0].get_header("Authorization")
        assert header and header.startswith("Basic ")

    def test_missing_measures_become_none(self) -> None:
        with _mock_responses([{"component": {"measures": []}}]):
            [record] = SONARQUBE.fetch(KIND_QUALITY, {
                "base_url": "https://s", "components": [{"component": "x"}]},
                lambda m: None)
        assert record.coverage_pct is None
        assert record.critical_issues is None


class TestHttpErrors:
    def test_403_points_to_approval_and_file_fallback(self) -> None:
        def raise_403(req, timeout=0):
            raise urllib.error.HTTPError(req.get_full_url(), 403, "nope", {},
                                         io.BytesIO(b""))
        with patch("sources.http._urlopen", side_effect=raise_403):
            with pytest.raises(RuntimeError) as exc:
                PROMETHEUS.fetch(KIND_SLO, {
                    "base_url": "https://p.example.com",
                    "services": [{"service": "A", "slo": "x",
                                  "target_pct": 99, "sli_query": "q"}]},
                    lambda m: None)
        msg = str(exc.value)
        assert "approval" in msg and "file source" in msg
