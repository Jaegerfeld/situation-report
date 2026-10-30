# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Writer gegen Reader (Beta Schnitt 1c, E4): der Generator schreibt
#   Provider-Rohdaten im Systemformat, `python -m sources fetch` liest sie
#   über das Replay ohne Netz, und das Ergebnis wird mit dem direkt
#   erzeugten Register verglichen — SLO (Prometheus, CSV) und Qualität
#   (SonarQube) exakt, DORA über GitLab exakt, über GitHub mit den
#   dokumentierten Näherungen (github_expected).
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from portfolio.dora_config import load_delivery
from portfolio.slo_config import load_slo
from sources.cli import main as cli_main
from testdata_generator.scenario import build_portfolio_scenario
from testdata_generator.source_inputs import (
    GITHUB_SAMPLE_CAP,
    GITHUB_WINDOW_DAYS,
    github_expected,
)
from testdata_generator.structure import structure_from_arts_spec

REF = date(2025, 6, 30)


@pytest.fixture(scope="module")
def room(tmp_path_factory):
    out = tmp_path_factory.mktemp("sources_room")
    messages: list[str] = []
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=messages.append,
                                     scale="s", stands=2)
    return out, paths, messages


def _fetch(cfg: Path, kind: str, out: Path) -> Path:
    def boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("network call during replay")
    with patch("sources.http._urlopen", side_effect=boom):
        assert cli_main(["fetch", "--kind", kind, "--config", str(cfg), "--output", str(out)]) == 0
    return out


def _slo_tuples(register):
    return [(r.service, r.slo, r.target_pct, r.sli_pct) for r in register.records]


class TestFilesAndFormats:
    def test_every_solution_has_its_sources_folder(self, room) -> None:
        out, paths, messages = room
        alpha, beta = paths["sources"]["alpha"], paths["sources"]["beta"]
        assert alpha["dora_provider"] == "github" and beta["dora_provider"] == "gitlab"
        assert sorted(alpha["configs"]) == ["dora", "quality", "slo", "slo_csv"]
        assert sorted(p.name for p in (out / "sources" / "alpha").iterdir()) == [
            "dora_sources.json", "github_responses.json", "prometheus_responses.json",
            "quality_sources.json", "slo.csv", "slo_sources.json", "slo_sources_csv.json",
            "sonarqube_responses.json"]
        assert (out / "sources" / "beta" / "gitlab_responses.json").is_file()
        assert any("Sources alpha" in m and "github" in m for m in messages)
        assert "## Sources (provider raw data, path 2)" in paths["readme"].read_text(encoding="utf-8")

    def test_raw_files_look_like_the_systems(self, room) -> None:
        out, _, _ = room
        prom = json.loads((out / "sources/alpha/prometheus_responses.json").read_text(encoding="utf-8"))
        assert prom["schema"] == 1 and prom["system"] == "prometheus"
        first = prom["responses"][0]
        assert first["path"] == "/api/v1/query" and "query" in first["params"]
        assert first["body"]["status"] == "success"
        assert first["body"]["data"]["resultType"] == "vector"
        assert len(first["body"]["data"]["result"][0]["value"]) == 2

        gh = json.loads((out / "sources/alpha/github_responses.json").read_text(encoding="utf-8"))
        deployments = next(e for e in gh["responses"] if e["path"].endswith("/deployments"))
        assert deployments["params"] == {"environment": "production"}
        assert all(d["created_at"].endswith("Z") for d in deployments["body"])
        repo_path = deployments["path"].rsplit("/deployments", 1)[0]
        statuses = [e for e in gh["responses"]
                    if e["path"].startswith(repo_path + "/deployments/")
                    and e["path"].endswith("/statuses")]
        assert len(statuses) == len(deployments["body"])
        assert statuses[0]["body"][0]["state"] in ("success", "failure")
        pulls = next(e for e in gh["responses"] if e["path"].endswith("/pulls"))
        assert {"created_at", "merged_at"} <= set(pulls["body"][0])

        gl = json.loads((out / "sources/beta/gitlab_responses.json").read_text(encoding="utf-8"))
        metrics = {e["params"]["metric"] for e in gl["responses"]}
        assert metrics == {"deployment_frequency", "lead_time_for_changes",
                           "change_failure_rate", "time_to_restore_service"}
        assert "%2F" in gl["responses"][0]["path"]       # project id quoted as GitLab wants it
        assert {"date", "value"} <= set(gl["responses"][0]["body"][0])

        sq = json.loads((out / "sources/alpha/sonarqube_responses.json").read_text(encoding="utf-8"))
        measures = {m["metric"]: m["value"] for m in sq["responses"][0]["body"]["component"]["measures"]}
        assert {"coverage", "sqale_rating", "critical_violations"} <= set(measures)

        csv_text = (out / "sources/alpha/slo.csv").read_text(encoding="utf-8")
        assert csv_text.startswith("service;slo;target_pct;sli_pct;window")


class TestWriterAgainstReader:
    def test_slo_via_prometheus_matches_the_register(self, room, tmp_path) -> None:
        out, paths, _ = room
        for key in ("alpha", "beta"):
            fetched = _fetch(paths["sources"][key]["configs"]["slo"], "slo", tmp_path / f"{key}_slo.json")
            got = load_slo(fetched)
            want = load_slo(paths[f"slo_{key}"])
            assert [(a, b) for a, b, _, _ in _slo_tuples(got)] == \
                [(a, b) for a, b, _, _ in _slo_tuples(want)]
            assert [r.target_pct for r in got.records] == pytest.approx(
                [r.target_pct for r in want.records])
            assert [r.sli_pct for r in got.records] == pytest.approx(
                [r.sli_pct for r in want.records])
            assert all(r.source.startswith("prometheus:") for r in got.records)

    def test_slo_via_csv_matches_the_register(self, room, tmp_path) -> None:
        out, paths, _ = room
        fetched = _fetch(paths["sources"]["alpha"]["configs"]["slo_csv"], "slo", tmp_path / "csv.json")
        got, want = load_slo(fetched), load_slo(paths["slo_alpha"])
        assert [(r.service, r.slo) for r in got.records] == [(r.service, r.slo) for r in want.records]
        assert [r.target_pct for r in got.records] == pytest.approx([r.target_pct for r in want.records])
        assert [r.sli_pct for r in got.records] == pytest.approx([r.sli_pct for r in want.records])

    def test_dora_via_gitlab_is_exact(self, room, tmp_path) -> None:
        out, paths, _ = room
        fetched = _fetch(paths["sources"]["beta"]["configs"]["dora"], "dora", tmp_path / "gl.json")
        got, want = load_delivery(fetched).dora, load_delivery(paths["dora_beta"]).dora
        assert [r.unit for r in got] == [r.unit for r in want]
        for g, w in zip(got, want):
            for field in ("deployments_per_day", "lead_time_hours",
                          "change_failure_rate_pct", "time_to_restore_hours"):
                assert getattr(g, field) == pytest.approx(getattr(w, field)), field
            assert g.source.startswith("gitlab:")

    def test_dora_via_github_matches_the_documented_derivation(self, room, tmp_path) -> None:
        out, paths, _ = room
        fetched = _fetch(paths["sources"]["alpha"]["configs"]["dora"], "dora", tmp_path / "gh.json")
        got, want = load_delivery(fetched).dora, load_delivery(paths["dora_alpha"]).dora
        assert [r.unit for r in got] == [r.unit for r in want]
        for g, w in zip(got, want):
            e = github_expected(w)
            assert g.deployments_per_day == pytest.approx(e.deployments_per_day)
            assert g.lead_time_hours == pytest.approx(e.lead_time_hours)
            assert g.time_to_restore_hours == pytest.approx(e.time_to_restore_hours)
            assert g.change_failure_rate_pct == pytest.approx(e.change_failure_rate_pct)
            # … and the derivation stays close to the register: exact rate,
            # exact medians, failure rate within one deployment of the sample.
            assert g.deployments_per_day == pytest.approx(w.deployments_per_day)
            assert g.lead_time_hours == pytest.approx(w.lead_time_hours, abs=0.1)
            sample = min(round(w.deployments_per_day * GITHUB_WINDOW_DAYS), GITHUB_SAMPLE_CAP)
            assert abs(g.change_failure_rate_pct - w.change_failure_rate_pct) <= 100 / sample + 0.1
            assert g.window == f"{GITHUB_WINDOW_DAYS}d"

    def test_quality_via_sonarqube_is_exact(self, room, tmp_path) -> None:
        out, paths, _ = room
        for key in ("alpha", "beta"):
            fetched = _fetch(paths["sources"][key]["configs"]["quality"], "quality",
                             tmp_path / f"{key}_q.json")
            got, want = load_delivery(fetched).quality, load_delivery(paths[f"dora_{key}"]).quality
            assert [(r.unit, r.coverage_pct, r.maintainability, r.critical_issues) for r in got] == \
                [(r.unit, r.coverage_pct, r.maintainability, r.critical_issues) for r in want]


class TestSolutionsWithoutRecords:
    def test_anchor_free_solution_gets_no_raw_data(self, tmp_path) -> None:
        messages: list[str] = []
        paths = build_portfolio_scenario(
            tmp_path, seed=5, reference=REF, log=messages.append, scale="s", stands=2,
            structure=structure_from_arts_spec("2,1,1"))
        gamma = paths["sources"]["gamma"]
        assert gamma["configs"] == {} and not gamma["dir"].exists()
        assert any("Sources gamma: no registers" in m for m in messages)
        assert "`gamma`: no registers" in paths["readme"].read_text(encoding="utf-8")
        # Beta (one ART) still carries the weak-source story -> raw data exists.
        assert paths["sources"]["beta"]["dora_provider"] == "gitlab"
