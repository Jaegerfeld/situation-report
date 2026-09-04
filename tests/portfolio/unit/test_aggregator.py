# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       04.09.2026
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
from portfolio.solution_config import KIND_PORTFOLIO, Member, SolutionConfig, StageMap


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
    from pathlib import Path

    import plotly.graph_objects as go
    fig = go.Figure()
    unit = ReportData(issues=[_issue("ART_A", "ART_A-1", 1, 5)], source_prefix="Sol")
    captured: dict = {}
    monkeypatch.setattr(aggregator, "_collect_report",
                        lambda *a, **k: ([fig], {}, [unit], []))
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
    monkeypatch.setattr(aggregator, "_collect_report", lambda *a, **k: ([], {}, [], []))
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


# ---------------------------------------------------------------------------
# A4: pooling with a custom stage map
# ---------------------------------------------------------------------------

def _cfd_data(prefix: str, stages: list[str], counts: dict[str, int]) -> ReportData:
    from datetime import date

    from build_reports.loader import CfdRecord
    return ReportData(
        issues=[], stages=stages, source_prefix=prefix,
        cfd=[CfdRecord(day=date(2025, 1, 1), stage_counts=counts)])


class TestPoolCfdWithStageMap:
    def _map(self) -> StageMap:
        return StageMap(
            stages={"Backlog": ["Funnel"], "In Arbeit": ["Doing", "Review"],
                    "Fertig": ["Done"]},
            first_stage="In Arbeit", closed_stage="Fertig")

    def test_counts_sum_into_custom_stages(self) -> None:
        a = _cfd_data("A", ["Funnel", "Doing", "Done"],
                      {"Funnel": 2, "Doing": 3, "Done": 1})
        b = _cfd_data("B", ["Review", "Done"], {"Review": 4, "Done": 5})
        records = aggregator._pool_cfd([a, b], stage_map=self._map(),
                                       log=lambda m: None)
        assert records[0].stage_counts == {"Backlog": 2, "In Arbeit": 7, "Fertig": 6}

    def test_unmapped_stage_falls_back_with_single_warning(self) -> None:
        a = _cfd_data("A", ["Mystery"], {"Mystery": 3})
        b = _cfd_data("B", ["Mystery"], {"Mystery": 2})
        warnings: list[str] = []
        records = aggregator._pool_cfd([a, b], stage_map=self._map(),
                                       log=warnings.append)
        assert records[0].stage_counts["In Arbeit"] == 5
        assert sum("Mystery" in w for w in warnings) == 1

    def test_pooled_report_carries_custom_stages_and_markers(self, monkeypatch) -> None:
        data = _cfd_data("A", ["Funnel", "Done"], {"Funnel": 1, "Done": 2})
        monkeypatch.setattr(aggregator, "_load_member", lambda m: data)
        cfg = SolutionConfig(
            name="Sol", members=[Member("A", issue_times="A.xlsx")],
            stage_map=self._map())
        pooled = aggregator.build_pooled_report_data(cfg, log=lambda m: None)
        assert pooled.stages == ["Backlog", "In Arbeit", "Fertig"]
        assert pooled.first_stage == "In Arbeit"
        assert pooled.closed_stage == "Fertig"

    def test_without_map_keeps_three_groups(self, monkeypatch) -> None:
        data = _cfd_data("A", ["Funnel", "Done"], {"Funnel": 1, "Done": 2})
        monkeypatch.setattr(aggregator, "_load_member", lambda m: data)
        cfg = SolutionConfig(name="Sol", members=[Member("A", issue_times="A.xlsx")])
        pooled = aggregator.build_pooled_report_data(cfg, log=lambda m: None)
        assert len(pooled.stages) == 3


# ---------------------------------------------------------------------------
# ART-Tiefe (Drill-down): optionale Auswertung bis auf ART-Ebene
# ---------------------------------------------------------------------------

def _raise_if_called(*_args, **_kwargs):
    raise AssertionError("ARTs wurden unnoetig nachgeladen")


def _colliding_portfolio(monkeypatch) -> SolutionConfig:
    """Two solutions whose ARTs carry the SAME name — the collision case."""
    sol_a = SolutionConfig(name="Solution A",
                           members=[Member(name="ART Team A", issue_times="A1.xlsx")])
    sol_b = SolutionConfig(name="Solution B",
                           members=[Member(name="ART Team A", issue_times="B1.xlsx")])
    portfolio = SolutionConfig(name="Group", kind=KIND_PORTFOLIO, members=[
        Member(name="Solution A", template="solA.json"),
        Member(name="Solution B", template="solB.json")])
    rd = {p: ReportData(issues=[_issue(p, f"{p}-{n}", 1, 5 + n) for n in range(1, 4)],
                        stages=["Analysis", "Dev", "Done"], source_prefix=p)
          for p in ("A1.xlsx", "B1.xlsx")}
    monkeypatch.setattr(aggregator, "load_report_data", _fake_loader(rd))
    monkeypatch.setattr(aggregator, "load_solution_config",
                        _fake_solution_loader({"solA.json": sol_a, "solB.json": sol_b}))
    return portfolio


class TestArtUnits:
    """The drill-down granularity: one unit per ART, also for a portfolio."""

    def test_portfolio_units_are_arts_not_solutions(self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        units = aggregator.load_art_units(portfolio, log=lambda *_: None)
        assert [u.source_prefix for u in units] == [
            "Solution A · ART A1", "Solution A · ART A2",
            "Solution B · ART B1"]
        # Nichts ist mehr gepoolt: jeder ART bringt seine eigenen 3 Issues mit.
        assert [len(u.issues) for u in units] == [3, 3, 3]

    def test_solution_units_keep_the_plain_art_name(self, monkeypatch) -> None:
        cfg = _two_art_config()
        rd = {p: ReportData(issues=[_issue(p, f"{p}-1", 1, 6)], stages=["Done"],
                            source_prefix=p) for p in ("A.xlsx", "B.xlsx")}
        monkeypatch.setattr(aggregator, "load_report_data", _fake_loader(rd))
        units = aggregator.load_art_units(cfg, log=lambda *_: None)
        # Ohne Portfolio darueber gibt es nichts zu unterscheiden.
        assert [u.source_prefix for u in units] == ["ART Alpha", "ART Beta"]

    def test_same_art_name_in_two_solutions_stays_distinguishable(
            self, monkeypatch) -> None:
        """Ohne den Solution-Praefix wuerden beide Zeilen stillschweigend
        verschmelzen — gleiche Beschriftung, kollidierende Figurenlabels."""
        portfolio = _colliding_portfolio(monkeypatch)
        labels = [u.source_prefix
                  for u in aggregator.load_art_units(portfolio, log=lambda *_: None)]
        assert labels == ["Solution A · ART Team A",
                          "Solution B · ART Team A"]
        assert len(set(labels)) == 2

    def test_missing_transitions_are_named_not_swallowed(self, monkeypatch) -> None:
        """Process Flow braucht Uebergaenge; fehlen sie, muss das Protokoll
        sagen WELCHER ART betroffen ist."""
        portfolio = _portfolio_setup(monkeypatch)
        lines: list[str] = []
        aggregator.load_art_units(portfolio, log=lines.append)
        notes = [ln for ln in lines if "no transition data" in ln]
        assert len(notes) == 3
        assert "Solution A · ART A1" in notes[0]


class TestArtDepthMetricDefaults:
    """Die beiden workflow-gebundenen Analysen sind nur auf ART-Ebene ehrlich."""

    def test_art_depth_adds_the_process_flow_analyses(self) -> None:
        portfolio = SolutionConfig(name="P", kind=KIND_PORTFOLIO,
                                   members=[Member("S", template="s.json")])
        with_depth = aggregator._default_metrics(
            portfolio, aggregator.MODE_COMPARISON, art_depth=True)
        assert with_depth == aggregator.DEFAULT_ART_METRICS
        assert "process_flow" in with_depth and "process_flow_time" in with_depth

    def test_without_art_depth_the_defaults_are_untouched(self) -> None:
        portfolio = SolutionConfig(name="P", kind=KIND_PORTFOLIO,
                                   members=[Member("S", template="s.json")])
        solution = _two_art_config()
        assert aggregator._default_metrics(
            portfolio,
            aggregator.MODE_COMPARISON) == aggregator.DEFAULT_POOLED_METRICS
        assert aggregator._default_metrics(
            solution,
            aggregator.MODE_COMPARISON) == aggregator.DEFAULT_COMPARISON_METRICS
        # Gepoolt bleibt gepoolt — auch mit ART-Tiefe.
        assert aggregator._default_metrics(
            portfolio, aggregator.MODE_POOLED,
            art_depth=True) == aggregator.DEFAULT_POOLED_METRICS


class TestArtDepthInReports:
    """Eine Regel, zwei Reichweiten: die Tabellen zaehlen immer ARTs auf,
    die Figuren nur im Vergleichsmodus."""

    def test_comparison_figures_are_per_art(self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        html = aggregator.render_comparison_html(
            portfolio, metrics=["flow_time"], log=lambda *_: None, art_depth=True)
        assert "Solution A · ART A1" in html
        assert "Solution B · ART B1" in html

    def test_comparison_without_depth_still_compares_solutions(
            self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        html = aggregator.render_comparison_html(
            portfolio, metrics=["flow_time"], log=lambda *_: None)
        assert "ART A1" not in html
        assert "ART Detail" not in html

    def test_pooled_keeps_pooled_figures_and_adds_the_art_tables(
            self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        html = aggregator.render_pooled_html(
            portfolio, metrics=["flow_time"], log=lambda *_: None, art_depth=True)
        assert "ART Detail — Management Summary per ART" in html
        assert "ART Detail — Data Quality per ART" in html
        assert "Solution A · ART A1" in html

    def test_solution_comparison_does_not_repeat_itself(self, monkeypatch) -> None:
        """Eine Solution vergleicht ohnehin ihre ARTs — der Zusatzblock waere
        eine wortgleiche Wiederholung und bleibt darum aus."""
        cfg = _two_art_config()
        rd = {p: ReportData(issues=[_issue(p, f"{p}-1", 1, 6)], stages=["Done"],
                            source_prefix=p) for p in ("A.xlsx", "B.xlsx")}
        monkeypatch.setattr(aggregator, "load_report_data", _fake_loader(rd))
        html = aggregator.render_comparison_html(
            cfg, metrics=["flow_time"], log=lambda *_: None, art_depth=True)
        assert "ART Detail" not in html

    def test_redundant_drill_down_costs_no_file_access(self, monkeypatch) -> None:
        """Der Verzicht wird aus der Konfiguration entschieden — ohne die
        ARTs vorher ein zweites Mal von der Platte zu lesen."""
        cfg = _two_art_config()
        monkeypatch.setattr(aggregator, "load_art_units", _raise_if_called)
        assert aggregator._art_detail_units(
            cfg, ["ART Alpha", "ART Beta"], log=lambda *_: None) == []

    def test_conference_pre_read_carries_the_art_detail(self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        html = aggregator.render_conference_html(
            portfolio, log=lambda *_: None, art_depth=True)
        assert "Input 1 · Aktuelle Daten" in html
        assert "ART Detail — Management Summary per ART" in html
        assert "Solution B · ART B1" in html

    def test_conference_pre_read_unchanged_when_off(self, monkeypatch) -> None:
        portfolio = _portfolio_setup(monkeypatch)
        html = aggregator.render_conference_html(portfolio, log=lambda *_: None)
        assert "ART Detail" not in html
