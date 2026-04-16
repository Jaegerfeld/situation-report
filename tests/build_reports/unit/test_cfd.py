# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für CfdMetric. Prüft In/Out-Ratio-Berechnung, Verhalten bei
#   leeren Daten und Render-Ausgabe.
# =============================================================================

from datetime import date

import pytest

from build_reports.loader import CfdRecord, ReportData
from build_reports.metrics.cfd import CfdMetric
from build_reports.terminology import SAFE


def _cfd(day: date, funnel: int, done: int) -> CfdRecord:
    return CfdRecord(day=day, stage_counts={"Funnel": funnel, "Done": done})


@pytest.fixture
def metric():
    return CfdMetric()


@pytest.fixture
def simple_cfd_data():
    return ReportData(
        issues=[],
        cfd=[
            _cfd(date(2025, 1, 1), funnel=10, done=0),
            _cfd(date(2025, 1, 2), funnel=20, done=2),
            _cfd(date(2025, 1, 3), funnel=30, done=5),
        ],
        stages=["Funnel", "Done"],
        source_prefix="TEST",
    )


class TestCompute:
    def test_days_count(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["days"] == 3

    def test_in_total_is_max_of_first_stage(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["in_total"] == 30

    def test_out_total_is_max_of_last_stage(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["out_total"] == 5

    def test_ratio_calculation(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.stats["ratio"] == pytest.approx(6.0)

    def test_warning_on_empty_cfd(self, metric):
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_warning_on_no_stages(self, metric):
        data = ReportData(
            issues=[],
            cfd=[_cfd(date(2025, 1, 1), 1, 0)],
            stages=[],
            source_prefix="",
        )
        result = metric.compute(data, SAFE)
        assert result.warnings

    def test_metric_id(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        assert result.metric_id == "cfd"


class TestRender:
    def test_returns_one_figure(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert len(figs) == 1

    def test_title_contains_ratio(self, metric, simple_cfd_data):
        result = metric.compute(simple_cfd_data, SAFE)
        figs = metric.render(result, SAFE)
        assert "6.0" in figs[0].layout.title.text

    def test_returns_empty_on_no_data(self, metric):
        data = ReportData(issues=[], cfd=[], stages=["Funnel"], source_prefix="")
        result = metric.compute(data, SAFE)
        assert metric.render(result, SAFE) == []
