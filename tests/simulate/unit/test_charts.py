# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für simulate.charts: die reine Exceedance-Berechnung sowie das
#   Erzeugen der Figuren und der gebündelten HTML-Seite (Smoke-Level).
# =============================================================================

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from simulate.charts import (
    combined_html,
    exceedance_curve,
    how_many_figure,
    scope_confidence_figure,
    when_done_figure,
)
from simulate.forecast import HowManyForecast, WhenDoneForecast


class TestExceedanceCurve:
    def test_probabilities(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=4, totals=[1, 1, 2, 3],
                             percentiles={50: 1})
        xs, ys = exceedance_curve(fc)
        assert xs == [1, 2, 3]
        assert ys == [100.0, 50.0, 25.0]

    def test_empty(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=0, totals=[], percentiles={})
        assert exceedance_curve(fc) == ([], [])


class TestFigures:
    def test_how_many_figure_is_figure(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=3, totals=[1, 2, 3],
                             percentiles={85: 1, 50: 2})
        fig = how_many_figure(fc)
        assert isinstance(fig, go.Figure)
        assert fig.data  # mindestens eine Trace

    def test_how_many_target_marker(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=4, totals=[1, 1, 2, 3],
                             percentiles={50: 2})
        fig = how_many_figure(fc, target=2)
        # Ziel-Marker als Annotation "scope 2: 50%"
        assert any("scope 2" in (a.text or "") for a in fig.layout.annotations)

    def test_how_many_target_date_in_title(self) -> None:
        fc = HowManyForecast(horizon_days=30, runs=3, totals=[1, 2, 3],
                             percentiles={})
        fig = how_many_figure(fc, target_date=date(2026, 9, 1))
        assert "2026-09-01" in fig.layout.title.text
        assert "by" in fig.layout.title.text

    def test_scope_confidence_gauge(self) -> None:
        fig = scope_confidence_figure(0.78, 50, date(2026, 9, 1))
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "indicator"
        assert fig.data[0].value == 78.0

    def test_when_done_empty_shows_annotation(self) -> None:
        fc = WhenDoneForecast(backlog=10, runs=5, split_rate=2.0, completion_days=[],
                              percentiles={}, dates={}, not_completed=5, start_date=None)
        fig = when_done_figure(fc)
        assert isinstance(fig, go.Figure)
        assert fig.layout.annotations  # Hinweis-Annotation vorhanden

    def test_when_done_with_data(self) -> None:
        fc = WhenDoneForecast(
            backlog=50, runs=4, split_rate=0.0, completion_days=[9, 10, 10, 11],
            percentiles={85: 11, 50: 10},
            dates={85: date(2026, 7, 12), 50: date(2026, 7, 11)},
            not_completed=0, start_date=date(2026, 7, 1),
        )
        fig = when_done_figure(fc)
        assert isinstance(fig, go.Figure)
        assert fig.data

    def test_when_done_labels_staggered(self) -> None:
        # Regression: dicht beieinander liegende Perzentile (123d/138d) dürfen sich
        # oben nicht überlagern -> ihre Labels müssen auf verschiedenen Höhen sitzen.
        fc = WhenDoneForecast(
            backlog=35, runs=100, split_rate=0.0,
            completion_days=[97, 123, 138, 164] * 25,
            percentiles={50: 97, 75: 123, 85: 138, 95: 164},
            dates={50: date(2026, 10, 6), 75: date(2026, 11, 1),
                   85: date(2026, 11, 16), 95: date(2026, 12, 12)},
            not_completed=0, start_date=date(2026, 7, 1),
        )
        fig = when_done_figure(fc)
        # Ein Label je Perzentil, jedes über seiner eigenen Linie (x == Tageswert).
        labels = fig.layout.annotations
        assert len(labels) == 4
        assert {a.x for a in labels} == {97, 123, 138, 164}
        # Die eng benachbarten Labels liegen auf unterschiedlichen Höhen (yshift).
        by_x = {a.x: a.yshift for a in labels}
        assert by_x[123] != by_x[138]

    def test_when_done_unreachable_percentile_skipped(self) -> None:
        # Ein im Cap unerreichbares Perzentil (days is None) darf keine Label-Zeile
        # belegen und kein Label erzeugen.
        fc = WhenDoneForecast(
            backlog=35, runs=10, split_rate=5.0, completion_days=[10, 12],
            percentiles={50: 10, 95: None}, dates={50: date(2026, 7, 11)},
            not_completed=8, start_date=date(2026, 7, 1),
        )
        fig = when_done_figure(fc)
        assert len(fig.layout.annotations) == 1
        assert fig.layout.annotations[0].x == 10


class TestCombinedHtml:
    def test_contains_plotly_and_intro(self) -> None:
        fc = HowManyForecast(horizon_days=10, runs=3, totals=[1, 2, 3],
                             percentiles={50: 2})
        html = combined_html([how_many_figure(fc)], intro_html="<p>INTRO</p>")
        assert "<p>INTRO</p>" in html
        assert "plotly" in html.lower()
        assert html.startswith("<!DOCTYPE html>")
