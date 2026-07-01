# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       02.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Plotly-Visualisierung der Monte-Carlo-Forecasts. Liefert zwei Diagramme im
#   Stil der übrigen Report-Metriken: die Exceedance-Kurve "Wie viele Items mit
#   welcher Konfidenz?" (mit Referenzlinien 85/75/50 %) und die Verteilung der
#   Fertigstellungstage für den Termin-Forecast. Zusätzlich eine Hilfsfunktion,
#   die mehrere Figuren zu einer eigenständigen HTML-Seite bündelt (Plotly.js
#   nur einmal via CDN, wie im übrigen Projekt).
# =============================================================================

from __future__ import annotations

import bisect
from collections import Counter
from datetime import date

import plotly.graph_objects as go

from .forecast import HowManyForecast, WhenDoneForecast, probability_at_least

_BG = "#e8e8e8"
#: Referenzlinien (Konfidenz -> Farbe) für die Exceedance-Kurve.
_REFLINES: tuple[tuple[int, str], ...] = ((85, "green"), (75, "orange"), (50, "red"))


def exceedance_curve(fc: HowManyForecast) -> tuple[list[int], list[float]]:
    """
    Exceedance-Kurve eines Kapazitäts-Forecasts.

    Args:
        fc: Ergebnis von how_many() (fc.totals ist aufsteigend sortiert).

    Returns:
        Tupel (xs, ys): xs = distinkte erreichte Item-Mengen, ys = zugehörige
        Wahrscheinlichkeit in Prozent, MINDESTENS xs[i] Items zu schaffen.
        Beide leer, wenn keine Läufe vorliegen.
    """
    totals = fc.totals
    n = len(totals)
    if n == 0:
        return [], []
    distinct = sorted(set(totals))
    ys = [(n - bisect.bisect_left(totals, x)) / n * 100.0 for x in distinct]
    return distinct, ys


def how_many_figure(fc: HowManyForecast, title: str | None = None,
                    target: int | None = None,
                    target_date: date | None = None) -> go.Figure:
    """
    Exceedance-Kurve "Wie wahrscheinlich wie viele Items?".

    Args:
        fc:          Ergebnis von how_many().
        title:       Optionaler Titel; Standard nennt Horizont und Laufzahl.
        target:      Optionale Scope-Zielmenge; wird mit ihrer Wahrscheinlichkeit als
                     senkrechte Linie markiert ("Schaffen wir den Scope?").
        target_date: Optionales Zieldatum für den Titel ("... bis Datum X").

    Returns:
        Plotly-Figur mit Kurve, Referenzlinien (85/75/50 %) und Konfidenz-Markern.
    """
    xs, ys = exceedance_curve(fc)
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines", line=dict(color="darkcyan", width=2),
        name="P(≥ x)",
    ))

    for y, color in _REFLINES:
        fig.add_hline(y=y, line_dash="dash", line_color=color,
                      annotation_text=f"{y}%", annotation_position="right")

    # Konfidenz-Marker: Item-Menge je Konfidenzstufe.
    if fc.percentiles:
        conf = sorted(fc.percentiles, reverse=True)
        fig.add_trace(go.Scatter(
            x=[fc.percentiles[c] for c in conf],
            y=list(conf),
            mode="markers+text",
            marker=dict(size=9, color="#14304a"),
            text=[f"{fc.percentiles[c]}" for c in conf],
            textposition="top center", textfont_color="blue",
            name="Konfidenz",
        ))

    if target is not None:
        p = probability_at_least(fc, target) * 100.0
        fig.add_vline(x=target, line_dash="dot", line_color="#c0392b",
                      annotation_text=f"scope {target}: {p:.0f}%",
                      annotation_position="top")

    if title is None:
        if target_date is not None:
            title = (f"Flow Predictability: items by {target_date.isoformat()} "
                     f"({fc.horizon_days} days, {fc.runs} runs)")
        else:
            title = (f"Flow Predictability: items in next {fc.horizon_days} days "
                     f"({fc.runs} runs)")
    fig.update_layout(
        title=title,
        title_font_size=11,
        xaxis_title="Items completed (≥ x)",
        yaxis_title="Likelihood (%)",
        plot_bgcolor=_BG, paper_bgcolor=_BG, height=450,
        showlegend=False,
    )
    return fig


def scope_confidence_figure(probability: float, target: int,
                            target_date: date | None = None) -> go.Figure:
    """
    Gauge: Wie sicher schaffen wir den Scope bis zum Horizont?

    Args:
        probability: Wahrscheinlichkeit in [0.0, 1.0] (z. B. aus
                     probability_at_least()).
        target:      Scope-Zielmenge an Items.
        target_date: Optionales Zieldatum (Horizont-Ende) für die Beschriftung.

    Returns:
        Plotly-Indicator-Gauge mit Schwelle bei 85 % und Ampelzonen (50/75 %).
    """
    sub = f"≥ {target} items"
    if target_date is not None:
        sub += f" by {target_date.isoformat()}"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(probability * 100.0, 1),
        number={"suffix": " %"},
        title={"text": f"Scope confidence<br>"
                       f"<span style='font-size:0.8em'>{sub}</span>"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#14304a"},
            "steps": [
                {"range": [0, 50], "color": "#f4c7c3"},
                {"range": [50, 75], "color": "#fde9c8"},
                {"range": [75, 100], "color": "#cfe8cf"},
            ],
            "threshold": {"line": {"color": "red", "width": 3}, "value": 85},
        },
    ))
    fig.update_layout(height=300, paper_bgcolor=_BG, margin=dict(t=80, b=10))
    return fig


def when_done_figure(fc: WhenDoneForecast, title: str | None = None) -> go.Figure:
    """
    Verteilung der Fertigstellungstage für den Termin-Forecast.

    Args:
        fc:    Ergebnis von when_done().
        title: Optionaler Titel; Standard nennt Backlog-Größe und Split-Rate.

    Returns:
        Plotly-Balkendiagramm der Tage-bis-fertig mit Konfidenz-Linien. Bei
        leerer Verteilung (kein Lauf wurde fertig) eine Figur mit Hinweis.
    """
    default_title = (
        f"Flow Predictability: days to finish {fc.backlog} items "
        f"(split rate {fc.split_rate:g}, {fc.runs} runs)"
    )
    fig = go.Figure()

    if not fc.completion_days:
        fig.add_annotation(text="No run completed within the cap "
                                "(scope growth outran throughput).",
                           showarrow=False, font=dict(size=13, color="red"))
        fig.update_layout(title=title or default_title, title_font_size=11,
                          plot_bgcolor=_BG, paper_bgcolor=_BG, height=450)
        return fig

    freq = Counter(fc.completion_days)
    xs = sorted(freq)
    ys = [freq[d] for d in xs]
    fig.add_trace(go.Bar(x=xs, y=ys, marker_color="#4a4a4a", name="runs"))

    # Konfidenz-Linien mit gestaffelten Labels: dicht beieinander liegende
    # Perzentile (z. B. 75 % und 85 %) würden sich sonst oben überlagern und
    # wären unlesbar. Die Labels werden über der Plotfläche auf mehreren Zeilen
    # verteilt – nach Tagen sortiert, damit benachbarte (nahe) Labels garantiert
    # auf unterschiedliche Höhen fallen. Konfidenzstufen, die im Cap nicht
    # erreichbar sind (days is None), werden vorher ausgefiltert.
    reachable: list[tuple[int, int]] = [
        (c, d) for c in fc.percentiles
        if (d := fc.percentiles[c]) is not None
    ]
    reachable.sort(key=lambda cd: cd[1])
    _rows = 3  # zyklische Label-Zeilen über der Plotfläche
    for i, (c, days) in enumerate(reachable):
        label = f"{c}%: {days}d"
        if c in fc.dates:
            label += f" ({fc.dates[c].isoformat()})"
        fig.add_vline(x=days, line_dash="dash", line_color="#14304a")
        fig.add_annotation(
            x=days, xref="x", y=1.0, yref="paper", yanchor="bottom",
            yshift=6 + (i % _rows) * 16, text=label, showarrow=False,
            font=dict(size=10, color="#14304a"),
        )

    subtitle = default_title
    if fc.not_completed:
        subtitle += f"  —  {fc.not_completed} run(s) not completed"
    fig.update_layout(
        title=title or subtitle, title_font_size=11,
        xaxis_title="Days to complete", yaxis_title="runs",
        plot_bgcolor=_BG, paper_bgcolor=_BG, height=450, showlegend=False,
        margin=dict(t=110),
    )
    return fig


def combined_html(figures: list[go.Figure], intro_html: str = "") -> str:
    """
    Bündle mehrere Figuren zu einer eigenständigen HTML-Seite.

    Plotly.js wird nur für die erste Figur eingebunden (CDN), die weiteren nutzen
    die geladene Bibliothek — analog zum übrigen Projekt.

    Args:
        figures:    Liste von Plotly-Figuren.
        intro_html: Optionaler HTML-Block (z. B. Kennzahlen-Tabelle) vor den
                    Diagrammen.

    Returns:
        Vollständiges HTML-Dokument als String.
    """
    parts: list[str] = []
    if intro_html:
        parts.append(intro_html)
    for i, fig in enumerate(figures):
        parts.append(fig.to_html(
            include_plotlyjs="cdn" if i == 0 else False,
            full_html=False,
            config={"responsive": True},
        ))
    body = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>"
        "body{margin:16px;font-family:sans-serif;background:#fff;}"
        "div.plotly-graph-div{margin-bottom:32px;}"
        "table.stats{border-collapse:collapse;margin:8px 0 24px 0;font-size:14px;}"
        "table.stats th,table.stats td{border:1px solid #c4ccd4;padding:4px 10px;text-align:left;}"
        "table.stats th{background:#14304a;color:#fff;}"
        "</style></head>"
        f"<body>{body}</body></html>"
    )
