# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Decision-Log-Darstellung (B4): HTML-/PDF-Rendering
#   (überfällige Annahmen zuerst, „review due"-Hervorhebung, supersedes im
#   Eintragstext, Solution-Spalte, Titelzähler) und das Einsammeln über die
#   Config (_collect_decisions inkl. Fehlertoleranz).
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

from portfolio.aggregator import _collect_decisions
from portfolio.decision_config import DecisionLog, LogEntry, save_decisions
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    save_solution_config,
)
from portfolio.summary import (
    _OVERDUE_COLOR,
    decisions_figure,
    render_decisions_html,
)

REF = date(2025, 6, 30)


def _entries() -> list[tuple[str, LogEntry]]:
    return [
        ("Solution A", LogEntry("E-0", "decision", "Old way", "superseded")),
        ("Solution A", LogEntry("E-1", "decision", "New way", "accepted",
                                supersedes="E-0")),
        ("Solution A", LogEntry("A-2", "assumption", "Fresh guess", "open",
                                review_by=REF + timedelta(days=30))),
        ("Solution A", LogEntry("A-1", "assumption", "Stale guess", "open",
                                owner="Team X",
                                review_by=REF - timedelta(days=10))),
        ("Solution A", LogEntry("A-3", "assumption", "Checked guess",
                                "confirmed")),
    ]


class TestRenderDecisionsHtml:
    def test_empty_entries_render_nothing(self) -> None:
        assert render_decisions_html([]) == ""

    def test_review_due_assumption_sorts_first(self) -> None:
        html = render_decisions_html(_entries(), reference=REF)
        # Titel statt IDs: "E-0" taucht auch im supersedes-Text von E-1 auf.
        positions = [html.index(k) for k in
                     ("Stale guess", "Fresh guess", "New way",
                      "Checked guess", "Old way")]
        assert positions == sorted(positions)

    def test_review_due_cell_is_highlighted(self) -> None:
        html = render_decisions_html(_entries(), reference=REF)
        rows = html.split("<tr>")
        stale_row = next(r for r in rows if "A-1" in r and "Stale" in r)
        fresh_row = next(r for r in rows if "A-2" in r)
        assert "(review due)" in stale_row
        assert _OVERDUE_COLOR in stale_row
        assert "(review due)" not in fresh_row

    def test_supersedes_shown_in_entry_text(self) -> None:
        html = render_decisions_html(_entries(), reference=REF)
        assert "(supersedes E-0)" in html

    def test_title_counts(self) -> None:
        html = render_decisions_html(_entries(), reference=REF)
        assert "2 decisions, 3 assumptions (1 due for review)" in html

    def test_single_source_hides_solution_column(self) -> None:
        assert "<th>Solution</th>" not in render_decisions_html(
            _entries(), reference=REF)

    def test_two_sources_add_solution_column(self) -> None:
        entries = _entries() + [
            ("Solution B", LogEntry("B-1", "decision", "Other", "accepted"))]
        html = render_decisions_html(entries, reference=REF)
        assert "<th>Solution</th>" in html
        assert "<td>Solution B</td>" in html


class TestDecisionsFigure:
    def test_figure_mirrors_html(self) -> None:
        fig = decisions_figure(_entries(), reference=REF)
        table = fig.data[0]
        assert list(table.header.values) == [
            "Type", "Entry", "Status", "Owner (team)", "Logged", "Review by"]
        assert len(table.cells.values[0]) == 5
        assert "2 decisions, 3 assumptions (1 due for review)" \
            in fig.layout.title.text
        # Die überfällige Annahme sortiert nach oben — Review-by-Zelle rot.
        assert list(table.cells.fill.color[5])[0] == _OVERDUE_COLOR


class TestCollectDecisions:
    def _solution(self, tmp_path, name: str, entries: list[LogEntry]):
        log_path = tmp_path / f"{name}_decisions.json"
        save_decisions(log_path, DecisionLog(entries=entries))
        return SolutionConfig(
            name=name,
            members=[Member(name="ART 1", issue_times="dummy.xlsx")],
            decisions=str(log_path))

    def test_solution_entries_are_labelled(self, tmp_path) -> None:
        cfg = self._solution(tmp_path, "Solution A",
                             [LogEntry("E-1", "decision", "T", "accepted")])
        entries = _collect_decisions(cfg, log=lambda m: None)
        assert [(s, e.entry_id) for s, e in entries] == [("Solution A", "E-1")]

    def test_solution_without_decisions_yields_empty(self) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")])
        assert _collect_decisions(cfg, log=lambda m: None) == []

    def test_portfolio_aggregates_member_logs(self, tmp_path) -> None:
        cfg_a = self._solution(tmp_path, "Solution A",
                               [LogEntry("A-1", "decision", "T", "accepted")])
        cfg_b = self._solution(tmp_path, "Solution B",
                               [LogEntry("B-1", "assumption", "T", "open")])
        path_a = tmp_path / "sol_a.json"
        path_b = tmp_path / "sol_b.json"
        save_solution_config(path_a, cfg_a)
        save_solution_config(path_b, cfg_b)
        portfolio = SolutionConfig(
            name="P", kind=KIND_PORTFOLIO,
            members=[Member(name="Solution A", template=str(path_a)),
                     Member(name="Solution B", template=str(path_b))])
        entries = _collect_decisions(portfolio, log=lambda m: None)
        assert [(s, e.entry_id) for s, e in entries] == [
            ("Solution A", "A-1"), ("Solution B", "B-1")]

    def test_broken_decisions_file_is_skipped_with_warning(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            decisions=str(bad))
        warnings: list[str] = []
        assert _collect_decisions(cfg, log=warnings.append) == []
        assert any("skipped" in w for w in warnings)
