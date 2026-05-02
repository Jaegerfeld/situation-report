# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m testdata_generator`. Startet ohne Argumente
#   die GUI, mit Argumenten das CLI. Ermöglicht so `python -m testdata_generator`
#   für den interaktiven Betrieb und `python -m testdata_generator --workflow ...`
#   für die automatisierte Nutzung.
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """
    Dispatch to GUI or CLI based on whether arguments are provided.

    No arguments → launch the GUI (tkinter).
    Any arguments → delegate to the CLI (argparse pipeline).
    """
    if len(sys.argv) > 1:
        from testdata_generator.cli import main as cli_main
        cli_main()
    else:
        try:
            from testdata_generator.gui import main as gui_main
            gui_main()
        except ImportError as exc:
            print(
                f"ERROR: GUI dependencies are not installed ({exc}).\n"
                "Install them with:  pip install situation-report\n"
                "Or run the CLI:     python -m testdata_generator --workflow <file> --help",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
