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

from datetime import date, datetime

from build_reports.loader import CfdRecord, IssueRecord, ReportData

from portfolio import aggregator
from portfolio.solution_config import KIND_PORTFOLIO, Member, SolutionConfig


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
    # pooled stages are the canonical groups (shared mapping for CFD)
    assert pooled.stages == ["To Do", "In Progress", "Done"]
    assert pooled.first_stage == "In Progress" and pooled.closed_stage == "Done"


def test_cfd_pooled_via_canonical_stage_mapping(monkeypatch) -> None:
    day = date(2025, 1, 6)
    # Two ARTs with DIFFERENT workflows; classify_stages maps each stage into
    # To Do / In Progress / Done and the daily entry counts are summed per group.
    data_a = ReportData(
        issues=[_issue("ART_A", "ART_A-1", 1, 5)],
        cfd=[CfdRecord(day=day,
                       stage_counts={"Funnel": 2, "Analysis": 1, "Dev": 0, "Done": 0})],
        stages=["Funnel", "Analysis", "Dev", "Done"], source_prefix="ART_A",
        first_stage="Analysis", closed_stage="Done")
    data_b = ReportData(
        issues=[_issue("ART_B", "ART_B-1", 1, 5)],
        cfd=[CfdRecord(day=day, stage_counts={"Backlog": 1, "InProg": 3, "Released": 2})],
        stages=["Backlog", "InProg", "Released"], source_prefix="ART_B",
        first_stage="InProg", closed_stage="Released")
    monkeypatch.setattr(aggregator, "load_report_data",
                        _fake_loader({"A.xlsx": data_a, "B.xlsx": data_b}))

    pooled = aggregator.build_pooled_report_data(_two_art_config(), log=lambda *_: None)

    assert pooled.stages == ["To Do", "In Progress", "Done"]
    assert len(pooled.cfd) == 1
    # A: Funnel(2)→To Do, Analysis(1)→In Progress; B: Backlog(1)→To Do,
    # InProg(3)→In Progress, Released(2)→Done.
    assert pooled.cfd[0].stage_counts == {"To Do": 3, "In Progress": 4, "Done": 2}


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


def test_default_metric_sets() -> None:
    # Flow Distribution pools cleanly → in both defaults.
    assert "flow_distribution" in aggregator.DEFAULT_POOLED_METRICS
    assert "flow_distribution" in aggregator.DEFAULT_COMPARISON_METRICS
    # Flow Load is stage-dependent → only the comparison default (not pooled).
    assert "flow_load" not in aggregator.DEFAULT_POOLED_METRICS
    assert "flow_load" in aggregator.DEFAULT_COMPARISON_METRICS
    # CFD is poolable via the canonical stage mapping → in both defaults.
    assert "cfd" in aggregator.DEFAULT_POOLED_METRICS
    assert "cfd" in aggregator.DEFAULT_COMPARISON_METRICS


def test_pooled_default_includes_flow_distribution(monkeypatch) -> None:
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

    assert "Flow Distribution" in html


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


# ---------------------------------------------------------------------------
# Portfolio nesting (Phase 3): a portfolio references solution templates.
# ---------------------------------------------------------------------------

def test_render_pdf_prepends_summary_and_exports(monkeypatch) -> None:
    import plotly.graph_objects as go
    from pathlib import Path
    fig = go.Figure()
    unit = ReportData(issues=[_issue("ART_A", "ART_A-1", 1, 5)], source_prefix="Sol")
    captured: dict = {}
    monkeypatch.setattr(aggregator, "_collect_report",
                        lambda *a, **k: ([fig], {}, [unit]))
    monkeypatch.setattr(aggregator, "export_pdf",
                        lambda pages, path: captured.update(pages=pages, path=str(path)))

    ok = aggregator.render_pdf(
        SolutionConfig(name="Sol", members=[Member("A", issue_times="A.xlsx")]),
        Path("out.pdf"), log=lambda *_: None)

    assert ok is True
    # First page is the summary (a Table figure), then the metric figure.
    assert len(captured["pages"]) == 2
    assert captured["pages"][1] is fig
    assert captured["pages"][0].data[0].type == "table"


def test_render_pdf_no_figures_returns_false(monkeypatch) -> None:
    from pathlib import Path
    monkeypatch.setattr(aggregator, "_collect_report", lambda *a, **k: ([], {}, []))
    ok = aggregator.render_pdf(
        SolutionConfig(name="X", members=[Member("A", issue_times="A.xlsx")]),
        Path("out.pdf"), log=lambda *_: None)
    assert ok is False


def _fake_solution_loader(by_path: dict[str, SolutionConfig]):
    """Return a load_solution_config replacement keyed by template path string."""
    def _load(path):
        return by_path[str(path)]
    return _load


def _portfolio_setup(monkeypatch) -> SolutionConfig:
    """Wire up a portfolio of two solutions (3 ARTs total) with mocked loaders."""
    sol_a = SolutionConfig(name="Solution A", members=[
        Member(name="ART A1", issue_times="A1.xlsx"),
        Member(name="ART A2", issue_times="A2.xlsx")])
    sol_b = SolutionConfig(name="Solution B", members=[
        Member(name="ART B1", issue_times="B1.xlsx")])
    portfolio = SolutionConfig(name="Group Portfolio", kind=KIND_PORTFOLIO, members=[
        Member(name="Solution A", template="solA.json"),
        Member(name="Solution B", template="solB.json")])

    rd = {p: ReportData(issues=[_issue(p, f"{p}-{n}", 1, 5 + n) for n in range(1, 4)],
                        stages=["Analysis", "Dev", "Done"], source_prefix=p)
          for p in ("A1.xlsx", "A2.xlsx", "B1.xlsx")}
    monkeypatch.setattr(aggregator, "load_report_data", _fake_loader(rd))
    monkeypatch.setattr(aggregator, "load_solution_config",
                        _fake_solution_loader({"solA.json": sol_a, "solB.json": sol_b}))
    return portfolio


def test_iter_art_members_flattens_portfolio(monkeypatch) -> None:
    portfolio = _portfolio_setup(monkeypatch)
    arts = aggregator._iter_art_members(portfolio)
    assert [m.name for m in arts] == ["ART A1", "ART A2", "ART B1"]


def test_pooled_portfolio_pools_all_arts(monkeypatch) -> None:
    portfolio = _portfolio_setup(monkeypatch)
    pooled = aggregator.build_pooled_report_data(portfolio, log=lambda *_: None)
    assert len(pooled.issues) == 9          # 3 ARTs × 3 issues
    assert pooled.source_prefix == "Group Portfolio"


def test_comparison_units_are_per_solution(monkeypatch) -> None:
    portfolio = _portfolio_setup(monkeypatch)
    units = aggregator.load_comparison_units(portfolio, log=lambda *_: None)
    # one unit per member solution, labelled with the solution name
    assert [u.source_prefix for u in units] == ["Solution A", "Solution B"]
    # Solution A pooled its two ARTs (6 issues); Solution B has one ART (3)
    assert [len(u.issues) for u in units] == [6, 3]


def test_comparison_html_groups_by_solution(monkeypatch) -> None:
    portfolio = _portfolio_setup(monkeypatch)
    html = aggregator.render_comparison_html(portfolio, log=lambda *_: None)
    assert html
    assert "Solution A" in html and "Solution B" in html
