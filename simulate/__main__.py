# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m simulate`. Ohne Argumente startet die GUI,
#   mit Argumenten das CLI für den Monte-Carlo-Forecast.
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """Dispatch to GUI (no args) or CLI (with args)."""
    if len(sys.argv) > 1:
        from simulate.cli import main as cli_main
        cli_main()
    else:
        try:
            from simulate.gui import main as gui_main
            gui_main()
        except ImportError as exc:
            print(
                f"ERROR: GUI dependencies are not available ({exc}).\n"
                "Run the CLI instead:  python -m simulate <IssueTimes.xlsx> "
                "--horizon 84 --output report.html",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
