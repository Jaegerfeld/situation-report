# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Dependency-Heatmap (B5): Grid-Bildung (nur offene
#   Abhängigkeiten, schwerster Status färbt die Zelle), HTML-/PDF-Rendering
#   (blocked zuerst, Overdue-Hervorhebung, Solution-Spalte, Titelzähler) und
#   das Einsammeln über die Config (_collect_dependencies inkl.
#   Fehlertoleranz).
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

from portfolio.aggregator import _collect_dependencies
from portfolio.dependency_config import (
    Dependency,
    DependencyRegister,
    save_dependencies,
)
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    save_solution_config,
)
from portfolio.summary import (
    _OVERDUE_COLOR,
    _heatmap_grid,
    dependency_figure,
    render_dependencies_html,
)

REF = date(2025, 6, 30)


def _entries() -> list[tuple[str, Dependency]]:
    return [
        ("Solution A", Dependency("D-2", "Fixtures", "ART 2", "ART 1",
                                  "on_track", due=REF + timedelta(days=20))),
        ("Solution A", Dependency("D-1", "API contract", "ART 1", "ART 3",
                                  "blocked", due=REF - timedelta(days=15))),
        ("Solution A", Dependency("D-3", "Old migration", "ART 2", "ART 3",
                                  "done", due=REF - timedelta(days=30))),
        ("Solution A", Dependency("D-4", "Feed", "ART 1", "ART 3",
                                  "at_risk", due=REF + timedelta(days=5))),
    ]


class TestHeatmapGrid:
    def test_open_dependencies_grouped_and_done_excluded(self) -> None:
        froms, tos, cells = _heatmap_grid(_entries())
        assert froms == ["ART 1", "ART 2"]
        assert tos == ["ART 1", "ART 3"]
        # D-3 (done) fehlt; D-1 + D-4 teilen sich die Zelle ART 1 -> ART 3.
        assert len(cells[("ART 1", "ART 3")]) == 2
        assert ("ART 2", "ART 3") not in cells


class TestRenderDependenciesHtml:
    def test_empty_entries_render_nothing(self) -> None:
        assert render_dependencies_html([]) == ""

    def test_orders_blocked_first_and_done_last(self) -> None:
        html = render_dependencies_html(_entries(), reference=REF)
        positions = [html.index(k) for k in ("D-1", "D-4", "D-2", "D-3")]
        assert positions == sorted(positions)

    def test_overdue_due_date_is_highlighted_but_not_done(self) -> None:
        html = render_dependencies_html(_entries(), reference=REF)
        rows = html.split("<tr>")
        blocked_row = next(r for r in rows if "D-1" in r)
        done_row = next(r for r in rows if "D-3" in r)
        assert "(overdue)" in blocked_row
        assert _OVERDUE_COLOR in blocked_row
        # done + verstrichenes due ist NICHT überfällig.
        assert "(overdue)" not in done_row

    def test_title_counts(self) -> None:
        html = render_dependencies_html(_entries(), reference=REF)
        assert "4 dependencies (1 blocked, 1 at risk, 1 overdue)" in html

    def test_heatmap_cell_shows_count(self) -> None:
        html = render_dependencies_html(_entries(), reference=REF)
        assert "needs \\ delivers" in html
        assert ">2</td>" in html  # ART 1 -> ART 3 buendelt D-1 + D-4

    def test_two_sources_add_solution_column(self) -> None:
        entries = _entries() + [
            ("Solution B", Dependency("B-1", "X", "ART 9", "ART 1", "on_track"))]
        html = render_dependencies_html(entries, reference=REF)
        assert "<th>Solution</th>" in html
        assert "<td>Solution B</td>" in html


class TestDependencyFigure:
    def test_figure_has_heatmap_and_detail_table(self) -> None:
        fig = dependency_figure(_entries(), reference=REF)
        assert len(fig.data) == 2
        heatmap, detail = fig.data
        assert list(heatmap.header.values) == ["needs \\ delivers", "ART 1", "ART 3"]
        assert list(detail.header.values) == [
            "Dependency", "From (needs)", "To (delivers)", "Status", "Due"]
        assert "4 dependencies (1 blocked, 1 at risk, 1 overdue)" \
            in fig.layout.title.text

    def test_detail_only_when_no_open_dependencies(self) -> None:
        done_only = [("S", Dependency("D-1", "T", "A", "B", "done"))]
        fig = dependency_figure(done_only)
        assert len(fig.data) == 1


class TestCollectDependencies:
    def _solution(self, tmp_path, name: str, deps: list[Dependency]):
        deps_path = tmp_path / f"{name}_deps.json"
        save_dependencies(deps_path, DependencyRegister(dependencies=deps))
        return SolutionConfig(
            name=name,
            members=[Member(name="ART 1", issue_times="dummy.xlsx")],
            dependencies=str(deps_path))

    def test_solution_entries_are_labelled(self, tmp_path) -> None:
        cfg = self._solution(tmp_path, "Solution A",
                             [Dependency("D-1", "T", "A", "B", "on_track")])
        entries = _collect_dependencies(cfg, log=lambda m: None)
        assert [(s, d.dep_id) for s, d in entries] == [("Solution A", "D-1")]

    def test_solution_without_dependencies_yields_empty(self) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")])
        assert _collect_dependencies(cfg, log=lambda m: None) == []

    def test_portfolio_aggregates_member_registers(self, tmp_path) -> None:
        cfg_a = self._solution(tmp_path, "Solution A",
                               [Dependency("A-1", "T", "A", "B", "on_track")])
        cfg_b = self._solution(tmp_path, "Solution B",
                               [Dependency("B-1", "T", "C", "A", "blocked")])
        path_a = tmp_path / "sol_a.json"
        path_b = tmp_path / "sol_b.json"
        save_solution_config(path_a, cfg_a)
        save_solution_config(path_b, cfg_b)
        portfolio = SolutionConfig(
            name="P", kind=KIND_PORTFOLIO,
            members=[Member(name="Solution A", template=str(path_a)),
                     Member(name="Solution B", template=str(path_b))])
        entries = _collect_dependencies(portfolio, log=lambda m: None)
        assert [(s, d.dep_id) for s, d in entries] == [
            ("Solution A", "A-1"), ("Solution B", "B-1")]

    def test_broken_dependencies_file_is_skipped_with_warning(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            dependencies=str(bad))
        warnings: list[str] = []
        assert _collect_dependencies(cfg, log=warnings.append) == []
        assert any("skipped" in w for w in warnings)
