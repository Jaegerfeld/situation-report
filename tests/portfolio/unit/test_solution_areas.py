# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Solution-Area-Registers (P5): Parsen und Fehlerpfade (zwei
#   Seiten je Naht, Schlüssel-Anlass), Nähte und Rekurrenz (zweimal
#   hervorgehoben, ab dreimal Signal), Rendering mit roter Rekurrenz-Zelle
#   und Legende, Collector mit Fehlerbehandlung, Konferenzmappe, Snapshot
#   und Delta (dritte Area kommt neu), Einseiter (Zeile, Entscheidungspunkt,
#   BLUF), Config-Roundtrip, Datenquellen-Dialog.
# =============================================================================

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from portfolio.aggregator import _collect_solution_areas
from portfolio.solution_areas_config import (
    AREA_ACTIVE,
    AREA_CLOSED,
    RECURRENCE_HIGHLIGHT,
    RECURRENCE_SIGNAL,
    SolutionArea,
    SolutionAreaRegister,
    load_solution_areas,
    parse_solution_areas,
    save_solution_areas,
    seams,
)
from portfolio.solution_config import Member, SolutionConfig, parse_solution_config, to_dict
from portfolio.summary import _OVERDUE_COLOR, render_solution_areas_html

REF = date(2026, 10, 13)


def _area(aid: str, topic: str, parts: list[str], opened: int, closed: int | None = None) -> SolutionArea:
    return SolutionArea(aid, f"Area {aid}", topic, parts, REF - timedelta(days=opened),
                        (REF - timedelta(days=closed)) if closed is not None else None)


class TestParse:
    def test_minimal_and_derived(self) -> None:
        reg = parse_solution_areas({"schema": 1, "areas": [
            {"id": "SA-1", "title": "T", "topic": "env", "participants": ["A", "B"],
             "opened_on": "2026-09-01"}]})
        a = reg.areas[0]
        assert a.status == AREA_ACTIVE and a.seam == ("A", "B")
        assert a.duration_days(date(2026, 9, 11)) == 10

    def test_closed_status_and_duration(self) -> None:
        a = _area("SA-1", "env", ["B", "A"], opened=30, closed=10)
        assert a.status == AREA_CLOSED and a.duration_days(REF) == 20 and a.seam == ("A", "B")

    @pytest.mark.parametrize("entry,match", [
        ({"id": "", "title": "T", "topic": "x", "participants": ["A", "B"]}, "non-empty 'id'"),
        ({"id": "S", "title": "", "topic": "x", "participants": ["A", "B"]}, "'title' and 'topic'"),
        ({"id": "S", "title": "T", "topic": "x", "participants": ["A"]}, "two distinct participants"),
        ({"id": "S", "title": "T", "topic": "x", "participants": ["A", "A"]}, "two distinct participants"),
        ({"id": "S", "title": "T", "topic": "x", "participants": ["A", "B"], "opened_on": "gestern"}, "YYYY-MM-DD"),
        ({"id": "S", "title": "T", "topic": "x", "participants": ["A", "B"], "opened_on": "2026-05-01",
          "closed_on": "2026-04-01"}, "closed before"),
    ])
    def test_rejects_structural_errors(self, entry, match) -> None:
        with pytest.raises(ValueError, match=match):
            parse_solution_areas({"areas": [entry]})

    def test_duplicate_and_shape(self) -> None:
        with pytest.raises(ValueError, match="Duplicate"):
            parse_solution_areas({"areas": [
                {"id": "S", "title": "T", "topic": "x", "participants": ["A", "B"]},
                {"id": "S", "title": "T", "topic": "x", "participants": ["A", "B"]}]})
        with pytest.raises(ValueError, match="'areas' list"):
            parse_solution_areas({"nope": []})

    def test_roundtrip(self, tmp_path) -> None:
        reg = SolutionAreaRegister([_area("SA-1", "env", ["A", "B"], 30, 10),
                                    _area("SA-2", "api", ["B", "C"], 5)])
        reg.areas[1].notes = "still open"
        path = tmp_path / "solution_areas.json"
        save_solution_areas(path, reg)
        assert load_solution_areas(path) == reg
        assert json.loads(path.read_text(encoding="utf-8"))["schema"] == 1


class TestSeams:
    def test_grouping_and_recurrence(self) -> None:
        areas = [_area("1", "env", ["A", "B"], 200, 170), _area("2", "env", ["B", "A"], 100, 80),
                 _area("3", "env", ["A", "B"], 9), _area("4", "latency", ["A", "C"], 50, 30),
                 _area("5", "api", ["A", "B"], 300, 280)]
        result = seams(areas)
        assert [s.participants for s in result] == [("A", "B"), ("A", "C")]
        ab = result[0]
        assert ab.count == 4 and ab.active == 1 and ab.recurrence == 3
        assert ab.recurring_topic == "env" and ab.signal and ab.highlighted
        assert ab.total_days(REF) == 30 + 20 + 9 + 20
        assert ab.last_opened == REF - timedelta(days=9)
        ac = result[1]
        assert ac.recurrence == 1 and not ac.highlighted and not ac.signal

    def test_thresholds(self) -> None:
        assert RECURRENCE_HIGHLIGHT == 2 and RECURRENCE_SIGNAL == 3
        twice = seams([_area("1", "env", ["A", "B"], 50, 40), _area("2", "env", ["A", "B"], 20, 10)])[0]
        assert twice.highlighted and not twice.signal


class TestRendering:
    def test_recurring_seam_first_red_cell_and_legend(self) -> None:
        entries = [("S", _area("1", "env", ["A", "B"], 200, 170)), ("S", _area("2", "env", ["A", "B"], 9)),
                   ("S", _area("3", "env", ["A", "B"], 100, 80)), ("S", _area("4", "api", ["C", "D"], 30, 20))]
        html = render_solution_areas_html(entries, lang="de", reference=REF)
        assert "4 Areas · 2 Nähte · 1 wiederkehrend · 1 EA-Signal" in html
        assert html.index("A × B") < html.index("C × D")
        assert f"background:{_OVERDUE_COLOR};font-weight:700'>3×" in html
        assert "env (3×)" in html and "wiederkehrend — derselbe Anlass" in html

    def test_empty_renders_nothing_and_no_legend_without_recurrence(self) -> None:
        assert render_solution_areas_html([], lang="en") == ""
        html = render_solution_areas_html([("S", _area("1", "env", ["A", "B"], 30, 20))], lang="en",
                                          reference=REF)
        assert "recurring —" not in html and "1 areas · 1 seams · 0 recurring" in html

    @pytest.mark.parametrize("lang", ["de", "en", "ro", "pt", "fr"])
    def test_every_language(self, lang) -> None:
        html = render_solution_areas_html([("S", _area("1", "env", ["A", "B"], 30, 20))], lang=lang,
                                          reference=REF)
        assert "<table" in html and "A × B" in html


class TestConfigAndCollector:
    def test_config_field_roundtrips_and_is_optional(self) -> None:
        cfg = SolutionConfig(name="S", members=[Member(name="ART A", issue_times="a.xlsx")],
                             solution_areas="registers/solution_areas.json")
        assert to_dict(cfg)["solution_areas"] == "registers/solution_areas.json"
        assert parse_solution_config(to_dict(cfg)) == cfg
        assert "solution_areas" not in to_dict(SolutionConfig(name="S", members=[]))

    def test_collector_labels_and_skips_broken(self, tmp_path) -> None:
        good = tmp_path / "areas.json"
        save_solution_areas(good, SolutionAreaRegister([_area("SA-1", "env", ["A", "B"], 30, 20)]))
        (tmp_path / "broken.json").write_text("{", encoding="utf-8")
        ok = SolutionConfig(name="Good", members=[], solution_areas=str(good))
        bad = SolutionConfig(name="Bad", members=[], solution_areas=str(tmp_path / "broken.json"))
        none = SolutionConfig(name="None", members=[])
        msgs: list[str] = []
        assert [(label, a.area_id) for label, a in _collect_solution_areas(ok, log=msgs.append)] == [("Good", "SA-1")]
        assert _collect_solution_areas(bad, log=msgs.append) == []
        assert any("solution-areas file skipped" in m for m in msgs)
        assert _collect_solution_areas(none, log=msgs.append) == []

    def test_datenraum_dialog_knows_the_register(self, tmp_path) -> None:
        from portfolio.gui import REGISTER_FIELDS, fill_from_datenraum
        assert "solution_areas" in REGISTER_FIELDS
        reg = tmp_path / "registers"
        reg.mkdir()
        (reg / "solution_areas.json").write_text("{}", encoding="utf-8")
        assert fill_from_datenraum(tmp_path) == {"solution_areas": str((reg / "solution_areas.json").resolve())}


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    out = tmp_path_factory.mktemp("demo")
    return build_portfolio_scenario(out, seed=42, reference=REF, log=lambda m: None)


class TestScenarioStory:
    def test_alpha_seam_carries_the_signal_and_delta_shows_it_arriving(self, demo) -> None:
        from portfolio.delta import compute_delta
        from portfolio.snapshot import load_snapshot
        reg = load_solution_areas(demo["areas_alpha"])
        all_seams = seams(reg.areas)
        seam = next(s for s in all_seams if s.participants == ("ART Alpha-1", "ART Alpha-3"))
        assert seam.signal and seam.recurring_topic == "test environment"
        # the generated base population never produces a second signal
        assert [s.participants for s in all_seams if s.signal] == [("ART Alpha-1", "ART Alpha-3")]
        assert all(a.title and a.topic for a in reg.areas)
        prev, now = load_snapshot(demo["snapshot_prev"]), load_snapshot(demo["snapshot_now"])
        assert len(now.governance["solution_areas"]) == len(prev.governance["solution_areas"]) + 1
        added = compute_delta(prev, now).governance["solution_areas"].added
        assert [e["id"] for e in added] == ["SA-A3"]

    def test_scale_l_keeps_the_signal_with_the_anchors(self, tmp_path) -> None:
        from testdata_generator.scenario import build_portfolio_scenario
        paths = build_portfolio_scenario(tmp_path, seed=7, reference=REF, scale="l",
                                         log=lambda m: None)
        reg = load_solution_areas(paths["areas_alpha"])
        assert len(reg.areas) > 4
        assert [s.participants for s in seams(reg.areas) if s.signal] == [("ART Alpha-1", "ART Alpha-3")]

    def test_report_and_pre_read_carry_the_seams(self, demo) -> None:
        from portfolio.aggregator import render_conference_html, render_pooled_html
        from portfolio.solution_config import load_solution_config
        cfg = load_solution_config(demo["solution_alpha"])
        assert "Solution Areas &amp; Rekurrenz je Naht" in render_pooled_html(cfg, log=lambda *_: None, lang="de")
        assert "ART Alpha-1 × ART Alpha-3" in render_conference_html(cfg, log=lambda *_: None, lang="de")

    def test_onepager_names_the_seam(self, demo) -> None:
        from portfolio.onepager import build_onepager
        from portfolio.solution_config import load_solution_config
        op = build_onepager(load_solution_config(demo["solution_alpha"]), "de", reference=REF)
        q1 = op.cells["dependencies"]["q1"]
        assert any(line.startswith("Solution Areas ") and "wiederkehrend" in line for line in q1.lines)
        assert any("Naht prüfen" in line and "ART Alpha-1 × ART Alpha-3 (test environment)" in line
                   for line in op.cells["dependencies"]["q3"].decide)

    def test_bluf_names_the_signal_when_it_is_the_only_alarm(self, tmp_path) -> None:
        from portfolio.onepager import build_onepager
        path = tmp_path / "areas.json"
        save_solution_areas(path, SolutionAreaRegister([
            _area("1", "env", ["A", "B"], 200, 170), _area("2", "env", ["A", "B"], 100, 80),
            _area("3", "env", ["A", "B"], 9)]))
        cfg = SolutionConfig(name="Only areas", members=[], solution_areas=str(path))
        op = build_onepager(cfg, "en", reference=REF, log=lambda m: None)
        assert op.bluf == "1 seam(s) with EA signal."
        assert op.cells["dependencies"]["q3"].decide == ["check the seam (EA signal, same topic ≥ 3×): A × B (env)"]

    def test_exec_summary_contract_counts_areas(self, demo) -> None:
        from portfolio.exec_summary import summary_to_markdown
        from portfolio.snapshot import load_snapshot
        md = summary_to_markdown(load_snapshot(demo["snapshot_now"]))
        assert "- solution_areas:" in md and "active" in md
