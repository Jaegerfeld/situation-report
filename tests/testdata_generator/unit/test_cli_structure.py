# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   CLI-Tests für die Struktur-Schalter des Portfolio-Szenarios (Beta
#   Schnitt 1a): --arts, --structure (Vorlage oder Datei), Schätzung und
#   Warnung auf der Konsole, Fehlerfälle über parser.error.
# =============================================================================

from __future__ import annotations

import json
import sys

import pytest

from testdata_generator.cli import main
from testdata_generator.structure import (
    TEMPLATE_LARGE,
    save_structure,
    structure_from_arts_spec,
    structure_template,
)


def _run(monkeypatch, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", ["testdata_generator", *argv])
    main()


class TestScenarioStructureFlags:
    def test_arts_spec_builds_that_many_arts(self, tmp_path, monkeypatch, capsys) -> None:
        out = tmp_path / "room"
        _run(monkeypatch, "--scenario", "portfolio", "--arts", "2,1s",
             "--scale", "s", "--output", str(out), "--seed", "5")
        assert len(list((out / "raw").glob("*_jira.json"))) == 3
        assert (out / "structure.json").is_file() and (out / "story.json").is_file()
        text = capsys.readouterr().out
        assert "Struktur: 1 Portfolio · 2 Solutions · 3 ARTs" in text
        assert "3 Jira-Exporte" in text

    def test_structure_file(self, tmp_path, monkeypatch) -> None:
        path = tmp_path / "s.json"
        save_structure(path, structure_from_arts_spec("1"))
        out = tmp_path / "room"
        _run(monkeypatch, "--scenario", "portfolio", "--structure", str(path),
             "--scale", "s", "--output", str(out))
        assert sorted(p.name for p in (out / "raw").glob("*_jira.json")) == ["Alpha-1_jira.json"]

    def test_structure_and_arts_exclude_each_other(self, tmp_path, monkeypatch, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, "--scenario", "portfolio", "--structure", "small",
                 "--arts", "2", "--output", str(tmp_path / "x"))
        assert exc.value.code == 2
        assert "exclude each other" in capsys.readouterr().err

    def test_bad_arts_spec_is_a_usage_error(self, tmp_path, monkeypatch, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, "--scenario", "portfolio", "--arts", "3,0",
                 "--output", str(tmp_path / "x"))
        assert exc.value.code == 2
        assert "at least one ART" in capsys.readouterr().err

    def test_missing_structure_file_is_a_usage_error(self, tmp_path, monkeypatch, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, "--scenario", "portfolio", "--structure",
                 str(tmp_path / "nope.json"), "--output", str(tmp_path / "x"))
        assert exc.value.code == 2
        assert "structure:" in capsys.readouterr().err

    def test_stands_flag_sets_the_series_length(self, tmp_path, monkeypatch, capsys) -> None:
        out = tmp_path / "room"
        _run(monkeypatch, "--scenario", "portfolio", "--arts", "1", "--stands", "3",
             "--scale", "s", "--output", str(out))
        assert len(list((out / "snapshots").glob("snapshot_??_*.json"))) == 3
        assert len(list((out / "deltas").glob("*.html"))) == 2
        assert "3 Stände, 2 Delta-Briefings" in capsys.readouterr().out

    def test_stands_out_of_range_is_a_usage_error(self, tmp_path, monkeypatch, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, "--scenario", "portfolio", "--arts", "1", "--stands", "1",
                 "--output", str(tmp_path / "x"))
        assert exc.value.code == 2
        assert "--stands must be 2..12" in capsys.readouterr().err

    def test_story_template_and_switches(self, tmp_path, monkeypatch, capsys) -> None:
        out = tmp_path / "room"
        _run(monkeypatch, "--scenario", "portfolio", "--arts", "2,1", "--story", "calm",
             "--event", "E6=on", "--scale", "s", "--output", str(out))
        data = json.loads((out / "story.json").read_text(encoding="utf-8"))
        assert data["template"] == "calm" and data["stands"] == 3     # calm suggests 3 stands
        enabled = {e["id"] for e in data["events"] if e["enabled"]}
        assert enabled == {"E6"}
        text = capsys.readouterr().out
        assert "Geschichte: calm, Schalter E6=on" in text and "3 Stände" in text

    def test_bad_event_switch_is_a_usage_error(self, tmp_path, monkeypatch, capsys) -> None:
        with pytest.raises(SystemExit) as exc:
            _run(monkeypatch, "--scenario", "portfolio", "--arts", "1", "--event", "E42=on",
                 "--output", str(tmp_path / "x"))
        assert exc.value.code == 2
        assert "unknown event id" in capsys.readouterr().err

    def test_large_template_warns_before_building(self, tmp_path, monkeypatch, capsys) -> None:
        # Do not build 49 ARTs in a unit test: stop right after the estimate.
        import testdata_generator.scenario as scenario

        calls: list[dict] = []
        monkeypatch.setattr(scenario, "build_portfolio_scenario",
                            lambda *a, **kw: calls.append(kw))
        _run(monkeypatch, "--scenario", "portfolio", "--structure", TEMPLATE_LARGE,
             "--output", str(tmp_path / "x"))
        captured = capsys.readouterr()
        assert "WARNUNG" in captured.err and "ARTs" in captured.err
        assert "5 Portfolios" in captured.out
        assert len(calls) == 1
        assert calls[0]["structure"].n_arts == structure_template(TEMPLATE_LARGE).n_arts
