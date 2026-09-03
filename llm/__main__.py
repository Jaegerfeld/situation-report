# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt: python -m llm → CLI (providers/test).
# =============================================================================

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
