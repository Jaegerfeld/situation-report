# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für get_data: ohne Argumente startet die GUI (beide
#   Erhebungswege wählbar), mit Argumenten läuft die CLI (fetch/check).
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """Dispatch: GUI without arguments, CLI with arguments."""
    if len(sys.argv) > 1:
        from .cli import main as cli_main

        sys.exit(cli_main())
    from .gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
