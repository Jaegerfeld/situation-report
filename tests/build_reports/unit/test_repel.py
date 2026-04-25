# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       25.04.2026
# Geändert:       25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für repel.py. Prüft, dass add_repelled_hlines() die korrekten
#   Annotationen und Shapes in Plotly-Figures erzeugt, Überlappungen verhindert
#   und None-Werte korrekt ignoriert.
# =============================================================================

import plotly.graph_objects as go
import pytest

from build_reports.repel import add_repelled_hlines


def _make_fig() -> go.Figure:
    """Return a blank Plotly Figure for testing."""
    return go.Figure()


def _count_annotations(fig: go.Figure) -> int:
    """Return the number of annotations in the figure layout."""
    return len(fig.layout.annotations)


def _count_shapes(fig: go.Figure) -> int:
    """Return the number of shapes (hlines) in the figure layout."""
    return len(fig.layout.shapes)


def _annotation_yshifts(fig: go.Figure) -> list[float]:
    """Return the yshift value for each annotation, defaulting to 0 if unset."""
    return [a.yshift or 0.0 for a in fig.layout.annotations]


class TestBasicBehavior:
    """Tests for the basic output of add_repelled_hlines()."""

    def test_adds_one_shape_per_valid_line(self):
        """One hline shape is added for each non-None entry."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(10.0, "red", "dot", "P50"),
                                  (20.0, "blue", "dash", "P85")], y_max=30.0)
        assert _count_shapes(fig) == 2

    def test_adds_one_annotation_per_valid_line(self):
        """One annotation is added for each non-None entry."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(10.0, "red", "dot", "A"),
                                  (20.0, "blue", "dash", "B")], y_max=30.0)
        assert _count_annotations(fig) == 2

    def test_none_entries_are_skipped(self):
        """Entries with y=None produce no shape or annotation."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(None, "red", "dot", "skip"),
                                  (20.0, "blue", "dash", "keep")], y_max=30.0)
        assert _count_shapes(fig) == 1
        assert _count_annotations(fig) == 1

    def test_all_none_adds_nothing(self):
        """An all-None lines list adds nothing to the figure."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(None, "red", "dot", "x")], y_max=30.0)
        assert _count_shapes(fig) == 0
        assert _count_annotations(fig) == 0

    def test_empty_lines_adds_nothing(self):
        """An empty lines list adds nothing to the figure."""
        fig = _make_fig()
        add_repelled_hlines(fig, [], y_max=30.0)
        assert _count_shapes(fig) == 0

    def test_annotation_texts_preserved(self):
        """Annotation text matches the label from the input tuple."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(10.0, "red", "dot", "Median"),
                                  (20.0, "blue", "dash", "P85")], y_max=30.0)
        texts = {a.text for a in fig.layout.annotations}
        assert texts == {"Median", "P85"}


class TestNoOverlap:
    """Tests that verify yshift is zero when lines are well-separated."""

    def test_widely_separated_lines_have_no_shift(self):
        """Lines far apart require no yshift correction."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(5.0, "red", "dot", "low"),
                                  (95.0, "blue", "dash", "high")], y_max=100.0,
                            fig_height=500, min_gap_px=14.0)
        shifts = _annotation_yshifts(fig)
        assert all(s == 0.0 for s in shifts)


class TestOverlapRepulsion:
    """Tests that verify yshift is applied when lines are too close."""

    def test_identical_values_produce_nonzero_shift(self):
        """When two lines have the same y, the lower annotation gets a nonzero yshift."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(50.0, "red", "dot", "A"),
                                  (50.0, "blue", "dash", "B")], y_max=100.0,
                            fig_height=500, min_gap_px=14.0)
        shifts = _annotation_yshifts(fig)
        # One shift must be nonzero (the lower label is pushed)
        assert any(s != 0.0 for s in shifts)

    def test_close_lines_lower_label_shifted_down(self):
        """The lower annotation receives a negative (downward) yshift when lines are close."""
        fig = _make_fig()
        add_repelled_hlines(fig, [(51.0, "red", "dot", "high"),
                                  (50.0, "blue", "dash", "low")], y_max=100.0,
                            fig_height=500, min_gap_px=14.0)
        shifts = _annotation_yshifts(fig)
        # At least one annotation must have been pushed down
        assert min(shifts) < 0.0

    def test_three_close_lines_all_separated(self):
        """All three labels are separated when three lines cluster at the same value."""
        fig = _make_fig()
        add_repelled_hlines(
            fig,
            [(50.0, "red", "dot", "A"),
             (50.0, "blue", "dash", "B"),
             (50.0, "green", "solid", "C")],
            y_max=100.0, fig_height=500, min_gap_px=14.0,
        )
        shifts = sorted(_annotation_yshifts(fig))
        # Each consecutive pair of effective positions must be at least min_gap_px apart
        for i in range(len(shifts) - 1):
            # Effective position = natural_px + shift. All naturals are equal here,
            # so we can compare shifts directly.
            assert shifts[i + 1] - shifts[i] >= 14.0 - 1e-6
