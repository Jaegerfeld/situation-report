# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Plugin-Registry für Metriken. Neue Metriken werden durch Import ihrer
#   Moduldate automatisch registriert. get_metric() liefert eine Instanz
#   anhand der metric_id. all_metrics() liefert alle registrierten Plugins.
# =============================================================================

from __future__ import annotations

from .base import MetricPlugin, MetricResult

_REGISTRY: dict[str, MetricPlugin] = {}


def register(plugin: MetricPlugin) -> MetricPlugin:
    """
    Register a MetricPlugin instance in the global registry.

    Typically called at module level in each metric file:
        register(FlowTimeMetric())

    Args:
        plugin: Instantiated MetricPlugin subclass to register.

    Returns:
        The same plugin instance (allows use as a decorator target).

    Raises:
        ValueError: If a plugin with the same metric_id is already registered.
    """
    if plugin.metric_id in _REGISTRY:
        raise ValueError(f"Metric '{plugin.metric_id}' is already registered.")
    _REGISTRY[plugin.metric_id] = plugin
    return plugin


def get_metric(metric_id: str) -> MetricPlugin:
    """
    Retrieve a registered metric plugin by its ID.

    Args:
        metric_id: The metric identifier (e.g. 'flow_time').

    Returns:
        The registered MetricPlugin instance.

    Raises:
        KeyError: If no metric with the given ID is registered.
    """
    return _REGISTRY[metric_id]


def all_metrics() -> list[MetricPlugin]:
    """
    Return all registered metric plugins in registration order.

    Returns:
        List of MetricPlugin instances.
    """
    return list(_REGISTRY.values())


# Import metric modules to trigger auto-registration.
# Add new metric modules here when they are created.
from . import flow_time          # noqa: E402, F401
from . import flow_velocity      # noqa: E402, F401
from . import flow_load          # noqa: E402, F401
from . import cfd                # noqa: E402, F401
from . import flow_distribution  # noqa: E402, F401
from . import process_flow       # noqa: E402, F401
