# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für cli.py. Prüft _parse_date, run_reports (Pipeline-Steuerung,
#   Filter-Weitergabe, Metrik-Auswahl, Ausgabepfade, Warnungen) und main()
#   (Argument-Parsing). Alle externen I/O-Aufrufe werden gemockt.
# =============================================================================

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import plotly.graph_objects as go
import pytest

from build_reports.cli import _parse_date, run_reports
from build_reports.metrics.base import MetricResult
from build_reports.terminology import GLOBAL, SAFE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(warnings: list[str] | None = None) -> MetricResult:
    """Build a minimal MetricResult with one figure."""
    return MetricResult(
        metric_id="test",
        stats={},
        chart_data={},
        warnings=warnings or [],
    )


def _make_plugin(metric_id: str = "test_metric", figures: int = 1) -> MagicMock:
    """Create a mock MetricPlugin that returns `figures` go.Figure objects."""
    plugin = MagicMock()
    plugin.metric_id = metric_id
    result = _make_result()
    plugin.compute.return_value = result
    plugin.render.return_value = [go.Figure() for _ in range(figures)]
    return plugin


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid_date(self):
        assert _parse_date("2025-06-15") == date(2025, 6, 15)

    def test_start_of_year(self):
        assert _parse_date("2024-01-01") == date(2024, 1, 1)

    def test_invalid_format_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
            _parse_date("15.06.2025")

    def test_invalid_date_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
            _parse_date("2025-13-01")

    def test_empty_string_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_date("")


# ---------------------------------------------------------------------------
# run_reports — pipeline orchestration
# ---------------------------------------------------------------------------

class TestRunReports:
    """Tests for the full pipeline orchestrated by run_reports()."""

    @pytest.fixture
    def issue_times(self, tmp_path) -> Path:
        """Dummy path (never read in unit tests due to mocking)."""
        p = tmp_path / "IssueTimes.xlsx"
        p.touch()
        return p

    @pytest.fixture
    def mock_data(self):
        """Minimal ReportData mock."""
        data = MagicMock()
        data.issues = [MagicMock() for _ in range(10)]
        data.cfd = [MagicMock() for _ in range(30)]
        return data

    @pytest.fixture
    def mock_filtered(self, mock_data):
        """Filtered data has fewer issues."""
        filtered = MagicMock()
        filtered.issues = mock_data.issues[:5]
        filtered.cfd = mock_data.cfd[:15]
        return filtered

    def _patch_all(self, mock_data, mock_filtered, plugins):
        """Return a context-manager stack that patches all external calls."""
        return (
            patch("build_reports.cli.load_report_data", return_value=mock_data),
            patch("build_reports.cli.apply_filters", return_value=mock_filtered),
            patch("build_reports.cli.all_metrics", return_value=plugins),
        )

    # --- data loading -------------------------------------------------------

    def test_calls_load_report_data(self, issue_times, mock_data, mock_filtered):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data) as mock_load, \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, log=lambda *_: None)
        mock_load.assert_called_once_with(issue_times, None)

    def test_passes_cfd_to_loader(self, issue_times, tmp_path, mock_data, mock_filtered):
        cfd = tmp_path / "CFD.xlsx"
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data) as mock_load, \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, cfd=cfd, log=lambda *_: None)
        mock_load.assert_called_once_with(issue_times, cfd)

    # --- filter passthrough -------------------------------------------------

    def test_passes_filter_config_to_apply_filters(self, issue_times, mock_data, mock_filtered):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered) as mock_flt, \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(
                issue_times,
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
                projects=["PROJ"],
                issuetypes=["Feature"],
                log=lambda *_: None,
            )
        cfg = mock_flt.call_args[0][1]
        assert cfg.from_date == date(2025, 1, 1)
        assert cfg.to_date == date(2025, 12, 31)
        assert cfg.projects == ["PROJ"]
        assert cfg.issuetypes == ["Feature"]

    def test_empty_projects_issuetypes_passed_as_empty_lists(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered) as mock_flt, \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, log=lambda *_: None)
        cfg = mock_flt.call_args[0][1]
        assert cfg.projects == []
        assert cfg.issuetypes == []

    # --- metric selection ---------------------------------------------------

    def test_all_metrics_called_when_no_metrics_specified(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]) as mock_all:
            run_reports(issue_times, log=lambda *_: None)
        mock_all.assert_called_once()

    def test_get_metric_called_for_each_specified_metric(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin("flow_time")
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.get_metric", return_value=plugin) as mock_get, \
             patch("build_reports.cli.all_metrics"):
            run_reports(issue_times, metrics=["flow_time"], log=lambda *_: None)
        mock_get.assert_called_once_with("flow_time")

    def test_unknown_metric_logged_and_skipped(
        self, issue_times, mock_data, mock_filtered
    ):
        logged = []
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.get_metric", side_effect=KeyError("unknown")), \
             patch("build_reports.cli.all_metrics"):
            run_reports(
                issue_times,
                metrics=["unknown"],
                log=logged.append,
            )
        assert any("WARNING" in m and "unknown" in m for m in logged)

    # --- plugin execution ---------------------------------------------------

    def test_compute_called_with_filtered_data_and_terminology(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, terminology=GLOBAL, log=lambda *_: None)
        plugin.compute.assert_called_once_with(mock_filtered, GLOBAL)

    def test_render_called_with_result_and_terminology(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin()
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, terminology=GLOBAL, log=lambda *_: None)
        plugin.render.assert_called_once_with(plugin.compute.return_value, GLOBAL)

    def test_warnings_from_result_are_logged(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin()
        plugin.compute.return_value = _make_result(warnings=["something odd"])
        logged = []
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, log=logged.append)
        assert any("something odd" in m for m in logged)

    # --- output routing -----------------------------------------------------

    def test_export_pdf_called_when_output_pdf_set(
        self, tmp_path, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin(figures=2)
        out = tmp_path / "report.pdf"
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]), \
             patch("build_reports.cli.export_pdf") as mock_export:
            run_reports(issue_times, output_pdf=out, log=lambda *_: None)
        mock_export.assert_called_once()
        assert mock_export.call_args[0][1] == out

    def test_pio_show_called_for_each_figure_when_open_browser(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin(figures=3)
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]), \
             patch("build_reports.cli.pio") as mock_pio:
            run_reports(issue_times, open_browser=True, log=lambda *_: None)
        assert mock_pio.show.call_count == 3

    def test_no_output_logs_warning(self, issue_times, mock_data, mock_filtered):
        plugin = _make_plugin()
        logged = []
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, log=logged.append)
        assert any("No output" in m for m in logged)

    def test_no_figures_logs_nothing_to_export(
        self, issue_times, mock_data, mock_filtered
    ):
        plugin = _make_plugin(figures=0)
        logged = []
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=[plugin]):
            run_reports(issue_times, output_pdf=Path("x.pdf"), log=logged.append)
        assert any("No figures" in m for m in logged)

    def test_figures_from_multiple_plugins_are_combined(
        self, issue_times, mock_data, mock_filtered
    ):
        plugins = [_make_plugin("a", figures=2), _make_plugin("b", figures=3)]
        with patch("build_reports.cli.load_report_data", return_value=mock_data), \
             patch("build_reports.cli.apply_filters", return_value=mock_filtered), \
             patch("build_reports.cli.all_metrics", return_value=plugins), \
             patch("build_reports.cli.export_pdf") as mock_export:
            run_reports(
                issue_times,
                output_pdf=Path("x.pdf"),
                log=lambda *_: None,
            )
        all_figs = mock_export.call_args[0][0]
        assert len(all_figs) == 5


# ---------------------------------------------------------------------------
# main() — argparse integration
# ---------------------------------------------------------------------------

class TestMain:
    """Tests that main() parses arguments correctly and calls run_reports."""

    def _run_main_with_argv(self, argv: list[str]) -> MagicMock:
        """
        Patch sys.argv, mock run_reports, call main(), and return the mock.
        """
        from build_reports.cli import main
        with patch("sys.argv", ["prog"] + argv), \
             patch("build_reports.cli.run_reports") as mock_run, \
             patch("build_reports.cli.all_metrics", return_value=[]):
            main()
        return mock_run

    def test_minimal_invocation_sets_issue_times(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv([str(issue_times)])
        assert mock_run.call_args[1]["issue_times"] == issue_times

    def test_pdf_flag_passed_as_path(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv([str(issue_times), "--pdf", "out.pdf"])
        assert mock_run.call_args[1]["output_pdf"] == Path("out.pdf")

    def test_browser_flag_sets_open_browser(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv([str(issue_times), "--browser"])
        assert mock_run.call_args[1]["open_browser"] is True

    def test_from_date_parsed(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv(
            [str(issue_times), "--from-date", "2025-01-01"]
        )
        assert mock_run.call_args[1]["from_date"] == date(2025, 1, 1)

    def test_to_date_parsed(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv(
            [str(issue_times), "--to-date", "2025-12-31"]
        )
        assert mock_run.call_args[1]["to_date"] == date(2025, 12, 31)

    def test_terminology_global(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv(
            [str(issue_times), "--terminology", GLOBAL]
        )
        assert mock_run.call_args[1]["terminology"] == GLOBAL

    def test_default_terminology_is_safe(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv([str(issue_times)])
        assert mock_run.call_args[1]["terminology"] == SAFE

    def test_projects_passed_as_list(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv(
            [str(issue_times), "--projects", "ARTA", "ARTB"]
        )
        assert mock_run.call_args[1]["projects"] == ["ARTA", "ARTB"]

    def test_issuetypes_passed_as_list(self, tmp_path):
        issue_times = tmp_path / "IT.xlsx"
        issue_times.touch()
        mock_run = self._run_main_with_argv(
            [str(issue_times), "--issuetypes", "Feature", "Bug"]
        )
        assert mock_run.call_args[1]["issuetypes"] == ["Feature", "Bug"]
