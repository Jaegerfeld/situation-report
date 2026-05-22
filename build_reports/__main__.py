# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       22.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m build_reports`. Startet ohne Argumente die
#   GUI, mit Argumenten das CLI. Ermöglicht so `python -m build_reports` für
#   den interaktiven Betrieb und `python -m build_reports <xlsx> --pdf ...`
#   für die automatisierte Nutzung. Das Sonderflag `--gui-template <pfad>`
#   startet die GUI und lädt das angegebene Projekt-Template (Datenübergabe
#   aus transform_data).
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

#: GUI-Flag zur Datenübergabe: lädt ein Projekt-Template direkt beim Start.
_GUI_TEMPLATE_FLAG = "--gui-template"


def _launch_gui(handover_template: Path | None = None) -> None:
    """Start the build_reports GUI, optionally pre-loading a handover template."""
    try:
        from build_reports.gui import main as gui_main
    except ImportError as exc:
        print(
            f"ERROR: GUI dependencies are not installed ({exc}).\n"
            "Install them with:  pip install situation-report[gui]\n"
            "Or run the CLI:     python -m build_reports <IssueTimes.xlsx> --help",
            file=sys.stderr,
        )
        sys.exit(1)
    gui_main(handover_template=handover_template)


def main() -> None:
    """
    Dispatch to GUI or CLI based on the command-line arguments.

    No arguments              → launch the GUI (tkinter + pywebview).
    ``--gui-template <path>`` → launch the GUI and load the given template.
    Any other arguments       → delegate to the CLI (argparse pipeline).
    """
    args = sys.argv[1:]

    if args and args[0] == _GUI_TEMPLATE_FLAG:
        if len(args) < 2:
            print(
                f"ERROR: {_GUI_TEMPLATE_FLAG} requires a template file path.",
                file=sys.stderr,
            )
            sys.exit(1)
        _launch_gui(Path(args[1]))
    elif args:
        # Arguments present → CLI mode
        from build_reports.cli import main as cli_main
        cli_main()
    else:
        # No arguments → GUI mode
        _launch_gui()


if __name__ == "__main__":
    main()
