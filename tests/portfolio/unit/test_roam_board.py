# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das ROAM-Board (B3): HTML-/PDF-Rendering (Sortierung,
#   Solution-Spalte nur im Portfolio-Fall, Aging-Hervorhebung, Titelzähler)
#   und das Einsammeln der Register über die Solution-/Portfolio-Config
#   (_collect_risks inkl. Fehlertoleranz bei kaputten Dateien).
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

from portfolio.aggregator import _collect_risks
from portfolio.risks_config import Risk, RiskRegister, save_risks
from portfolio.solution_config import (
    KIND_PORTFOLIO,
    Member,
    SolutionConfig,
    save_solution_config,
)
from portfolio.summary import (
    _AGING_COLOR,
    _RISK_AGING_DAYS,
    render_roam_html,
    roam_figure,
)

REF = date(2025, 6, 30)


def _entries() -> list[tuple[str, Risk]]:
    """Unordered sample entries from one source (fresh + aging owned risk)."""
    return [
        ("Solution A", Risk("R-3", "Accepted thing", "accepted", impact="low")),
        ("Solution A", Risk("R-1", "Old owned thing", "owned", owner="Team X",
                            impact="medium",
                            status_since=REF - timedelta(days=_RISK_AGING_DAYS + 10))),
        ("Solution A", Risk("R-2", "Fresh owned thing", "owned", owner="Team Y",
                            status_since=REF - timedelta(days=3))),
        ("Solution A", Risk("R-4", "Fixed thing", "resolved")),
    ]


class TestRenderRoamHtml:
    def test_empty_entries_render_nothing(self) -> None:
        assert render_roam_html([]) == ""

    def test_single_source_has_no_solution_column(self) -> None:
        html = render_roam_html(_entries(), reference=REF)
        assert "<th>Solution</th>" not in html
        assert "<th>ROAM</th>" in html
        assert "<th>Owner (team)</th>" in html

    def test_rows_follow_roam_order(self) -> None:
        html = render_roam_html(_entries(), reference=REF)
        positions = [html.index(k) for k in ("R-4", "R-1", "R-2", "R-3")]
        assert positions == sorted(positions)  # resolved, owned(high, fresh), accepted

    def test_aging_owned_risk_is_highlighted(self) -> None:
        html = render_roam_html(_entries(), reference=REF)
        rows = html.split("<tr>")
        aging_row = next(r for r in rows if "R-1" in r)
        fresh_row = next(r for r in rows if "R-2" in r)
        assert _AGING_COLOR in aging_row
        assert _AGING_COLOR not in fresh_row

    def test_title_counts_total_owned_and_aging(self) -> None:
        html = render_roam_html(_entries(), reference=REF)
        assert "4 risks, 2 owned" in html
        assert f"1 owned &gt; {_RISK_AGING_DAYS}d" in html

    def test_two_sources_add_solution_column(self) -> None:
        entries = _entries() + [("Solution B", Risk("R-9", "Other", "owned"))]
        html = render_roam_html(entries, reference=REF)
        assert "<th>Solution</th>" in html
        assert "<td>Solution B</td>" in html


class TestRoamFigure:
    def test_figure_mirrors_html(self) -> None:
        fig = roam_figure(_entries(), reference=REF)
        table = fig.data[0]
        assert list(table.header.values) == [
            "ROAM", "Risk", "Impact", "Owner (team)", "Since"]
        assert len(table.cells.values[0]) == 4
        assert "4 risks, 2 owned" in fig.layout.title.text
        # Aging highlight sits in the Since column of the aging risk's row.
        assert _AGING_COLOR in list(table.cells.fill.color[4])


class TestCollectRisks:
    def _solution(self, tmp_path, name: str, risks: list[Risk]):
        risks_path = tmp_path / f"{name}_risks.json"
        save_risks(risks_path, RiskRegister(risks=risks))
        cfg = SolutionConfig(
            name=name,
            members=[Member(name="ART 1", issue_times="dummy.xlsx")],
            risks=str(risks_path))
        return cfg

    def test_solution_risks_are_labelled_with_solution_name(self, tmp_path) -> None:
        cfg = self._solution(tmp_path, "Solution A",
                             [Risk("R-1", "T", "owned")])
        entries = _collect_risks(cfg, log=lambda m: None)
        assert len(entries) == 1
        assert entries[0][0] == "Solution A"
        assert entries[0][1].risk_id == "R-1"

    def test_solution_without_risks_yields_empty(self) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")])
        assert _collect_risks(cfg, log=lambda m: None) == []

    def test_portfolio_aggregates_member_solution_risks(self, tmp_path) -> None:
        cfg_a = self._solution(tmp_path, "Solution A", [Risk("A-1", "T", "owned")])
        cfg_b = self._solution(tmp_path, "Solution B", [Risk("B-1", "T", "resolved")])
        path_a = tmp_path / "sol_a.json"
        path_b = tmp_path / "sol_b.json"
        save_solution_config(path_a, cfg_a)
        save_solution_config(path_b, cfg_b)
        portfolio = SolutionConfig(
            name="P", kind=KIND_PORTFOLIO,
            members=[Member(name="Solution A", template=str(path_a)),
                     Member(name="Solution B", template=str(path_b))])
        entries = _collect_risks(portfolio, log=lambda m: None)
        assert [(s, r.risk_id) for s, r in entries] == [
            ("Solution A", "A-1"), ("Solution B", "B-1")]

    def test_broken_risks_file_is_skipped_with_warning(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            risks=str(bad))
        warnings: list[str] = []
        entries = _collect_risks(cfg, log=warnings.append)
        assert entries == []
        assert any("skipped" in w for w in warnings)

    def test_missing_risks_file_is_skipped_with_warning(self, tmp_path) -> None:
        cfg = SolutionConfig(
            name="S", members=[Member(name="A", issue_times="x.xlsx")],
            risks=str(tmp_path / "absent.json"))
        warnings: list[str] = []
        assert _collect_risks(cfg, log=warnings.append) == []
        assert any("skipped" in w for w in warnings)
