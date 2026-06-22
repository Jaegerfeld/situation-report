# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.aggregator: Record-Level-Pooling mehrerer ARTs in
#   ein ReportData sowie End-to-End-Erzeugung des gepoolten HTML-Reports. Der
#   build_reports-Loader wird gemockt, sodass keine echten XLSX nötig sind.
# =============================================================================

from __future__ import annotations

from datetime import datetime

from build_reports.loader import IssueRecord, ReportData

from portfolio import aggregator
from portfolio.solution_config import Member, SolutionConfig


def _issue(project: str, key: str, first_day: int, closed_day: int) -> IssueRecord:
    """Build a minimal closed IssueRecord (Jan 2025) with a non-zero cycle time."""
    return IssueRecord(
        project=project,
        key=key,
        issuetype="Feature",
        status="Done",
        created=datetime(2025, 1, first_day, 8, 0, 0),
        component="",
        first_date=datetime(2025, 1, first_day, 8, 0, 0),
        implementation_date=None,
        closed_date=datetime(2025, 1, closed_day, 8, 0, 0),
        stage_minutes={"Dev": 1000},
        resolution="Done",
    )


def _fake_loader(by_path: dict[str, ReportData]):
    """Return a load_report_data replacement keyed by the issue_times path string."""
    def _load(issue_times, cfd=None, workflow=None, transitions=None):
        return by_path[str(issue_times)]
    return _load


def _two_art_config() -> SolutionConfig:
    return SolutionConfig(
        name="Payments Solution",
        members=[
            Member(name="ART Alpha", issue_times="A.xlsx"),
            Member(name="ART Beta", issue_times="B.xlsx"),
        ],
    )


def test_pooling_concatenates_records(monkeypatch) -> None:
    data_a = ReportData(
        issues=[_issue("ART_A", "ART_A-1", 1, 10), _issue("ART_A", "ART_A-2", 2, 12)],
        stages=["Analysis", "Dev", "Done"], source_prefix="ART_A",
    )
    data_b = ReportData(
        issues=[_issue("ART_B", "ART_B-1", 3, 9)],
        stages=["Dev", "Done", "Released"], source_prefix="ART_B",
    )
    monkeypatch.setattr(
        aggregator, "load_report_data",
        _fake_loader({"A.xlsx": data_a, "B.xlsx": data_b}),
    )

    pooled = aggregator.build_pooled_report_data(_two_art_config(), log=lambda *_: None)

    assert len(pooled.issues) == 3
    assert {i.key for i in pooled.issues} == {"ART_A-1", "ART_A-2", "ART_B-1"}
    # source_prefix becomes the solution name → figures get the solution label
    assert pooled.source_prefix == "Payments Solution"
    # stages unioned in first-seen order, no duplicates
    assert pooled.stages == ["Analysis", "Dev", "Done", "Released"]


def test_resolve_member_paths_direct() -> None:
    paths = aggregator._resolve_member_paths(
        Member(name="ART Alpha", issue_times="A.xlsx", cfd="A_CFD.xlsx")
    )
    assert str(paths["issue_times"]) == "A.xlsx"
    assert str(paths["cfd"]) == "A_CFD.xlsx"
    assert paths["workflow"] is None and paths["transitions"] is None


def test_load_members_labels_each_separately(monkeypatch) -> None:
    data_a = ReportData(issues=[_issue("ART_A", "ART_A-1", 1, 10)],
                         stages=["Dev", "Done"], source_prefix="ART_A")
    data_b = ReportData(issues=[_issue("ART_B", "ART_B-1", 3, 9)],
                        stages=["Dev", "Done"], source_prefix="ART_B")
    monkeypatch.setattr(
        aggregator, "load_report_data",
        _fake_loader({"A.xlsx": data_a, "B.xlsx": data_b}),
    )

    members = aggregator.load_members(_two_art_config(), log=lambda *_: None)

    # Not pooled: one ReportData per member, each labelled with the member name
    assert len(members) == 2
    assert [m.source_prefix for m in members] == ["ART Alpha", "ART Beta"]
    assert [len(m.issues) for m in members] == [1, 1]


def test_render_comparison_html_groups_by_metric(monkeypatch) -> None:
    data_a = ReportData(
        issues=[_issue("ART_A", f"ART_A-{n}", 1, 5 + n) for n in range(1, 6)],
        stages=["Analysis", "Dev", "Done"], source_prefix="ART_A",
    )
    data_b = ReportData(
        issues=[_issue("ART_B", f"ART_B-{n}", 2, 6 + n) for n in range(1, 6)],
        stages=["Analysis", "Dev", "Done"], source_prefix="ART_B",
    )
    monkeypatch.setattr(
        aggregator, "load_report_data",
        _fake_loader({"A.xlsx": data_a, "B.xlsx": data_b}),
    )

    html = aggregator.render_comparison_html(_two_art_config(), log=lambda *_: None)

    assert html
    # Both ART names appear (figures labelled per ART via source_prefix)
    assert "ART Alpha" in html and "ART Beta" in html
    # The solution name is NOT used as a figure label in comparison mode
    assert "Payments Solution" not in html


def test_render_pooled_html_endtoend(monkeypatch) -> None:
    data_a = ReportData(
        issues=[_issue("ART_A", f"ART_A-{n}", 1, 5 + n) for n in range(1, 6)],
        stages=["Analysis", "Dev", "Done"], source_prefix="ART_A",
    )
    data_b = ReportData(
        issues=[_issue("ART_B", f"ART_B-{n}", 2, 6 + n) for n in range(1, 6)],
        stages=["Analysis", "Dev", "Done"], source_prefix="ART_B",
    )
    monkeypatch.setattr(
        aggregator, "load_report_data",
        _fake_loader({"A.xlsx": data_a, "B.xlsx": data_b}),
    )

    html = aggregator.render_pooled_html(_two_art_config(), log=lambda *_: None)

    assert html  # non-empty HTML document
    assert "<html" in html.lower()
    # The solution name is injected as the figure-title prefix (source_prefix)
    assert "Payments Solution" in html
