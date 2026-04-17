# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für FlowVelocityMetric. Prüft Aggregation nach Tag/Woche/PI,
#   Ausschluss von Issues ohne Closed Date sowie Render-Ausgabe.
# =============================================================================

from datetime import datetime

import pytest

from build_reports.loader import IssueRecord, ReportData
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.terminology import SAFE


def _issue(key: str, closed: datetime | None) -> IssueRecord:
    return IssueRecord(
        project="P", key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=datetime(2025, 1, 2), implementation_date=None,
        closed_date=closed, stage_minutes={}, resolution="",
    )


@pytest.fixture
def metric():
    return FlowVelocityMetric()


@pytest.fixture
def data_5_issues():
    """Five issues closed across different days in the same week."""
    return ReportData(
        issues=[
            _issue("A-1", datetime(2025, 3, 3)),   # Mon
            _issue("A-2", datetime(2025, 3, 3)),   # Mon (same day as A-1)
            _issue("A-3", datetime(2025, 3, 5)),   # Wed
            _issue("A-4", datetime(2025, 3, 10)),  # Mon next week
            _issue("A-5", None),                   # no closed date — excluded
        ],
        cfd=[], stages=[], source_prefix="TEST",
    )


class TestCompute:
    def test_count_excludes_no_closed_date(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        assert result.stats["count"] == 4

    def test_daily_freq_two_on_same_day(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        freq = result.chart_data.daily_freq
        # Two items on 2025-03-03 → freq[2] = 1
        assert freq.get(2, 0) == 1

    def test_weekly_groups_correctly(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        weekly = result.chart_data.weekly
        # 2025-W10 (Mar 3+5) = 3 items, 2025-W11 (Mar 10) = 1 item
        assert sum(weekly.values()) == 4

    def test_warning_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_warning_when_all_open(self, metric):
        data = ReportData(
            issues=[_issue("X", None)],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        assert result.metric_id == "flow_velocity"


class TestPiIntervals:
    def test_default_uses_quarterly_intervals(self, metric, data_5_issues):
        """Without pi_config_path, quarterly intervals are generated."""
        result = metric.compute(data_5_issues, SAFE)
        pi_intervals = result.chart_data.pi_intervals
        assert len(pi_intervals) > 0
        # All interval names follow the "YYYY QN" pattern
        for iv in pi_intervals:
            assert "Q" in iv.name

    def test_per_pi_keys_match_interval_names(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        expected_names = {iv.name for iv in result.chart_data.pi_intervals}
        actual_names = set(result.chart_data.per_pi.keys())
        assert actual_names == expected_names

    def test_per_pi_counts_sum_to_issue_count(self, metric, data_5_issues):
        """Total items across all PIs equals the count of issues with Closed Date."""
        result = metric.compute(data_5_issues, SAFE)
        total = sum(result.chart_data.per_pi.values())
        assert total == result.stats["count"]

    def test_custom_pi_config_loaded(self, metric, tmp_path):
        """When pi_config_path is set, custom intervals are used."""
        import json
        cfg = tmp_path / "pi.json"
        cfg.write_text(json.dumps({
            "mode": "date",
            "intervals": [
                {"name": "My PI 1", "from": "2025-01-01", "to": "2025-06-30"},
                {"name": "My PI 2", "from": "2025-07-01", "to": "2025-12-31"},
            ],
        }), encoding="utf-8")

        metric.pi_config_path = str(cfg)
        data = ReportData(
            issues=[
                _issue("X-1", datetime(2025, 2, 1)),
                _issue("X-2", datetime(2025, 8, 1)),
            ],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.chart_data.per_pi.get("My PI 1") == 1
        assert result.chart_data.per_pi.get("My PI 2") == 1

    def test_invalid_pi_config_path_falls_back_to_quarters(self, metric, data_5_issues):
        """An invalid path produces a warning and falls back to quarterly intervals."""
        metric.pi_config_path = "/nonexistent/path.json"
        result = metric.compute(data_5_issues, SAFE)
        assert any("PI config" in w for w in result.warnings)
        # Still produces chart data with quarterly intervals
        assert result.chart_data is not None
        assert len(result.chart_data.pi_intervals) > 0

    def test_unassigned_issues_produce_warning(self, metric, tmp_path):
        """Issues that fall outside all intervals generate a warning."""
        import json
        cfg = tmp_path / "pi.json"
        cfg.write_text(json.dumps({
            "mode": "date",
            "intervals": [
                {"name": "Q1 2025", "from": "2025-01-01", "to": "2025-03-31"},
            ],
        }), encoding="utf-8")
        metric.pi_config_path = str(cfg)
        data = ReportData(
            issues=[
                _issue("A", datetime(2025, 2, 1)),   # inside
                _issue("B", datetime(2025, 7, 1)),   # outside
            ],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert any("not covered" in w for w in result.warnings)


class TestRender:
    def test_returns_three_figures(self, metric, data_5_issues):
        result = metric.compute(data_5_issues, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 3

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=[], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []

    def test_pi_chart_xaxis_title_is_quarter_for_default(self, metric, data_5_issues):
        metric.pi_config_path = ""
        result = metric.compute(data_5_issues, SAFE)
        figs = metric.render(result, SAFE)
        pi_fig = figs[2]
        assert pi_fig.layout.xaxis.title.text == "Quarter"

    def test_pi_chart_xaxis_title_is_pi_for_custom_config(self, metric, tmp_path):
        import json
        cfg = tmp_path / "pi.json"
        cfg.write_text(json.dumps({
            "mode": "date",
            "intervals": [{"name": "PI 1", "from": "2025-01-01", "to": "2025-12-31"}],
        }), encoding="utf-8")
        metric.pi_config_path = str(cfg)
        data = ReportData(
            issues=[_issue("X", datetime(2025, 3, 1))],
            cfd=[], stages=[], source_prefix="",
        )
        result = metric.compute(data, SAFE)
        figs = metric.render(result, SAFE)
        pi_fig = figs[2]
        assert pi_fig.layout.xaxis.title.text == "PI"
