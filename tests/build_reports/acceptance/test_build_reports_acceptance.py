# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Acceptance-Tests für build_reports gegen den realen ART_A-Datensatz.
#   Prüft, dass loader, filters und alle Metrik-Plugins mit echten Daten
#   korrekt funktionieren: sinnvolle Statistikwerte, vollständige Datenladung,
#   renderfähige Figures.
# =============================================================================

from datetime import date
from pathlib import Path

import pytest

from build_reports.export import export_pdf, export_png
from build_reports.filters import FilterConfig, apply_filters
from build_reports.loader import load_report_data
from build_reports.metrics.cfd import CfdMetric
from build_reports.metrics.flow_distribution import FlowDistributionMetric
from build_reports.metrics.flow_load import FlowLoadMetric
from build_reports.metrics.flow_time import FlowTimeMetric
from build_reports.metrics.flow_velocity import FlowVelocityMetric
from build_reports.terminology import SAFE

TRANSFORM_DIR = Path(__file__).parent.parent.parent.parent / "transform_data"
ISSUE_TIMES = TRANSFORM_DIR / "ART_A_IssueTimes.xlsx"
CFD = TRANSFORM_DIR / "ART_A_CFD.xlsx"


@pytest.fixture(scope="module")
def art_a_data():
    """Load the real ART_A dataset once for all acceptance tests."""
    return load_report_data(ISSUE_TIMES, CFD)


class TestLoader:
    def test_loads_issues(self, art_a_data):
        assert len(art_a_data.issues) > 0

    def test_loads_cfd(self, art_a_data):
        assert len(art_a_data.cfd) > 0

    def test_stages_not_empty(self, art_a_data):
        assert len(art_a_data.stages) > 0

    def test_source_prefix(self, art_a_data):
        assert art_a_data.source_prefix == "ART_A"

    def test_issues_have_keys(self, art_a_data):
        assert all(i.key for i in art_a_data.issues)

    def test_issues_have_project(self, art_a_data):
        assert all(i.project for i in art_a_data.issues)

    def test_stage_minutes_keys_match_stages(self, art_a_data):
        for issue in art_a_data.issues:
            assert set(issue.stage_minutes.keys()) == set(art_a_data.stages)


class TestFiltersOnRealData:
    def test_date_filter_reduces_issues(self, art_a_data):
        cfg = FilterConfig(from_date=date(2026, 1, 1))
        filtered = apply_filters(art_a_data, cfg)
        assert len(filtered.issues) < len(art_a_data.issues)

    def test_date_filter_all_closed_in_range(self, art_a_data):
        cfg = FilterConfig(from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))
        filtered = apply_filters(art_a_data, cfg)
        for issue in filtered.issues:
            assert issue.closed_date is not None
            assert issue.closed_date.date() >= date(2026, 1, 1)

    def test_cfd_filter_reduces_records(self, art_a_data):
        cfg = FilterConfig(from_date=date(2026, 1, 1))
        filtered = apply_filters(art_a_data, cfg)
        assert len(filtered.cfd) < len(art_a_data.cfd)


class TestFlowTimeOnRealData:
    def test_compute_returns_count(self, art_a_data):
        metric = FlowTimeMetric()
        result = metric.compute(art_a_data, SAFE)
        assert result.stats.get("count", 0) > 0

    def test_median_is_positive(self, art_a_data):
        metric = FlowTimeMetric()
        result = metric.compute(art_a_data, SAFE)
        assert result.stats["median"] > 0

    def test_min_less_than_max(self, art_a_data):
        metric = FlowTimeMetric()
        result = metric.compute(art_a_data, SAFE)
        assert result.stats["min"] <= result.stats["max"]

    def test_render_produces_two_figures(self, art_a_data):
        metric = FlowTimeMetric()
        result = metric.compute(art_a_data, SAFE)
        figures = metric.render(result, SAFE)
        assert len(figures) == 2


class TestFlowVelocityOnRealData:
    def test_count_positive(self, art_a_data):
        result = FlowVelocityMetric().compute(art_a_data, SAFE)
        assert result.stats.get("count", 0) > 0

    def test_render_three_figures(self, art_a_data):
        metric = FlowVelocityMetric()
        result = metric.compute(art_a_data, SAFE)
        assert len(metric.render(result, SAFE)) == 3

    def test_avg_per_week_positive(self, art_a_data):
        result = FlowVelocityMetric().compute(art_a_data, SAFE)
        assert result.stats["avg_per_week"] > 0


class TestFlowLoadOnRealData:
    def test_open_count_positive(self, art_a_data):
        result = FlowLoadMetric().compute(art_a_data, SAFE)
        assert result.stats.get("open_count", 0) > 0

    def test_render_one_figure(self, art_a_data):
        metric = FlowLoadMetric()
        result = metric.compute(art_a_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1


class TestCfdOnRealData:
    def test_days_positive(self, art_a_data):
        result = CfdMetric().compute(art_a_data, SAFE)
        assert result.stats.get("days", 0) > 0

    def test_render_one_figure(self, art_a_data):
        metric = CfdMetric()
        result = metric.compute(art_a_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_ratio_positive(self, art_a_data):
        result = CfdMetric().compute(art_a_data, SAFE)
        assert result.stats.get("ratio", 0) > 0


class TestFlowDistributionOnRealData:
    def test_total_matches_issue_count(self, art_a_data):
        result = FlowDistributionMetric().compute(art_a_data, SAFE)
        assert result.stats["total"] == len(art_a_data.issues)

    def test_render_one_figure_with_two_pies(self, art_a_data):
        metric = FlowDistributionMetric()
        result = metric.compute(art_a_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1
        pie_traces = [t for t in figs[0].data if t.type == "pie"]
        assert len(pie_traces) == 2


class TestExportOnRealData:
    def test_export_single_pdf(self, tmp_path, art_a_data):
        metric = FlowTimeMetric()
        result = metric.compute(art_a_data, SAFE)
        figs = metric.render(result, SAFE)
        out = tmp_path / "flow_time.pdf"
        export_pdf([figs[0]], out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_export_png(self, tmp_path, art_a_data):
        metric = FlowVelocityMetric()
        result = metric.compute(art_a_data, SAFE)
        figs = metric.render(result, SAFE)
        out = tmp_path / "velocity.png"
        export_png(figs[0], out)
        assert out.exists()
        assert out.stat().st_size > 0
