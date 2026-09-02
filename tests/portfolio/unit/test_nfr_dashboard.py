# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das NFR-/Runway-Dashboard (B2): HTML-/PDF-Rendering
#   (Sortierung verletzt/gap zuerst, Solution-Spalte, Overdue-Hervorhebung,
#   Titelzähler) und das Einsammeln über die Config (_collect_nfr inkl.
#   Fehlertoleranz bei kaputten Dateien).
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

from portfolio.aggregator import _collect_nfr
from portfolio.nfr_config import Nfr, NfrRegister, RunwayItem, save_nfr
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    save_solution_config,
)
from portfolio.summary import _OVERDUE_COLOR, nfr_figure, render_nfr_html

REF = date(2025, 6, 30)


def _nfrs() -> list[tuple[str, Nfr]]:
    return [
        ("Solution A", Nfr("N-2", "Uptime", ">= 99.5 %", "met", actual="99.7 %")),
        ("Solution A", Nfr("N-1", "Response", "p95 < 200 ms", "violated",
                           actual="340 ms", owner="Team A")),
        ("Solution A", Nfr("N-3", "Load", "50 users", "at_risk")),
    ]


def _runway() -> list[tuple[str, RunwayItem]]:
    return [
        ("Solution A", RunwayItem("RW-2", "Test env", "building",
                                  needed_by=REF + timedelta(days=30))),
        ("Solution A", RunwayItem("RW-1", "Failover", "gap",
                                  needed_by=REF - timedelta(days=20))),
    ]


class TestRenderNfrHtml:
    def test_empty_renders_nothing(self) -> None:
        assert render_nfr_html([], []) == ""

    def test_orders_violated_and_gap_first(self) -> None:
        html = render_nfr_html(_nfrs(), _runway(), reference=REF)
        positions = [html.index(k) for k in ("N-1", "N-3", "N-2")]
        assert positions == sorted(positions)
        positions_r = [html.index(k) for k in ("RW-1", "RW-2")]
        assert positions_r == sorted(positions_r)

    def test_overdue_runway_date_is_highlighted(self) -> None:
        html = render_nfr_html(_nfrs(), _runway(), reference=REF)
        rows = html.split("<tr>")
        overdue_row = next(r for r in rows if "RW-1" in r)
        fresh_row = next(r for r in rows if "RW-2" in r)
        assert "(overdue)" in overdue_row
        assert _OVERDUE_COLOR in overdue_row
        assert "(overdue)" not in fresh_row

    def test_title_counts(self) -> None:
        html = render_nfr_html(_nfrs(), _runway(), reference=REF)
        assert "3 NFRs (1 violated, 1 at risk)" in html
        assert "2 runway elements (1 gaps, 1 overdue)" in html

    def test_single_source_hides_solution_column(self) -> None:
        html = render_nfr_html(_nfrs(), _runway(), reference=REF)
        assert "<th>Solution</th>" not in html

    def test_two_sources_add_solution_column(self) -> None:
        nfrs = _nfrs() + [("Solution B", Nfr("B-1", "Other", "t", "met"))]
        html = render_nfr_html(nfrs, _runway(), reference=REF)
        assert "<th>Solution</th>" in html
        assert "<td>Solution B</td>" in html

    def test_nfr_only_renders_single_table(self) -> None:
        html = render_nfr_html(_nfrs(), [], reference=REF)
        assert "NFR" in html
        assert "Runway element" not in html
        assert "runway elements" not in html


class TestNfrFigure:
    def test_figure_mirrors_html(self) -> None:
        fig = nfr_figure(_nfrs(), _runway(), reference=REF)
        assert len(fig.data) == 2
        nfr_table, runway_table = fig.data
        assert list(nfr_table.header.values) == [
            "NFR", "Target", "Actual", "Status", "Owner (team)"]
        assert list(runway_table.header.values) == [
            "Runway element", "Status", "Needed by", "Owner (team)"]
        assert "3 NFRs (1 violated, 1 at risk)" in fig.layout.title.text
        # Overdue highlight sits in the Needed-by column, first row (gap first).
        assert list(runway_table.cells.fill.color[2])[0] == _OVERDUE_COLOR

    def test_runway_only_has_one_table(self) -> None:
        fig = nfr_figure([], _runway(), reference=REF)
        assert len(fig.data) == 1


class TestCollectNfr:
    def _solution(self, tmp_path, name: str, register: NfrRegister):
        nfr_path = tmp_path / f"{name}_nfr.json"
        save_nfr(nfr_path, register)
        return SolutionConfig(
            name=name,
            members=[Member(name="ART 1", issue_times="dummy.xlsx")],
            nfr=str(nfr_path))

    def test_solution_entries_are_labelled(self, tmp_path) -> None:
        cfg = self._solution(tmp_path, "Solution A", NfrRegister(
            nfrs=[Nfr("N-1", "T", "t", "met")],
            runway=[RunwayItem("RW-1", "T", "gap")]))
        nfrs, runway = _collect_nfr(cfg, log=lambda m: None)
        assert [(s, n.nfr_id) for s, n in nfrs] == [("Solution A", "N-1")]
        assert [(s, r.item_id) for s, r in runway] == [("Solution A", "RW-1")]

    def test_solution_without_nfr_yields_empty(self) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")])
        assert _collect_nfr(cfg, log=lambda m: None) == ([], [])

    def test_portfolio_aggregates_member_registers(self, tmp_path) -> None:
        cfg_a = self._solution(tmp_path, "Solution A", NfrRegister(
            nfrs=[Nfr("A-1", "T", "t", "met")]))
        cfg_b = self._solution(tmp_path, "Solution B", NfrRegister(
            runway=[RunwayItem("B-1", "T", "building")]))
        path_a = tmp_path / "sol_a.json"
        path_b = tmp_path / "sol_b.json"
        save_solution_config(path_a, cfg_a)
        save_solution_config(path_b, cfg_b)
        portfolio = SolutionConfig(
            name="P", kind=KIND_PORTFOLIO,
            members=[Member(name="Solution A", template=str(path_a)),
                     Member(name="Solution B", template=str(path_b))])
        nfrs, runway = _collect_nfr(portfolio, log=lambda m: None)
        assert [(s, n.nfr_id) for s, n in nfrs] == [("Solution A", "A-1")]
        assert [(s, r.item_id) for s, r in runway] == [("Solution B", "B-1")]

    def test_broken_nfr_file_is_skipped_with_warning(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            nfr=str(bad))
        warnings: list[str] = []
        assert _collect_nfr(cfg, log=warnings.append) == ([], [])
        assert any("skipped" in w for w in warnings)
