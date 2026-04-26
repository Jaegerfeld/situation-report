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
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import plotly.graph_objects as go

from ..loader import ReportData, TransitionEntry
from ..terminology import PROCESS_FLOW, PROCESS_FLOW_TIME, term
from . import register
from .base import MetricPlugin, MetricResult

# Graph layout constants
_NODE_RADIUS = 0.07     # radius of node circle in data coordinates
_CURVE_OFFSET = 0.22    # perpendicular offset for bidirectional edge curves
_LOOP_DIST = 0.20       # distance of self-loop center from node center
_LOOP_RADIUS = 0.10     # radius of self-loop arc
_MAX_EDGE_WIDTH = 10.0  # maximum plotly line width for the heaviest edge
_MIN_EDGE_WIDTH = 1.0   # minimum plotly line width

_LABEL_WRAP_AT = 9      # wrap multi-word labels longer than this many chars

_COLOR_EDGE = "#5b8db8"
_COLOR_EDGE_BACK = "#c0392b"   # rework / backward transitions
_COLOR_SELF_LOOP = "#e67e22"
_COLOR_NODE_FILL = "#2c3e50"
_COLOR_NODE_TEXT = "#ffffff"

# Process Flow: Time — node fill color scale (fast → slow)
_COLOR_TIME_FAST = "#27ae60"   # green
_COLOR_TIME_MID  = "#f39c12"   # orange
_COLOR_TIME_SLOW = "#c0392b"   # red
_COLOR_TIME_NONE = "#7f8c8d"   # gray for statuses without dwell data


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


@dataclass
class _NodeTimeStats:
    """Dwell time statistics for one status node."""
    avg_minutes: float
    q1_minutes: float
    median_minutes: float
    q3_minutes: float
    n: int                            # number of dwell-time samples


@dataclass
class _FlowTimeData:
    nodes: list[str]
    edges: list[_Edge]
    stats_by_node: dict[str, _NodeTimeStats]   # key = status; missing = no data
    issue_count: int
    workflow_stages: list[str]


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def _format_label(label: str) -> str:
    """
    Insert a <br> near the midpoint of multi-word labels longer than
    _LABEL_WRAP_AT chars. Single long words without spaces are returned
    unchanged (node size is enlarged instead).

    Args:
        label: Raw status/stage name.

    Returns:
        Label string, optionally containing a single <br> break.
    """
    if len(label) <= _LABEL_WRAP_AT or " " not in label:
        return label
    words = label.split()
    mid = len(label) / 2
    cum, best_i, best_dist = 0, 0, float("inf")
    for i, w in enumerate(words[:-1]):
        cum += len(w) + 1
        d = abs(cum - mid)
        if d < best_dist:
            best_dist, best_i = d, i
    return " ".join(words[: best_i + 1]) + "<br>" + " ".join(words[best_i + 1 :])


def _node_size(formatted_label: str) -> int:
    """
    Return marker size (px) based on the longest line in the formatted label.

    Args:
        formatted_label: Label string, possibly containing <br>.

    Returns:
        Marker size in screen pixels.
    """
    max_line = max(len(ln) for ln in formatted_label.split("<br>"))
    if max_line <= 6:
        return 44
    if max_line <= 9:
        return 58
    return 72


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

_TS_FMT = "%d.%m.%Y %H:%M:%S"


def _parse_ts(ts_str: str) -> datetime | None:
    """
    Parse a timestamp string from Transitions.xlsx.

    Args:
        ts_str: Timestamp string in "DD.MM.YYYY HH:MM:SS" format.

    Returns:
        datetime object, or None if parsing fails.
    """
    try:
        return datetime.strptime(ts_str.strip(), _TS_FMT)
    except (ValueError, AttributeError):
        return None


def _format_duration(minutes: float) -> str:
    """
    Format a duration in minutes as a compact human-readable string.

    Args:
        minutes: Duration in minutes.

    Returns:
        String like "45m", "3.2h", or "2.1d".
    """
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """
    Linearly interpolate between two hex colors.

    Args:
        c1: Start color as "#rrggbb".
        c2: End color as "#rrggbb".
        t:  Interpolation factor in [0, 1].

    Returns:
        Interpolated color as "#rrggbb".
    """
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _time_color(normalized: float) -> str:
    """
    Map a normalized dwell time [0=fast, 1=slow] to a traffic-light color.

    Args:
        normalized: Value in [0, 1].

    Returns:
        CSS color string (green → orange → red).
    """
    if normalized <= 0.5:
        return _lerp_color(_COLOR_TIME_FAST, _COLOR_TIME_MID, normalized * 2)
    return _lerp_color(_COLOR_TIME_MID, _COLOR_TIME_SLOW, (normalized - 0.5) * 2)


def _node_size_time(status: str) -> int:
    """
    Marker size for Process Flow: Time nodes (status name + time line).

    Args:
        status: Raw status/stage label.

    Returns:
        Marker size in pixels — large enough for two label lines.
    """
    fmt = _format_label(status)
    max_line = max(len(ln) for ln in fmt.split("<br>"))
    n_lines = fmt.count("<br>") + 2  # status lines + 1 time line
    if max_line <= 6:
        h_size = 48
    elif max_line <= 9:
        h_size = 62
    else:
        h_size = 76
    v_size = n_lines * 14 + 16
    return max(h_size, v_size)


# ---------------------------------------------------------------------------
# Shared transition grouping
# ---------------------------------------------------------------------------

def _group_transitions(
    transitions: list[TransitionEntry],
    first_stage: str | None,
) -> dict[str, list[tuple[str, str]]]:
    """
    Group transitions by issue key with Created→first_stage mapping applied.

    'Created' entries (synthetic transform_data entries) are mapped to
    first_stage when available. A consecutive first_stage entry that
    immediately follows a Created-mapped entry is suppressed to avoid
    spurious self-loops. Genuine self-loops are preserved.

    Args:
        transitions: Flat list of TransitionEntry records (file order = chronological).
        first_stage: Stage to substitute for 'Created', or None to keep as-is.

    Returns:
        Dict mapping issue key to list of (label, timestamp_str) tuples.
    """
    skip_next: set[str] = set()
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for t in transitions:
        if t.label == "Created" and first_stage is not None:
            result[t.key].append((first_stage, t.timestamp))
            skip_next.add(t.key)
        elif t.key in skip_next:
            skip_next.discard(t.key)
            if t.label != first_stage:
                result[t.key].append((t.label, t.timestamp))
        else:
            result[t.key].append((t.label, t.timestamp))
    return result


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

    Node size scales with label length; multi-word labels are wrapped with
    <br> to keep lines short. Original names are preserved in hover via
    customdata.

    Args:
        fig:   Plotly Figure.
        nodes: Ordered list of node labels.
        pos:   Node positions.
    """
    xs = [pos[n][0] for n in nodes]
    ys = [pos[n][1] for n in nodes]
    formatted = [_format_label(n) for n in nodes]
    sizes = [_node_size(f) for f in formatted]

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=_COLOR_NODE_FILL,
            line=dict(color="#ffffff", width=2),
        ),
        text=formatted,
        customdata=nodes,
        textposition="middle center",
        textfont=dict(color=_COLOR_NODE_TEXT, size=10),
        hovertemplate="<b>%{customdata}</b><extra></extra>",
        showlegend=False,
    ))


def _add_nodes_time(
    fig: go.Figure,
    nodes: list[str],
    pos: dict[str, tuple[float, float]],
    stats_by_node: dict[str, _NodeTimeStats],
) -> None:
    """
    Draw Process Flow: Time nodes — colored by avg dwell time, two-line labels.

    Node fill uses a green→orange→red scale (fast→slow). Nodes without dwell
    data are shown in gray. Hover displays quartile statistics.

    Args:
        fig:           Plotly Figure.
        nodes:         Ordered list of status labels.
        pos:           Node positions.
        stats_by_node: Dwell time stats per status; missing key = no data.
    """
    xs = [pos[n][0] for n in nodes]
    ys = [pos[n][1] for n in nodes]

    # Color scale: normalize avg_minutes to [0, 1] across nodes with data
    avgs = [stats_by_node[n].avg_minutes for n in nodes if n in stats_by_node]
    min_avg = min(avgs) if avgs else 0.0
    max_avg = max(avgs) if avgs else 1.0
    span = max_avg - min_avg if max_avg > min_avg else 1.0

    colors: list[str] = []
    for n in nodes:
        if n in stats_by_node:
            norm = (stats_by_node[n].avg_minutes - min_avg) / span
            colors.append(_time_color(norm))
        else:
            colors.append(_COLOR_TIME_NONE)

    # Two-line node text: status name (possibly wrapped) + avg time
    display_labels: list[str] = []
    for n in nodes:
        name_fmt = _format_label(n)
        if n in stats_by_node:
            time_str = _format_duration(stats_by_node[n].avg_minutes)
            display_labels.append(f"{name_fmt}<br>Ø {time_str}")
        else:
            display_labels.append(f"{name_fmt}<br>—")

    sizes = [_node_size_time(n) for n in nodes]

    # customdata columns: [0] name, [1] avg, [2] Q1, [3] median, [4] Q3, [5] n
    customdata: list[list[str]] = []
    for n in nodes:
        s = stats_by_node.get(n)
        if s:
            customdata.append([
                n,
                f"Ø {_format_duration(s.avg_minutes)}",
                f"Q1: {_format_duration(s.q1_minutes)}",
                f"Median: {_format_duration(s.median_minutes)}",
                f"Q3: {_format_duration(s.q3_minutes)}",
                f"n = {s.n}",
            ])
        else:
            customdata.append([n, "keine Daten", "", "", "", ""])

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(color="#ffffff", width=2),
        ),
        text=display_labels,
        customdata=customdata,
        textposition="middle center",
        textfont=dict(color=_COLOR_NODE_TEXT, size=9),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "%{customdata[1]}<br>"
            "%{customdata[2]}<br>"
            "%{customdata[3]}<br>"
            "%{customdata[4]}<br>"
            "%{customdata[5]}"
            "<extra></extra>"
        ),
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

        first_stage = data.stages[0] if data.stages else None
        by_issue = _group_transitions(data.transitions, first_stage)

        # Count consecutive transition pairs
        edge_counter: Counter[tuple[str, str]] = Counter()
        for entries in by_issue.values():
            labels = [lbl for lbl, _ in entries]
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


class ProcessFlowTimeMetric(MetricPlugin):
    """
    Process Flow: Time metric.

    Same directed-graph layout as Process Flow: Transitions, but nodes are
    coloured and labelled by average dwell time in each status.  The colour
    scale runs green (fast) → orange → red (slow) to highlight bottlenecks.
    Mouse-hover shows Q1, median, Q3, and sample count for each status.
    Dwell time is computed as the elapsed time between consecutive status
    entries per issue.  The last status of each issue is excluded (no exit
    timestamp available).
    """

    metric_id = PROCESS_FLOW_TIME

    def compute(self, data: ReportData, terminology: str) -> MetricResult:
        """
        Compute average and quartile dwell times per status from transition data.

        Args:
            data:        ReportData — uses data.transitions and data.stages.
            terminology: Active terminology mode (unused here).

        Returns:
            MetricResult with _FlowTimeData as chart_data, or warnings if no data.
        """
        warnings: list[str] = []
        if not data.transitions:
            warnings.append("No transition data available. Load a Transitions.xlsx file.")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        first_stage = data.stages[0] if data.stages else None
        by_issue = _group_transitions(data.transitions, first_stage)

        # Compute dwell times and edge counts simultaneously
        dwell_times: dict[str, list[float]] = defaultdict(list)
        edge_counter: Counter[tuple[str, str]] = Counter()

        for entries in by_issue.values():
            for i in range(len(entries) - 1):
                lbl_a, ts_a = entries[i]
                lbl_b, ts_b = entries[i + 1]
                edge_counter[(lbl_a, lbl_b)] += 1
                dt_a = _parse_ts(ts_a)
                dt_b = _parse_ts(ts_b)
                if dt_a and dt_b:
                    minutes = (dt_b - dt_a).total_seconds() / 60
                    if minutes >= 0:
                        dwell_times[lbl_a].append(minutes)

        if not edge_counter:
            warnings.append("No transitions found (each issue has at most one status entry).")
            return MetricResult(metric_id=self.metric_id, warnings=warnings)

        total = sum(edge_counter.values())

        # Node ordering: workflow stages first, then alphabetically
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

        # Build per-node stats
        stats_by_node: dict[str, _NodeTimeStats] = {}
        for status, times in dwell_times.items():
            if len(times) >= 2:
                qs = statistics.quantiles(times, n=4)
                q1, med, q3 = qs[0], qs[1], qs[2]
            else:
                q1 = med = q3 = times[0]
            stats_by_node[status] = _NodeTimeStats(
                avg_minutes=statistics.mean(times),
                q1_minutes=q1,
                median_minutes=med,
                q3_minutes=q3,
                n=len(times),
            )

        flow_data = _FlowTimeData(
            nodes=ordered_nodes,
            edges=edges,
            stats_by_node=stats_by_node,
            issue_count=len(by_issue),
            workflow_stages=list(data.stages),
        )

        # Summary stats for the result header
        nodes_with_data = [n for n in ordered_nodes if n in stats_by_node]
        if nodes_with_data:
            slowest = max(nodes_with_data, key=lambda n: stats_by_node[n].avg_minutes)
            top_stat = (
                f"{slowest} "
                f"(Ø {_format_duration(stats_by_node[slowest].avg_minutes)})"
            )
        else:
            top_stat = "—"

        return MetricResult(
            metric_id=self.metric_id,
            stats=dict(
                nodes=len(ordered_nodes),
                issue_count=len(by_issue),
                nodes_with_data=len(nodes_with_data),
                slowest_stage=top_stat,
            ),
            chart_data=flow_data,
            warnings=warnings,
        )

    def render(self, result: MetricResult, terminology: str) -> list[go.Figure]:
        """
        Render the process flow time chart as a directed graph with coloured nodes.

        Args:
            result:      MetricResult from compute().
            terminology: Active terminology mode for the chart title.

        Returns:
            List with one plotly Figure, or empty list if no data.
        """
        if not result.chart_data:
            return []

        fd: _FlowTimeData = result.chart_data
        label = term(PROCESS_FLOW_TIME, terminology)

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

        for edge in fd.edges:
            width = _edge_width(edge, max_count)
            color = _edge_color(edge, fd.workflow_stages)
            if edge.is_self_loop:
                _add_self_loop(fig, edge.source, pos, edge, width, color)
            else:
                _add_edge(fig, edge, pos, bidirectional, width, color)

        _add_nodes_time(fig, fd.nodes, pos, fd.stats_by_node)

        # Color legend
        legend_items = [
            (_COLOR_TIME_FAST, "Fast (short dwell)"),
            (_COLOR_TIME_MID,  "Medium"),
            (_COLOR_TIME_SLOW, "Slow (bottleneck)"),
            (_COLOR_TIME_NONE, "No data"),
        ]
        for i, (col, txt) in enumerate(legend_items):
            fig.add_annotation(
                x=1.01, y=0.95 - i * 0.08,
                xref="paper", yref="paper",
                text=f'<span style="color:{col}; font-size:16px">●</span> {txt}',
                showarrow=False,
                xanchor="left",
                font=dict(size=11),
            )

        fig.update_layout(
            title=(
                f"{label}  —  {fd.issue_count} issues, "
                f"{len(fd.edges)} unique transitions"
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


register(ProcessFlowTimeMetric())
