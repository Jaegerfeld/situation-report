# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   tkinter-Rückfalllösung des Datenraums (Beta, 30.10.2026): Modell ohne
#   Fenster (Zeilen ↔ Struktur, Vorschau, Anfrage, Fehler, Fenstertexte,
#   Öffnen-Ziele) und ein Fenster-Rauchtest, der ohne Display übersprungen
#   wird — die drei Reiter, der Struktur-Editor, der Vorlagenwechsel und
#   eine komplette Erzeugung mit Ergebniskarte.
# =============================================================================

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path

import pytest

from testdata_generator.dataspace_gui import (
    DataspaceWindow,
    PortfolioRow,
    Settings,
    SolutionRow,
    build_preview,
    build_request,
    next_solution_name,
    open_target,
    rows_from_structure,
    structure_from_rows,
    when_text,
)
from testdata_generator.story import Event
from testdata_generator.structure import WORKFLOW_STAGE_MAP, structure_template
from testdata_generator.web.texts import texts_for

REF = date(2025, 6, 30)


def _settings(**kw) -> Settings:
    s = Settings(**kw)
    if not s.rows:
        s.rows = rows_from_structure(structure_template("standard"))
    return s


class TestModel:
    def test_rows_roundtrip_the_standard_structure(self) -> None:
        rows = rows_from_structure(structure_template("standard"))
        assert [(p.name, [(s.name, s.workflow, s.arts) for s in p.solutions]) for p in rows] == [
            ("Demo Portfolio", [("Alpha", "classic", 3), ("Beta", "stage_map", 3)])]
        assert structure_from_rows(rows).describe() == "1 Portfolio · 2 Solutions · 6 ARTs"

    def test_rows_build_arts_from_solution_names(self) -> None:
        rows = [PortfolioRow("Nord", [SolutionRow("Kern", WORKFLOW_STAGE_MAP, 2), SolutionRow("Rand", "classic", 1)])]
        s = structure_from_rows(rows)
        assert s.portfolios[0].solutions[0].arts == ["Kern-1", "Kern-2"]
        assert s.portfolios[0].solutions[1].workflow == "classic"
        with pytest.raises(ValueError, match="at least one ART"):
            structure_from_rows([PortfolioRow("P", [SolutionRow("A", "classic", 0)])])

    def test_next_solution_name_skips_used_greek_letters(self) -> None:
        rows = rows_from_structure(structure_template("standard"))
        assert next_solution_name(rows) == "Gamma"
        rows[0].solutions.append(SolutionRow("Gamma"))
        assert next_solution_name(rows) == "Delta"

    def test_preview_follows_template_switches_and_stands(self) -> None:
        s = _settings(template="escalation", switches={"E3": False}, stands=4)
        structure, est, story = build_preview(s)
        assert est.stands == 4 and est.deltas == 3 and structure.n_arts == 6
        assert story.template == "escalation" and story.stands == 4
        assert not next(e for e in story.events if e.event_id == "E3").enabled
        calm = _settings(template="calm")
        assert calm.effective_stands() == 3 and build_preview(calm)[1].stands == 3

    def test_request_translation_and_errors(self, tmp_path) -> None:
        s = _settings(seed="7", reference=REF.isoformat(), realism=90, ai_drafts=True,
                      output_dir=str(tmp_path / "raum"), lang="de")
        req = build_request(s)
        assert req.seed == 7 and req.reference == REF and req.ai_drafts and req.lang == "de"
        assert req.art_profiles == {a: {"realism": 90} for a in req.structure.portfolios[0].arts}
        assert build_request(_settings(output_dir="x")).art_profiles is None
        for bad, needle in (({"seed": "abc"}, "seed"), ({"reference": "gestern"}, "reference"),
                            ({"output_dir": "  "}, "output_dir"), ({"stands": 99}, "stands")):
            with pytest.raises(ValueError, match=needle):
                build_request(_settings(output_dir="x", **bad) if "output_dir" not in bad
                              else _settings(**bad))

    def test_when_text_matches_the_browser_wording(self) -> None:
        t = texts_for("de")
        assert when_text(Event("E1", "outlier_art", "t", stand_from=1, stand_to=None), 6, t) == "alle Stände"
        assert when_text(Event("E3", "blocked_dependency", "t", stand_from=4, stand_to=None), 6, t) == "ab Stand 4"
        assert when_text(Event("E3", "blocked_dependency", "t", stand_from=6, stand_to=None), 6, t) == "letzter Stand"
        assert when_text(Event("E5", "recurring_seam", "t", stand_from=1, stand_to=1), 6, t) == "Stand 1"
        assert when_text(Event("E1", "outlier_art", "t", stand_from=1, stand_to=4), 6, t) == "Stand 1–4"


@pytest.fixture
def window():
    try:
        win = DataspaceWindow(lang="de")
        win.withdraw()
    except tk.TclError as exc:  # pragma: no cover - headless CI
        pytest.skip(f"no display: {exc}")
    yield win
    try:
        win.destroy()
    except tk.TclError:
        pass


def _pump(win: tk.Tk, ms: int = 250) -> None:
    deadline = win.tk.call("clock", "milliseconds") + ms
    while win.tk.call("clock", "milliseconds") < deadline:
        win.update()


class TestWindow:
    def test_three_tabs_preview_and_structure_editor(self, window) -> None:
        win = window
        assert win.nb.index("end") == 3
        _pump(win)
        assert win.preview is not None and win.preview_error is None
        assert len(win._event_vars) == 10
        assert "6 Jira-Exporte" in win.lbl_yields.cget("text")
        # template change resets switches and follows the suggested stands
        win.var_template.set("calm")
        win._on_template()
        _pump(win)
        assert win.s.template == "calm" and win.s.effective_stands() == 3
        assert all(not v.get() for v in win._event_vars.values())
        # structure editor: add a solution, count ARTs, remove a portfolio is blocked
        win._add_solution(win.s.rows[0])
        _pump(win)
        assert [s.name for s in win.s.rows[0].solutions] == ["Alpha", "Beta", "Gamma"]
        assert win.s.structure_template == "custom"
        assert "3 Solution" in win.lbl_sum.cget("text") and "8 ARTs" in win.lbl_sum.cget("text")
        win._remove_portfolio(0)
        assert len(win.s.rows) == 1
        assert any("Solution Gamma" in n for n in win.preview[2].notices)

    def test_generation_runs_to_the_result_card(self, window, tmp_path, monkeypatch) -> None:
        win = window
        win.var_struct_tpl.set(win.t["st_small"])
        win._on_struct_template()
        win.scl_stands.set(2)
        win._on_stands("2")
        win.var_scale.set(win.t["scale_s"])
        win._on_scale()
        win.var_ref.set(REF.isoformat())
        win.var_out.set(str(tmp_path / "raum"))
        _pump(win)
        win._generate()
        deadline = win.tk.call("clock", "milliseconds") + 180_000
        while win.job_state == "running" and win.tk.call("clock", "milliseconds") < deadline:
            win.update()
            win.tk.call("after", 50)
        assert win.job_state == "done", win.job_error
        assert win.result is not None and win.result.stands == 2 and win.result.deltas == 1
        assert (tmp_path / "raum" / "portfolio.json").is_file()
        assert "raum" in win.result_box.cget("text")
        assert all(m.cget("text") in ("✓", "–") for m, _, _ in win.step_rows.values())
        opened: list[Path] = []
        monkeypatch.setattr("testdata_generator.dataspace_gui.default_open", opened.append)
        win._open("readme")
        assert opened and opened[-1].name == "README.md"
        win._open_pair()
        assert opened[-1].name == "delta_01-02.html"

    def test_non_empty_folder_asks_and_bad_input_is_shown(self, window, tmp_path, monkeypatch) -> None:
        win = window
        full = tmp_path / "voll"
        full.mkdir()
        (full / "x.txt").write_text("x", encoding="utf-8")
        asked: list[str] = []
        monkeypatch.setattr("testdata_generator.dataspace_gui.messagebox.askyesno",
                            lambda *a, **k: asked.append(a[0]) or False)
        win.var_out.set(str(full))
        win._generate()
        assert asked == [win.t["confirm_title"]] and win.job_state == "idle"
        win.var_seed.set("abc")
        win._generate()
        assert "seed" in win.lbl_error.cget("text")


class TestOpenTarget:
    def test_open_target_rejects_unknown_and_missing(self, tmp_path) -> None:
        from testdata_generator.dataspace import GenerationRequest, generate_dataspace
        req = GenerationRequest(output_dir=tmp_path / "r", reference=REF, scale="s", stands=2,
                                structure=structure_template("small"))
        result = generate_dataspace(req)
        opened: list[Path] = []
        assert open_target(result, "folder", opener=opened.append) == tmp_path / "r"
        with pytest.raises(ValueError):
            open_target(result, "nothing", opener=opened.append)
        with pytest.raises(LookupError):
            open_target(result, "drafts", opener=opened.append)
        assert open_target(result, "delta", a=1, b=2, opener=opened.append).name == "delta_01-02.html"
