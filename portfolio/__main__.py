# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m portfolio`. Phase 1 stellt nur das CLI bereit
#   (aggregierter Pooled-Report). Die geteilte Einstiegs-/Verwaltungs-GUI folgt
#   in Phase 2; bis dahin verweist ein Aufruf ohne Argumente auf das CLI.
# =============================================================================

from __future__ import annotations

import sys


def main() -> None:
    """Dispatch to the portfolio CLI (the GUI is a Phase-2 deliverable)."""
    if len(sys.argv) > 1:
        from portfolio.cli import main as cli_main
        cli_main()
    else:
        print(
            "portfolio (Phase 1) currently provides a CLI only.\n"
            "Usage:  python -m portfolio <solution-config.json> --output report.html\n"
            "The split management GUI is planned for Phase 2.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
