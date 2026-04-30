# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für das launcher-Modul. Startet die Launcher-GUI, über die
#   alle verfügbaren SituationReport-Module geöffnet werden können.
# =============================================================================

import sys


def main() -> None:
    """Start the SituationReport launcher GUI."""
    try:
        from launcher.gui import main as gui_main
        gui_main()
    except ImportError as exc:
        print(f"ERROR: GUI dependencies not available ({exc}).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
