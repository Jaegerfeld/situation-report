# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests für das Replay der Quellen (sources/replay.py, Beta Schnitt 1c):
#   Laden und Prüfen der Datei, Treffer über Pfad und Kennparameter,
#   Fehlmeldung, Bedienung von get_json ohne Netz, Aktivierung über die
#   Config in fetch_records, Pfadauflösung relativ zur Config-Datei,
#   as_of-Verankerung der Fenster bei GitHub und GitLab.
# =============================================================================

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from sources.base import KIND_DORA, KIND_SLO
from sources.cli import fetch_records
from sources.cli import main as cli_main
from sources.http import get_json
from sources.providers.github_dora import PROVIDER as GITHUB
from sources.providers.gitlab_dora import PROVIDER as GITLAB
from sources.providers.prometheus import PROVIDER as PROMETHEUS
from sources.replay import Replay, activated, active, replay_from_config, resolve_relative


def _write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _no_network():
    def boom(*_a, **_k):  # pragma: no cover - must never run
        raise AssertionError("network call during replay")
    return patch("sources.http._urlopen", side_effect=boom)


class TestReplayFile:
    def test_lookup_matches_path_and_params_ignoring_others(self, tmp_path) -> None:
        path = _write(tmp_path / "r.json", {"schema": 1, "system": "demo", "responses": [
            {"path": "/api/v1/query", "params": {"query": "up"}, "body": {"a": 1}},
            {"path": "/api/v1/query", "params": {"query": "down"}, "body": {"a": 2}},
            {"path": "/plain", "body": [1, 2]}]})
        replay = Replay.load(path)
        assert replay.system == "demo"
        assert replay.lookup("https://h/api/v1/query?query=down&time=123") == {"a": 2}
        assert replay.lookup("https://h/api/v1/query?query=up") == {"a": 1}
        assert replay.lookup("https://h/plain?anything=1") == [1, 2]

    def test_lookup_returns_a_copy(self, tmp_path) -> None:
        replay = Replay.load(_write(tmp_path / "r.json", {"schema": 1, "responses": [
            {"path": "/x", "body": {"list": [1]}}]}))
        first = replay.lookup("https://h/x")
        first["list"].append(2)
        assert replay.lookup("https://h/x") == {"list": [1]}

    def test_miss_names_the_request(self, tmp_path) -> None:
        replay = Replay.load(_write(tmp_path / "r.json", {"schema": 1, "system": "github",
                                                          "responses": []}))
        with pytest.raises(RuntimeError, match="no recorded response for /repos/a/b\\?x=1"):
            replay.lookup("https://h/repos/a/b?x=1")

    @pytest.mark.parametrize("data", [
        {"schema": 2, "responses": []},
        {"schema": 1, "responses": {}},
        {"schema": 1, "responses": [{"body": 1}]},
        {"schema": 1, "responses": [{"path": "/x", "body": 1, "params": []}]},
    ])
    def test_rejects_malformed_files(self, tmp_path, data) -> None:
        with pytest.raises(RuntimeError, match="Replay file"):
            Replay.load(_write(tmp_path / "bad.json", data))

    def test_missing_and_invalid_json(self, tmp_path) -> None:
        with pytest.raises(RuntimeError, match="cannot be read"):
            Replay.load(tmp_path / "nope.json")
        (tmp_path / "x.json").write_text("{", encoding="utf-8")
        with pytest.raises(RuntimeError, match="not valid JSON"):
            Replay.load(tmp_path / "x.json")


class TestActivation:
    def test_get_json_is_served_without_network(self, tmp_path) -> None:
        replay = Replay.load(_write(tmp_path / "r.json", {"schema": 1, "responses": [
            {"path": "/api/v1/query", "body": {"data": {"result": [{"value": [0, "99.5"]}]}}}]}))
        assert active() is None
        with _no_network(), activated(replay):
            assert active() is replay
            assert get_json("https://p.invalid/api/v1/query?query=x", {}, "P")["data"]
            [record] = PROMETHEUS.fetch(KIND_SLO, {
                "base_url": "https://p.invalid",
                "services": [{"service": "S", "slo": "avail", "target_pct": 99.0,
                              "sli_query": "x"}]}, lambda m: None)
        assert record.sli_pct == 99.5
        assert active() is None

    def test_activated_none_is_a_no_op(self) -> None:
        with activated(None):
            assert active() is None

    def test_fetch_records_activates_replay_from_config(self, tmp_path) -> None:
        _write(tmp_path / "prom.json", {"schema": 1, "responses": [
            {"path": "/api/v1/query", "body": {"data": {"result": [{"value": [0, "98"]}]}}}]})
        cfg = {"provider": "prometheus", "base_url": "https://p.invalid",
               "replay": "prom.json",
               "services": [{"service": "S", "slo": "a", "target_pct": 99.0, "sli_query": "q"}]}
        lines: list[str] = []
        with _no_network():
            records = fetch_records(KIND_SLO, [cfg], log=lines.append, base_dir=tmp_path)
        assert records[0]["sli_pct"] == 98.0
        assert any("Replay, kein Netz" in li for li in lines)

    def test_resolve_relative_prefers_cwd_then_config_dir(self, tmp_path, monkeypatch) -> None:
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / "data.csv").write_text("x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert resolve_relative("data.csv", cfg_dir) == cfg_dir / "data.csv"
        (tmp_path / "data.csv").write_text("y", encoding="utf-8")
        assert resolve_relative("data.csv", cfg_dir) == Path("data.csv")
        assert resolve_relative("missing.csv", cfg_dir) == Path("missing.csv")
        assert replay_from_config({}, cfg_dir) is None

    def test_cli_resolves_csv_path_relative_to_the_config(self, tmp_path, monkeypatch, capsys) -> None:
        room = tmp_path / "room"
        room.mkdir()
        (room / "slo.csv").write_text("service;slo;target_pct;sli_pct\nS;a;99,5;99,7\n",
                                      encoding="utf-8")
        cfg = _write(room / "slo_sources.json",
                     {"sources": [{"provider": "csv", "path": "slo.csv"}]})
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        out = tmp_path / "out.json"
        assert cli_main(["fetch", "--kind", "slo", "--config", str(cfg), "--output", str(out)]) == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["records"][0]["sli_pct"] == 99.7
        assert "1 slo records" in capsys.readouterr().out


class TestAsOf:
    def test_github_counts_deployments_as_of_the_configured_day(self, tmp_path) -> None:
        base = "/repos/demo/alpha-1"
        replay = Replay.load(_write(tmp_path / "gh.json", {"schema": 1, "responses": [
            {"path": f"{base}/deployments", "body": [
                {"id": 1, "created_at": "2025-06-20T10:00:00Z"},
                {"id": 2, "created_at": "2025-06-10T10:00:00Z"}]},
            {"path": f"{base}/deployments/1/statuses", "body": [{"state": "success"}]},
            {"path": f"{base}/deployments/2/statuses", "body": [{"state": "failure"}]},
            {"path": f"{base}/pulls", "body": []},
            {"path": f"{base}/issues", "body": []}]}))
        cfg = {"owner": "demo", "repo": "alpha-1", "window_days": 30, "base_url": "https://g.invalid"}
        with _no_network(), activated(replay):
            [anchored] = GITHUB.fetch(KIND_DORA, {**cfg, "as_of": "2025-06-30"}, lambda m: None)
            [today] = GITHUB.fetch(KIND_DORA, cfg, lambda m: None)
        assert anchored.deployments_per_day == pytest.approx(2 / 30, abs=1e-3)
        assert anchored.change_failure_rate_pct == 50.0
        assert today.deployments_per_day == 0.0   # 2025 lies outside a window ending now
        assert datetime.now(UTC).year >= 2026

    def test_github_rejects_bad_as_of(self) -> None:
        with pytest.raises(RuntimeError, match="'as_of' must be an ISO date"):
            GITHUB.fetch(KIND_DORA, {"owner": "a", "repo": "b", "as_of": "gestern"}, lambda m: None)

    def test_gitlab_sends_the_anchored_start_date(self, tmp_path) -> None:
        seen: list[str] = []
        real = Replay.load(_write(tmp_path / "gl.json", {"schema": 1, "responses": [
            {"path": "/api/v4/projects/p/dora/metrics", "body": [{"date": "2025-06-29", "value": 2}]}]}))
        original = real.lookup

        def spy(url: str):
            seen.append(url)
            return original(url)

        real.lookup = spy  # type: ignore[method-assign]
        with _no_network(), activated(real):
            [record] = GITLAB.fetch(KIND_DORA, {"base_url": "https://gl.invalid", "project_id": "p",
                                                 "window_days": 30, "as_of": "2025-06-30"},
                                    lambda m: None)
        assert all("start_date=2025-05-31" in u for u in seen) and len(seen) == 4
        assert record.deployments_per_day == 2.0
        with pytest.raises(RuntimeError, match="'as_of' must be an ISO date"):
            GITLAB.fetch(KIND_DORA, {"base_url": "https://gl.invalid", "project_id": "p",
                                     "as_of": "x"}, lambda m: None)
