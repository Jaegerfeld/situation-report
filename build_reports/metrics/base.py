# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Definiert die abstrakte Basisklasse MetricPlugin sowie den zugehörigen
#   MetricResult-Container. Jede Metrik implementiert compute() zur
#   Berechnung von Statistiken und render() zur Erzeugung von plotly-Figures.
#   Das Plugin-System erlaubt das Hinzufügen neuer Metriken durch Ablegen
#   einer neuen Datei im metrics/-Verzeichnis.
# =============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    """
    Container for the output of a metric computation.

    Attributes:
        metric_id:  Identifier of the metric that produced this result (e.g. 'flow_time').
        stats:      Key/value pairs of computed statistics (e.g. median, mean, count).
        chart_data: Arbitrary data passed from compute() to render() for figure construction.
        warnings:   Optional list of human-readable warnings produced during computation.
    """
    metric_id: str
    stats: dict[str, Any] = field(default_factory=dict)
    chart_data: Any = None
    warnings: list[str] = field(default_factory=list)


class MetricPlugin(ABC):
    """
    Abstract base class for all build_reports metric plugins.

    Subclasses must declare a unique `metric_id` class attribute and implement
    `compute()` and `render()`. They are auto-registered via MetricRegistry
    when the metrics package is imported.

    Class attributes:
        metric_id: Unique string key matching a constant in terminology.py
                   (e.g. 'flow_time', 'flow_velocity').
    """

    metric_id: str = ""

    @abstractmethod
    def compute(self, data: "ReportData", terminology: str) -> MetricResult:  # noqa: F821
        """
        Compute statistics for this metric from the provided report data.

        Args:
            data:        Filtered ReportData from loader.py.
            terminology: Active mode — either terminology.SAFE or terminology.GLOBAL.

        Returns:
            MetricResult with stats and chart_data populated.
        """

    @abstractmethod
    def render(self, result: MetricResult, terminology: str) -> list[Any]:
        """
        Build a list of plotly Figure objects from a MetricResult.

        One metric may produce multiple figures (e.g. Flow Time produces
        a boxplot and a scatterplot).

        Args:
            result:      MetricResult produced by compute().
            terminology: Active mode — either terminology.SAFE or terminology.GLOBAL.

        Returns:
            List of plotly Figure objects ready for display or export.
        """
