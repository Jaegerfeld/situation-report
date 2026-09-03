# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für Strategic Themes & integrierte Roadmap (B7, VSC-2):
#   Parsen/Roundtrip (Tippfehler-Referenz = Fehler, leeres theme = Zombie),
#   Orphan-/Zombie-Ableitung, Rendering (Orphan rot „declared & forgotten",
#   Roadmap-Matrix Trains × P1·P2·Y1·Y2·Y3, Zombie-Markierung), Collector
#   und die Delta-Erweiterung um Roadmap-Epics (Mehrfeld-Änderungen,
#   Theme-Verlust = worsened „zombie").
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.aggregator import _collect_themes
from portfolio.delta import compute_delta
from portfolio.snapshot import Snapshot
from portfolio.solution_config import Member, SolutionConfig
from portfolio.summary import _OVERDUE_COLOR, render_themes_html
from portfolio.themes_config import (
    Epic,
    StrategicTheme,
    ThemesRegister,
    load_themes,
    orphan_theme_ids,
    parse_themes,
    save_themes,
    zombie_epics,
)


def _register() -> ThemesRegister:
    return ThemesRegister(
        themes=[StrategicTheme("T-1", "Digital"),
                StrategicTheme("T-2", "Forgotten")],
        epics=[Epic("EP-1", "Portal", "ART A", "P1", theme="T-1"),
               Epic("EP-2", "Zombie thing", "ART B", "Y1")])


class TestParse:
    def test_minimal_and_derivations(self) -> None:
        register = parse_themes({
            "themes": [{"id": "T-1", "title": "Digital"},
                       {"id": "T-2", "title": "Forgotten"}],
            "epics": [{"id": "EP-1", "title": "Portal", "train": "ART A",
                       "horizon": "P1", "theme": "T-1"},
                      {"id": "EP-2", "title": "Zombie", "train": "ART B",
                       "horizon": "Y1"}]})
        assert orphan_theme_ids(register) == {"T-2"}
        assert [e.epic_id for e in zombie_epics(register)] == ["EP-2"]
        assert register.epics[1].status == "planned"

    def test_typo_reference_is_error_not_zombie(self) -> None:
        with pytest.raises(ValueError, match="unknown theme"):
            parse_themes({"themes": [{"id": "T-1", "title": "X"}],
                          "epics": [{"id": "EP-1", "title": "Y",
                                     "train": "A", "horizon": "P1",
                                     "theme": "T-9"}]})

    def test_rejects_structural_errors(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_themes([])
        with pytest.raises(ValueError, match="Duplicate theme"):
            parse_themes({"themes": [{"id": "T", "title": "a"},
                                     {"id": "T", "title": "b"}]})
        with pytest.raises(ValueError, match="unknown horizon"):
            parse_themes({"epics": [{"id": "E", "title": "t", "train": "A",
                                     "horizon": "Q3"}]})
        with pytest.raises(ValueError, match="unknown status"):
            parse_themes({"epics": [{"id": "E", "title": "t", "train": "A",
                                     "horizon": "P1", "status": "paused"}]})
        with pytest.raises(ValueError, match="'train'"):
            parse_themes({"epics": [{"id": "E", "title": "t",
                                     "horizon": "P1"}]})

    def test_roundtrip(self, tmp_path) -> None:
        path = tmp_path / "themes.json"
        save_themes(path, _register())
        assert load_themes(path) == _register()


class TestRendering:
    def _entries(self):
        reg = _register()
        return ([("Sol A", t) for t in reg.themes],
                [("Sol A", e) for e in reg.epics])

    def test_orphan_zombie_and_matrix(self) -> None:
        themes, epics = self._entries()
        html = render_themes_html(themes, epics)
        assert "2 themes, 2 epics (1 orphan themes, 1 zombie epics)" in html
        assert "declared &amp; forgotten" in html
        assert "[ZOMBIE]" in html and _OVERDUE_COLOR in html
        # Matrix: Trains als Zeilen, alle fuenf Horizonte als Spalten.
        assert "Train \\ Horizon" in html
        for horizon in ("P1", "P2", "Y1", "Y2", "Y3"):
            assert f"<th>{horizon}</th>" in html
        assert "Zombie initiatives" in html

    def test_orphanhood_is_portfolio_wide(self) -> None:
        # Das Theme der einen Solution wird vom Epic der anderen bedient.
        themes = [("Sol A", StrategicTheme("T-1", "Shared"))]
        epics = [("Sol B", Epic("EP-9", "Server", "ART B", "P1",
                                theme="T-1"))]
        html = render_themes_html(themes, epics)
        assert "declared" not in html

    def test_empty_renders_nothing(self) -> None:
        assert render_themes_html([], []) == ""


class TestCollectorAndDelta:
    def test_collector_labels_and_skips_broken(self, tmp_path) -> None:
        good = tmp_path / "themes.json"
        save_themes(good, _register())
        cfg = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            themes=str(good))
        themes, epics = _collect_themes(cfg, log=lambda m: None)
        assert len(themes) == 2 and len(epics) == 2

        bad = tmp_path / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        cfg_bad = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            themes=str(bad))
        warnings: list[str] = []
        assert _collect_themes(cfg_bad, log=warnings.append) == ([], [])
        assert any("skipped" in w for w in warnings)

    def _snapshot(self, as_of: date, epics: list[dict]) -> Snapshot:
        return Snapshot(
            name="Demo", kind="portfolio", as_of=as_of, created="",
            target_ct=90, total={"label": "Demo", "items": 1,
                                 "completed": 1, "open": 0},
            governance={"risks": [], "dependencies": [], "nfr": [],
                        "runway": [], "capabilities": [], "decisions": [],
                        "epics": epics})

    def test_delta_reports_updated_roadmaps(self) -> None:
        prev = self._snapshot(date(2025, 6, 16), [
            {"id": "EP-1", "title": "Portal", "train": "A", "horizon": "P2",
             "theme": "T-1", "status": "planned", "solution": "S"},
            {"id": "EP-9", "title": "Legacy", "train": "B", "horizon": "Y1",
             "theme": "T-1", "status": "planned", "solution": "S"}])
        now = self._snapshot(date(2025, 6, 30), [
            {"id": "EP-1", "title": "Portal", "train": "A", "horizon": "P1",
             "theme": "T-1", "status": "in_progress", "solution": "S"},
            {"id": "EP-9", "title": "Legacy", "train": "B", "horizon": "Y1",
             "theme": "", "status": "planned", "solution": "S"}])
        delta = compute_delta(prev, now)
        section = delta.governance["epics"]
        by_id = {c.entry_id: c for c in section.changed}
        # Mehrfeld-Aenderung: Horizont vorgezogen + Status.
        assert set(by_id["EP-1"].fields) == {"horizon", "status"}
        assert not by_id["EP-1"].worsened
        # Theme verloren -> Zombie -> worsened.
        assert by_id["EP-9"].fields["theme"] == ("T-1", "")
        assert by_id["EP-9"].worsened
