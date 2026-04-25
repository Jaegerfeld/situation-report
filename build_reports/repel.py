# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       25.04.2026
# Geändert:       25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Hilfsfunktionen zur kollisionsfreien Platzierung von Annotationen in
#   Plotly-Diagrammen. Verhindert Überlappungen von Beschriftungen bei
#   horizontalen Referenzlinien (ähnlich dem Prinzip von ggrepel in R).
# =============================================================================

from __future__ import annotations

import plotly.graph_objects as go


def add_repelled_hlines(
    fig: go.Figure,
    lines: list[tuple[float | None, str, str, str]],
    y_max: float,
    y_min: float = 0.0,
    fig_height: int = 500,
    min_gap_px: float = 14.0,
    line_width: float = 1.5,
    annotation_font_size: int = 9,
) -> None:
    """
    Add horizontal reference lines with non-overlapping right-side annotations.

    When multiple lines have y-values so close that their labels would overlap,
    vertical pixel offsets (yshift) are applied to the annotations to maintain
    a minimum separation. The repulsion algorithm processes lines from top to
    bottom and pushes each label downward as needed.

    The annotation is placed at the right edge of the plot (xref="paper",
    x=1.0) at the line's y-coordinate (yref="y"), with yshift applied as a
    pixel correction.

    Args:
        fig:                  Figure to add the lines and annotations to.
        lines:                List of (y, color, dash, label) tuples.
                              Entries with y=None are skipped.
        y_max:                Maximum y-axis data value — used to convert data
                              units to an approximate pixel scale.
        y_min:                Minimum y-axis data value (default 0).
        fig_height:           Figure height in pixels, used for pixel scale
                              estimation (default 500).
        min_gap_px:           Minimum vertical distance between annotation
                              labels in pixels (default 14).
        line_width:           Width of the horizontal line in pixels (default 1.5).
        annotation_font_size: Font size for annotation text (default 9).
    """
    valid = [(y, c, d, lbl) for y, c, d, lbl in lines if y is not None]
    if not valid:
        return

    span = max(y_max - y_min, 1e-9)
    # Approximate plot area as 75 % of total figure height (accounts for margins)
    plot_px = fig_height * 0.75
    px_per_unit = plot_px / span

    def _to_px(y: float) -> float:
        """Convert data-unit y to approximate pixel distance from plot bottom."""
        return (y - y_min) * px_per_unit

    # Sort descending so the highest label is placed first
    sorted_lines = sorted(valid, key=lambda t: t[0], reverse=True)

    placed_px: list[float] = []   # effective pixel position (from bottom) of each placed label
    yshifts: list[float] = []

    for y, *_ in sorted_lines:
        natural_px = _to_px(y)
        shift_px = 0.0

        for prev_px in placed_px:
            gap = prev_px - (natural_px + shift_px)
            if 0 <= gap < min_gap_px:
                # Push this label down so it clears the label above
                shift_px = prev_px - natural_px - min_gap_px

        placed_px.append(natural_px + shift_px)
        yshifts.append(shift_px)

    for (y, color, dash, label), yshift in zip(sorted_lines, yshifts):
        fig.add_hline(
            y=y,
            line_color=color,
            line_dash=dash,
            line_width=line_width,
        )
        fig.add_annotation(
            x=1.0, y=y,
            xref="paper", yref="y",
            text=label,
            showarrow=False,
            font=dict(size=annotation_font_size),
            xanchor="left",
            yanchor="middle",
            yshift=yshift,
        )
