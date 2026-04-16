# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m build_reports`. Startet ohne Argumente die
#   GUI, mit Argumenten das CLI. Ermöglicht so `python -m build_reports` für
#   den interaktiven Betrieb und `python -m build_reports <xlsx> --pdf ...`
#   für die automatisierte Nutzung.
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """
    Dispatch to GUI or CLI based on whether arguments are provided.

    No arguments → launch the GUI (tkinter + pywebview).
    Any arguments → delegate to the CLI (argparse pipeline).
    """
    if len(sys.argv) > 1:
        # Arguments present → CLI mode
        from build_reports.cli import main as cli_main
        cli_main()
    else:
        # No arguments → GUI mode
        try:
            from build_reports.gui import main as gui_main
            gui_main()
        except ImportError as exc:
            print(
                f"ERROR: GUI dependencies are not installed ({exc}).\n"
                "Install them with:  pip install situation-report[gui]\n"
                "Or run the CLI:     python -m build_reports <IssueTimes.xlsx> --help",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
