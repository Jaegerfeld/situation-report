# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests für die Veränderung zweier Bewertungsstände (P3 Schritt 2): Stand
#   zum Stichtag, Zellen-Diff, neue Bewertungen ohne Namen, Entscheidungen,
#   hinzugekommene/entfallene Prozesse, Katalogwechsel, „keine Änderungen"
#   ausdrücklich, Markdown-Contract ohne Personen, HTML in fünf Sprachen.
# =============================================================================

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from harmonisation.delta import compute_delta, delta_to_markdown, filter_as_of
from harmonisation.examples import write_example
from harmonisation.model import (
    DECISION_OPEN,
    LANGS,
    Catalogue,
    Decision,
    Dimension,
    Process,
    Question,
    Workspace,
    load_workspace,
)
from harmonisation.render import _T, render_delta_html

CUT = date(2026, 9, 20)   # zwischen den beiden o2d-Bewertungen (15.09. / 22.09.)


@pytest.fixture
def ws(tmp_path) -> Workspace:
    write_example(tmp_path)
    return load_workspace(tmp_path)


class TestFilterAsOf:
    def test_keeps_only_assessments_up_to_the_day(self, ws) -> None:
        prev = filter_as_of(ws, CUT)
        assert [a.day for a in prev.assessments] == [date(2026, 9, 15)]
        assert prev.processes == ws.processes and prev.catalogue is ws.catalogue

    def test_dated_decisions_follow_the_day_undated_stay(self, ws) -> None:
        undated = Decision("p2p", DECISION_OPEN, "noch offen", None, "Board")
        ws.decisions["p2p"] = undated
        prev = filter_as_of(ws, CUT)          # Board-Entscheidungen vom 06.10. fallen weg
        assert set(prev.decisions) == {"p2p"}


class TestComputeDelta:
    def test_example_since_september(self, ws) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "2026-09-20", "2026-10-12")
        assert not delta.quiet
        changed = {(c.process, c.dimension) for c in delta.cells}
        dims = ("business_value", "transparency", "it_operations")
        assert changed == {(p, d) for p in ("o2d", "c2o") for d in dims}
        bv = next(c for c in delta.cells
                  if (c.process, c.dimension) == ("o2d", "business_value"))
        assert bv.score == (78.1, 67.6) and bv.spread == (None, 21.0)
        assert bv.assessments == (1, 2)
        assert [(n.process, n.day) for n in delta.new_assessments] == [
            ("o2d", date(2026, 9, 22)), ("c2o", date(2026, 9, 29))]
        assert sorted(d.process for d in delta.decisions) == ["c2o", "o2d"]
        assert all(d.old is None for d in delta.decisions)
        assert not delta.added_processes and not delta.removed_processes
        assert not delta.catalogue_changed

    def test_same_state_is_quiet(self, ws) -> None:
        assert compute_delta(ws, ws, "a", "b").quiet

    def test_added_and_removed_processes(self, ws) -> None:
        later = replace(ws, processes=ws.processes[1:] + (Process("x2y", "X-to-Y"),))
        delta = compute_delta(ws, later, "a", "b")
        assert delta.added_processes == ["X-to-Y"]
        assert delta.removed_processes == ["Order-to-Delivery"]
        # a removed process yields no cell changes
        assert all(c.process != "o2d" for c in delta.cells)

    def test_catalogue_change_is_flagged(self, ws) -> None:
        other = Catalogue("other", (Dimension("d", {"en": "D"},
                                              (Question("q1", {"en": "Q"}),)),))
        later = replace(ws, catalogue=other, assessments=())
        assert compute_delta(ws, later, "a", "b").catalogue_changed

    def test_undated_decisions_are_counted(self, ws) -> None:
        ws.decisions["h2r"] = Decision("h2r", DECISION_OPEN, "", None, "")
        assert compute_delta(ws, ws, "a", "b").undated_decisions == 1


class TestMarkdown:
    def test_contract_carries_numbers_but_no_persons(self, ws) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "2026-09-20", "2026-10-12")
        md = delta_to_markdown(delta, ws)
        assert "78.1 -> 67.6" in md and "spread none -> 21" in md
        assert "assessment dated 2026-09-22" in md
        assert "open -> standardise" in md
        for person in ("Logistik-Leitung", "IT-Architektur", "Vertriebs-Leitung",
                       "Head of Logistics", "CPO"):
            assert person not in md

    def test_quiet_is_said_explicitly(self, ws) -> None:
        md = delta_to_markdown(compute_delta(ws, ws, "a", "b"), ws)
        assert "No changes between the two states." in md

    def test_deterministic(self, ws) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "a", "b")
        assert delta_to_markdown(delta, ws) == delta_to_markdown(delta, ws)


class TestHtml:
    @pytest.mark.parametrize("lang", LANGS)
    def test_renders_every_language(self, ws, lang: str) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "2026-09-20", "2026-10-12")
        html = render_delta_html(delta, ws, lang, today=date(2026, 10, 12))
        assert f'<html lang="{lang}">' in html
        assert _T[lang]["delta_cells"] in html
        assert "Order-to-Delivery" in html and "→" in html

    def test_quiet_page_says_so(self, ws) -> None:
        html = render_delta_html(compute_delta(ws, ws, "a", "b"), ws, "de")
        assert "Keine Änderungen zwischen den beiden Ständen." in html
        assert "<table>" not in html

    def test_decisions_and_new_assessments_listed(self, ws) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "2026-09-20", "2026-10-12")
        html = render_delta_html(delta, ws, "de")
        assert "Bewertung vom 22.09.2026" in html
        assert "offen → <b>standardisieren" in html
        assert "Logistik-Leitung" not in html      # Namen nur in der Matrix selbst

    def test_lower_score_is_not_called_worse(self, ws) -> None:
        delta = compute_delta(filter_as_of(ws, CUT), ws, "a", "b")
        html = render_delta_html(delta, ws, "de").lower()
        assert "verschlechter" not in html.replace("keine verschlechterung", "")
