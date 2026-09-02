# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Capability-Map-Darstellung (B1): HTML-/PDF-Rendering
#   (kritisch zuerst, Solution-Spalte, Uncovered-Hervorhebung, Titelzähler)
#   und das Einsammeln über die Config (_collect_capabilities inkl.
#   Fehlertoleranz und Warnung bei unbekannten ART-Namen).
# =============================================================================

from __future__ import annotations

from portfolio.aggregator import _collect_capabilities
from portfolio.capability_config import (
    Capability,
    CapabilityMap,
    save_capabilities,
)
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    save_solution_config,
)
from portfolio.summary import (
    _UNCOVERED_COLOR,
    capability_figure,
    render_capabilities_html,
)


def _entries() -> list[tuple[str, Capability]]:
    return [
        ("Solution A", Capability("C-2", "Fine thing", "healthy",
                                  arts=["ART 1"])),
        ("Solution A", Capability("C-1", "Broken thing", "critical",
                                  arts=["ART 2"], owner="Team X")),
        ("Solution A", Capability("C-3", "Watch thing", "at_risk",
                                  arts=["ART 1", "ART 2"])),
        ("Solution A", Capability("C-4", "Orphan thing", "healthy")),
    ]


class TestRenderCapabilitiesHtml:
    def test_empty_entries_render_nothing(self) -> None:
        assert render_capabilities_html([]) == ""

    def test_orders_critical_first(self) -> None:
        html = render_capabilities_html(_entries())
        positions = [html.index(k) for k in ("C-1", "C-3", "C-2", "C-4")]
        assert positions == sorted(positions)

    def test_uncovered_capability_is_flagged(self) -> None:
        html = render_capabilities_html(_entries())
        rows = html.split("<tr>")
        orphan_row = next(r for r in rows if "C-4" in r)
        covered_row = next(r for r in rows if "C-2" in r)
        assert _UNCOVERED_COLOR in orphan_row
        assert _UNCOVERED_COLOR not in covered_row

    def test_title_counts(self) -> None:
        html = render_capabilities_html(_entries())
        assert "4 capabilities (1 critical, 1 at risk), 1 uncovered" in html

    def test_single_source_hides_solution_column(self) -> None:
        assert "<th>Solution</th>" not in render_capabilities_html(_entries())

    def test_two_sources_add_solution_column(self) -> None:
        entries = _entries() + [
            ("Solution B", Capability("B-1", "Other", "healthy", arts=["X"]))]
        html = render_capabilities_html(entries)
        assert "<th>Solution</th>" in html
        assert "<td>Solution B</td>" in html


class TestCapabilityFigure:
    def test_figure_mirrors_html(self) -> None:
        fig = capability_figure(_entries())
        table = fig.data[0]
        assert list(table.header.values) == [
            "Capability", "Health", "Contributing ARTs", "Owner (team)",
            "Assessed"]
        assert len(table.cells.values[0]) == 4
        assert "4 capabilities (1 critical, 1 at risk), 1 uncovered" \
            in fig.layout.title.text
        # Uncovered flag sits in the ARTs column of the orphan's row (last —
        # healthy sorts after critical/at_risk, id C-4 after C-2).
        assert list(table.cells.fill.color[2])[-1] == _UNCOVERED_COLOR


class TestCollectCapabilities:
    def _solution(self, tmp_path, name: str, caps: list[Capability],
                  member_names: list[str] | None = None):
        caps_path = tmp_path / f"{name}_caps.json"
        save_capabilities(caps_path, CapabilityMap(capabilities=caps))
        members = [Member(name=m, issue_times="dummy.xlsx")
                   for m in (member_names or ["ART 1"])]
        return SolutionConfig(name=name, members=members,
                              capabilities=str(caps_path))

    def test_solution_entries_are_labelled(self, tmp_path) -> None:
        cfg = self._solution(tmp_path, "Solution A",
                             [Capability("C-1", "T", "healthy", arts=["ART 1"])])
        entries = _collect_capabilities(cfg, log=lambda m: None)
        assert [(s, c.cap_id) for s, c in entries] == [("Solution A", "C-1")]

    def test_solution_without_capabilities_yields_empty(self) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")])
        assert _collect_capabilities(cfg, log=lambda m: None) == []

    def test_unknown_art_name_logs_warning_but_keeps_entry(self, tmp_path) -> None:
        cfg = self._solution(
            tmp_path, "Solution A",
            [Capability("C-1", "T", "healthy", arts=["ART 1", "Ghost ART"])],
            member_names=["ART 1"])
        warnings: list[str] = []
        entries = _collect_capabilities(cfg, log=warnings.append)
        assert len(entries) == 1
        assert any("unknown ARTs" in w and "Ghost ART" in w for w in warnings)

    def test_portfolio_aggregates_member_maps(self, tmp_path) -> None:
        cfg_a = self._solution(tmp_path, "Solution A",
                               [Capability("A-1", "T", "healthy", arts=["ART 1"])])
        cfg_b = self._solution(tmp_path, "Solution B",
                               [Capability("B-1", "T", "critical", arts=["ART 1"])])
        path_a = tmp_path / "sol_a.json"
        path_b = tmp_path / "sol_b.json"
        save_solution_config(path_a, cfg_a)
        save_solution_config(path_b, cfg_b)
        portfolio = SolutionConfig(
            name="P", kind=KIND_PORTFOLIO,
            members=[Member(name="Solution A", template=str(path_a)),
                     Member(name="Solution B", template=str(path_b))])
        entries = _collect_capabilities(portfolio, log=lambda m: None)
        assert [(s, c.cap_id) for s, c in entries] == [
            ("Solution A", "A-1"), ("Solution B", "B-1")]

    def test_broken_capabilities_file_is_skipped_with_warning(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            capabilities=str(bad))
        warnings: list[str] = []
        assert _collect_capabilities(cfg, log=warnings.append) == []
        assert any("skipped" in w for w in warnings)
