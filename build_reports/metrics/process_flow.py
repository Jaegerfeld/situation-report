# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.04.2026
# Geändert:       26.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Implementiert die Process Flow Metrik. Erzeugt einen gerichteten Graphen
#   aller Status-Übergänge aus der Transitions.xlsx. Knoten = Status,
#   Kanten = Übergänge mit Anzahl als Beschriftung. Kantendicke ist proportional
#   zur relativen Häufigkeit des Übergangs. Bidirektionale Kanten werden als
#   Kurven dargestellt, Self-Loops als kleiner Kreisbogen am Knoten.
# =============================================================================

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import plotly.graph_objects as go

from ..loader import ReportData
from ..terminology import PROCESS_FLOW, term
from . import register
from .base import MetricPlugin, MetricResult

# Graph layout constants
_NODE_RADIUS = 0.07     # radius of node circle in data coordinates
_CURVE_OFFSET = 0.22    # perpendicular offset for bidirectional edge curves
_LOOP_DIST = 0.20       # distance of self-loop center from node center
_LOOP_RADIUS = 0.10     # radius of self-loop arc
_MAX_EDGE_WIDTH = 10.0  # maximum plotly line width for the heaviest edge
_MIN_EDGE_WIDTH = 1.0   # minimum plotly line width

_COLOR_EDGE = "#5b8db8"
_COLOR_EDGE_BACK = "#c0392b"   # rework / backward transitions
_COLOR_SELF_LOOP = "#e67e22"
_COLOR_NODE_FILL = "#2c3e50"
_COLOR_NODE_TEXT = "#ffffff"


@dataclass
class _Edge:
    source: str
    target: str
    count: int
    relative: float   # count / total_transitions
    is_self_loop: bool = False


@dataclass
class _FlowData:
    nodes: list[str]                  # ordered for circular layout
    edges: list[_Edge]
    total_transitions: int
    issue_count: int
    workflow_stages: list[str]        # from ReportData.stages (may be empty)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _circular_positions(nodes: list[str]) -> dict[str, tuple[float, float]]:
    """
    Place nodes evenly on a unit circle, starting at the top (12 o'clock).

    Args:
        nodes: Ordered list of node labels.

    Returns:
        Dict mapping node label to (x, y) coordinates.
    """
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: (0.0, 0.0)}
    angle_step = 2 * math.pi / n
    return {
        node: (
            math.sin(i * angle_step),        # x: sin starts right from top
            math.cos(i * angle_step),        # y: cos starts at top
        )
        for i, node in enumerate(nodes)
    }


def _bezier_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    n: int = 30,
) -> tuple[list[float], list[float]]:
    """
    Sample a quadratic Bezier curve from p0 through control point p1 to p2.

    Args:
        p0: Start point (x, y).
        p1: Control point (x, y).
        p2: End point (x, y).
        n:  Number of sample points.

    Returns:
        Tuple of (x_list, y_list).
    """
    xs, ys = [], []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        xs.append(mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0])
        ys.append(mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1])
    return xs, ys


def _edge_width(edge: _Edge, max_count: int) -> float:
    """Map edge count to line width in [_MIN_EDGE_WIDTH, _MAX_EDGE_WIDTH]."""
    if max_count == 0:
        return _MIN_EDGE_WIDTH
    ratio = edge.count / max_count
    return _MIN_EDGE_WIDTH + ratio * (_MAX_EDGE_WIDTH - _MIN_EDGE_WIDTH)


def _edge_color(edge: _Edge, workflow_stages: list[str]) -> str:
    """
    Return edge color: rework color for backward transitions (source appears
    after target in workflow order), self-loop color for self-loops,
    default blue otherwise.

    Args:
        edge:            The edge to color.
        workflow_stages: Ordered list of workflow stages.

    Returns:
        CSS color string.
    """
    if edge.is_self_loop:
        return _COLOR_SELF_LOOP
    if workflow_stages:
        idx = {s: i for i, s in enumerate(workflow_stages)}
        src_i = idx.get(edge.source, -1)
        tgt_i = idx.get(edge.target, -1)
        if src_i >= 0 and tgt_i >= 0 and src_i > tgt_i:
            return _COLOR_EDGE_BACK
    return _COLOR_EDGE


# ---------------------------------------------------------------------------
# Figure building helpers
# ---------------------------------------------------------------------------

def _add_self_loop(
    fig: go.Figure,
    node: str,
    pos: dict[str, tuple[float, float]],
    edge: _Edge,
    width: float,
    color: str,
) -> None:
    """
    Draw a small circular arc as a self-loop on a node, positioned outward
    from the graph center.

    Args:
        fig:   Plotly Figure to add traces/annotations to.
        node:  Node label (self-loop source = target).
        pos:   Dict of node positions.
        edge:  The self-loop _Edge.
        width: Line width.
        color: Line color.
    """
    nx, ny = pos[node]
    length = math.hypot(nx, ny)
    if length > 0:
        dx, dy = nx / length, ny / length
    else:
        dx, dy = 0.0, 1.0

    cx = nx + dx * _LOOP_DIST
    cy = ny + dy * _LOOP_DIST

    angles = [i * 2 * math.pi / 60 for i in range(61)]
    lx = [cx + _LOOP_RADIUS * math.cos(a) for a in angles]
    ly = [cy + _LOOP_RADIUS * math.sin(a) for a in angles]

    fig.add_trace(go.Scatter(
        x=lx, y=ly,
        mode="lines",
        line=dict(width=width, color=color),
        hovertemplate=(
            f"<b>{node} → {node}</b><br>"
            f"Count: {edge.count} ({edge.relative:.1%})<extra></extra>"
        ),
        showlegend=False,
    ))

    # Label near the loop
    lx_mid = cx + _LOOP_RADIUS * math.cos(math.pi / 4) + dx * 0.06
    ly_mid = cy + _LOOP_RADIUS * math.sin(math.pi / 4) + dy * 0.06
    fig.add_annotation(
        x=lx_mid, y=ly_mid,
        text=str(edge.count),
        showarrow=False,
        font=dict(size=9, color="#333"),
        bgcolor="rgba(255,255,255,0.8)",
        borderpad=2,
    )


def _add_edge(
    fig: go.Figure,
    edge: _Edge,
    pos: dict[str, tuple[float, float]],
    bidirectional: set[tuple[str, str]],
    width: float,
    color: str,
) -> None:
    """
    Draw a directed edge between two nodes.

    Straight edges for unidirectional connections; quadratic Bezier curves
    for bidirectional pairs. Arrowhead drawn as annotation near the target.
    Count label placed at the curve midpoint.

    Args:
        fig:           Plotly Figure.
        edge:          The _Edge to draw.
        pos:           Node positions.
        bidirectional: Set of (u, v) pairs that also have a (v, u) counterpart.
        width:         Line width.
        color:         Line color.
    """
    x1, y1 = pos[edge.source]
    x2, y2 = pos[edge.target]

    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length   # unit direction
    px, py = -uy, ux                    # perpendicular (left of direction)

    is_bidir = (edge.source, edge.target) in bidirectional
    offset_sign = 1 if is_bidir else 0

    # Control point for Bezier (offset only for bidirectional pairs)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    cp = (
        mx + offset_sign * _CURVE_OFFSET * px,
        my + offset_sign * _CURVE_OFFSET * py,
    )

    # Shorten start/end so lines don't overlap the node circles
    t_start = _NODE_RADIUS / length
    t_end = 1 - _NODE_RADIUS / length
    if t_start >= t_end:
        return

    # Evaluate Bezier at t_start and t_end for actual line endpoints
    def _bz(t: float) -> tuple[float, float]:
        mt = 1 - t
        bx = mt * mt * x1 + 2 * mt * t * cp[0] + t * t * x2
        by = mt * mt * y1 + 2 * mt * t * cp[1] + t * t * y2
        return bx, by

    sx1, sy1 = _bz(t_start)
    sx2, sy2 = _bz(t_end)

    bx, by = _bezier_points((sx1, sy1), cp, (sx2, sy2))

    fig.add_trace(go.Scatter(
        x=bx, y=by,
        mode="lines",
        line=dict(width=width, color=color),
        hovertemplate=(
            f"<b>{edge.source} → {edge.target}</b><br>"
            f"Count: {edge.count} ({edge.relative:.1%})<extra></extra>"
        ),
        showlegend=False,
    ))

    # Arrowhead annotation at target end
    n = len(bx)
    ax_tail, ay_tail = bx[n - 3], by[n - 3]
    fig.add_annotation(
        x=sx2, y=sy2,
        ax=ax_tail, ay=ay_tail,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True,
        arrowhead=2, arrowsize=1.2,
        arrowwidth=max(1.0, width * 0.6),
        arrowcolor=color,
    )

    # Count label at curve midpoint, offset slightly outward
    label_x = bx[n // 2] + offset_sign * px * 0.06
    label_y = by[n // 2] + offset_sign * py * 0.06
    fig.add_annotation(
        x=label_x, y=label_y,
        text=str(edge.count),
        showarrow=False,
        font=dict(size=9, color="#333"),
        bgcolor="rgba(255,255,255,0.8)",
        borderpad=2,
    )


def _add_nodes(
    fig: go.Figure,
    nodes: list[str],
    pos: dict[str, tuple[float, float]],
) -> None:
    """
    Draw all nodes as filled circles with centered label text.

    Args:
        fig:   Plotly Figure.
        nodes: Ordered list of node labels.
        pos:   Node positions.
    """
    xs = [pos[n][0] for n in nodes]
    ys = [pos[n][1] for n in nodes]

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(
            size=42,
            color=_COLOR_NODE_FILL,
            line=dict(color="#ffffff", width=2),
        ),
        text=nodes,
        textposition="middle center",
        textfont=dict(color=_COLOR_NODE_TEXT, size=10),
        hovertemplate="<b>%{text}</b><extra></extra>",
        showlegend=False,
    ))


# ---------------------------------------------------------------------------
# Metric plugin
# ---------------------------------------------------------------------------

class ProcessFlowMetric(MetricPlugin):
    """
    Process Flow metric.

    Visualises all status transitions from Transitions.xlsx as a directed
    graph. Nodes represent statuses; edges are labelled with transition counts.
    Edge thickness is proportional to the relative share of that transition
    among all transitions. Bidirectional edges are drawn as curves to keep
    both directions visually distinct. Self-loops are shown as small arcs.
    Backward transitions (rework) are coloured red when workflow stage order
    is known.
    """

    metric_id = PROCESS_FLOW

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Count all consecutive status transitions per issue and aggregate them.

        Args:
            data:        ReportData — uses data.transitions and data.stages.
            terminology: Active terminology mode (unused here, kept for API).

        Returns:
            MetricResult with _FlowData as chart_data, or warnings if no data.
        """
        warnings: list[str] = []
        if not data.transitions:
            warnings.append("No transition data available. Load a Transitions.xlsx file.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        # Group labels per issue key (preserving file order = chronological)
        by_issue: dict[str, list[str]] = defaultdict(list)
        for t in data.transitions:
            by_issue[t.key].append(t.label)

        # Count consecutive transition pairs
        edge_counter: Counter[tuple[str, str]] = Counter()
        for labels in by_issue.values():
            for i in range(len(labels) - 1):
                edge_counter[(labels[i], labels[i + 1])] += 1

        if not edge_counter:
            warnings.append("No transitions found (each issue has at most one status entry).")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        total = sum(edge_counter.values())

        # Order nodes: workflow stages first (in order), then remaining alphabetically
        stage_set = set(data.stages)
        all_statuses = sorted(set(s for pair in edge_counter for s in pair))
        ordered_nodes = (
            [s for s in data.stages if s in all_statuses]
            + [s for s in all_statuses if s not in stage_set]
        )

        edges = [
            _Edge(
                source=fr,
                target=to,
                count=cnt,
                relative=cnt / total,
                is_self_loop=(fr == to),
            )
            for (fr, to), cnt in sorted(edge_counter.items(), key=lambda x: -x[1])
        ]

        flow_data = _FlowData(
            nodes=ordered_nodes,
            edges=edges,
            total_transitions=total,
            issue_count=len(by_issue),
            workflow_stages=list(data.stages),
        )

        stats = dict(
            nodes=len(ordered_nodes),
            edge_pairs=len(edges),
            total_transitions=total,
            issue_count=len(by_issue),
            top_transition=f"{edges[0].source} → {edges[0].target} ({edges[0].count})",
        )

        return MetricResult(
            metric_id=self.metric_id,
            stats=stats,
            chart_data=flow_data,
            warnings=warnings,
        )

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render the process flow as a directed graph figure.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for the chart title.

        Returns:
            List with one plotly Figure, or empty list if no data.
        """
        if not result.chart_data:
            return []

        fd: _FlowData = result.chart_data
        label = term(PROCESS_FLOW, terminology)

        pos = _circular_positions(fd.nodes)
        max_count = max(e.count for e in fd.edges) if fd.edges else 1

        bidirectional: set[tuple[str, str]] = {
            (e.source, e.target)
            for e in fd.edges
            if not e.is_self_loop
            and any(
                other.source == e.target and other.target == e.source
                for other in fd.edges
                if not other.is_self_loop
            )
        }

        fig = go.Figure()

        # Draw edges (behind nodes)
        for edge in fd.edges:
            width = _edge_width(edge, max_count)
            color = _edge_color(edge, fd.workflow_stages)
            if edge.is_self_loop:
                _add_self_loop(fig, edge.source, pos, edge, width, color)
            else:
                _add_edge(fig, edge, pos, bidirectional, width, color)

        # Draw nodes (on top of edges)
        _add_nodes(fig, fd.nodes, pos)

        # Legend annotations
        legend_items = [
            ("━", _COLOR_EDGE, "Forward transition"),
            ("━", _COLOR_EDGE_BACK, "Backward / rework"),
            ("━", _COLOR_SELF_LOOP, "Self-loop"),
        ]
        for i, (sym, col, txt) in enumerate(legend_items):
            fig.add_annotation(
                x=1.01, y=0.95 - i * 0.08,
                xref="paper", yref="paper",
                text=f'<span style="color:{col}; font-size:16px">{sym}</span> {txt}',
                showarrow=False,
                xanchor="left",
                font=dict(size=11),
            )

        fig.update_layout(
            title=(
                f"{label}  —  {fd.issue_count} issues, "
                f"{fd.total_transitions} transitions, "
                f"{len(fd.edges)} unique pairs"
            ),
            title_font_size=12,
            paper_bgcolor="#e8e8e8",
            plot_bgcolor="#f5f5f5",
            height=700,
            margin=dict(l=20, r=160, t=50, b=20),
            xaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[-1.4, 1.4],
            ),
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[-1.4, 1.4],
                scaleanchor="x", scaleratio=1,
            ),
        )

        return [fig]


register(ProcessFlowMetric())
