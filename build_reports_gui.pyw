# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Doppelklick-Starter für die build_reports-GUI. Wird mit pythonw.exe
#   ausgeführt (kein Konsolenfenster). Fügt das Projektverzeichnis in den
#   sys.path ein, damit build_reports auch ohne Installation gefunden wird.
# =============================================================================

import sys
from pathlib import Path

# Make sure the project root is importable regardless of working directory
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from build_reports.gui import main

main()
