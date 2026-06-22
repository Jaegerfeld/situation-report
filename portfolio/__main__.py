# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m portfolio`. Ohne Argumente startet die
#   Verwaltungs-GUI (Solutions & Portfolios), mit Argumenten das CLI für den
#   aggregierten Report.
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """Dispatch to GUI (no args) or CLI (with args)."""
    if len(sys.argv) > 1:
        from portfolio.cli import main as cli_main
        cli_main()
    else:
        try:
            from portfolio.gui import main as gui_main
            gui_main()
        except ImportError as exc:
            print(
                f"ERROR: GUI dependencies are not available ({exc}).\n"
                "Run the CLI instead:  python -m portfolio <config.json> --output report.html",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
