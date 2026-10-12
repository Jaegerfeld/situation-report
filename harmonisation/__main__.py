# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m harmonisation`. Ohne Argumente startet die
#   GUI, mit Argumenten das CLI (Arbeitsbereich → Entscheider-Matrix).
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """Dispatch to GUI (no args) or CLI (with args)."""
    if len(sys.argv) > 1:
        from harmonisation.cli import main as cli_main
        sys.exit(cli_main())
    try:
        from harmonisation.gui import main as gui_main
    except ImportError as exc:
        print(f"ERROR: GUI dependencies are not available ({exc}).\n"
              "Run the CLI instead:  python -m harmonisation <workspace> "
              "--lang de --browser", file=sys.stderr)
        sys.exit(1)
    gui_main()


if __name__ == "__main__":
    main()
