# =============================================================================
# Autor:          Robert Seebauer
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.04.2026
# Geändert:       10.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Universeller Einstiegspunkt für `python -m transform_data`. Leitet den
#   Aufruf automatisch weiter: ohne Argumente wird die grafische Oberfläche
#   gestartet, mit Argumenten wird die Kommandozeilen-Variante aufgerufen.
#   Auf Systemen ohne tkinter wird eine verständliche Fehlermeldung ausgegeben.
# =============================================================================

import sys


def main() -> None:
    if len(sys.argv) > 1:
        from transform_data.transform import main as cli_main
        cli_main()
    else:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print(
                "tkinter ist in dieser Python-Umgebung nicht verfügbar.\n"
                "Bitte CLI verwenden:\n"
                "  python -m transform_data.transform <json_datei> <workflow_datei>",
                file=sys.stderr,
            )
            sys.exit(1)
        from transform_data.gui import TransformApp
        TransformApp().mainloop()


if __name__ == "__main__":
    main()
