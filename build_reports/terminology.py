# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Stellt die Terminologie-Umschaltung zwischen SAFe und Global bereit.
#   Jede Metrik hat in beiden Modi einen eigenen Namen. Die Funktion `term`
#   liefert den korrekten Begriff für den gewählten Modus.
# =============================================================================

from __future__ import annotations

# Supported terminology modes
SAFE = "SAFe"
GLOBAL = "Global"
MODES = (SAFE, GLOBAL)

# Metric IDs as constants
FLOW_TIME = "flow_time"
FLOW_VELOCITY = "flow_velocity"
FLOW_LOAD = "flow_load"
FLOW_DISTRIBUTION = "flow_distribution"
FLOW_PREDICTABILITY = "flow_predictability"
CFD = "cfd"

_TERMS: dict[str, dict[str, str]] = {
    SAFE: {
        FLOW_TIME: "Flow Time",
        FLOW_VELOCITY: "Flow Velocity",
        FLOW_LOAD: "Flow Load",
        FLOW_DISTRIBUTION: "Flow Distribution",
        FLOW_PREDICTABILITY: "Flow Predictability",
        CFD: "Cumulative Flow Diagram",
    },
    GLOBAL: {
        FLOW_TIME: "Cycle Time",
        FLOW_VELOCITY: "Throughput",
        FLOW_LOAD: "WIP",
        FLOW_DISTRIBUTION: "Flow Distribution",
        FLOW_PREDICTABILITY: "Flow Predictability",
        CFD: "Cumulative Flow Diagram",
    },
}


def term(metric_id: str, mode: str = SAFE) -> str:
    """
    Return the display name for a metric in the given terminology mode.

    Args:
        metric_id: One of the metric ID constants (e.g. FLOW_TIME).
        mode:      Terminology mode — either SAFE or GLOBAL.

    Returns:
        Human-readable metric name for the selected mode.

    Raises:
        KeyError: If metric_id or mode is unknown.
    """
    return _TERMS[mode][metric_id]


def all_terms(mode: str = SAFE) -> dict[str, str]:
    """
    Return all metric display names for the given terminology mode.

    Args:
        mode: Terminology mode — either SAFE or GLOBAL.

    Returns:
        Dict mapping metric_id to display name.

    Raises:
        KeyError: If mode is unknown.
    """
    return dict(_TERMS[mode])
