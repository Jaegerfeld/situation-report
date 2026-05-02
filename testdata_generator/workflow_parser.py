# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Thin re-export wrapper um transform_data.workflow. Stellt WorkflowSpec
#   (Alias für Workflow) und parse_workflow für den testdata_generator bereit,
#   ohne die Parsing-Logik zu duplizieren.
# =============================================================================

from __future__ import annotations

from transform_data.workflow import Workflow as WorkflowSpec
from transform_data.workflow import parse_workflow

__all__ = ["WorkflowSpec", "parse_workflow"]
