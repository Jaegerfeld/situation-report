# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       31.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einstiegspunkt für `python -m testdata_generator`. Startet ohne Argumente
#   die GUI, mit Argumenten das CLI. Ermöglicht so `python -m testdata_generator`
#   für den interaktiven Betrieb und `python -m testdata_generator --workflow ...`
#   für die automatisierte Nutzung. Stellt die Konsolenausgabe vorab auf UTF-8,
#   damit die Texte der fünf Sprachen (ă, ș, ç, ã …) auch in einer Windows-
#   Konsole mit Legacy-Zeichensatz (cp1252/cp850) nicht zum Absturz führen.
# =============================================================================

from __future__ import annotations

import sys
from typing import TextIO


def ensure_utf8_console(*streams: TextIO) -> None:
    """
    Switch the given text streams (default: stdout and stderr) to UTF-8.

    Windows consoles and piped output often use a legacy code page; printing
    Romanian or Portuguese text then raises UnicodeEncodeError. Streams that
    cannot be reconfigured (e.g. test doubles) are left untouched; characters
    a terminal still cannot show are replaced instead of aborting the run.
    """
    targets = streams or (sys.stdout, sys.stderr)
    for stream in targets:
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        encoding = (getattr(stream, "encoding", None) or "").replace("-", "").lower()
        if encoding == "utf8":
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main() -> None:
    """
    Dispatch to GUI or CLI based on whether arguments are provided.

    No arguments → launch the GUI (tkinter).
    Any arguments → delegate to the CLI (argparse pipeline).
    """
    ensure_utf8_console()
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
