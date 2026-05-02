# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für das helper-Modul (JSON Merger). Nimmt mehrere
#   Jira-REST-API-JSON-Dateien als Eingabe, führt sie zusammen und schreibt
#   eine einzelne Ausgabedatei. Deduplizierung nach Issue-ID ist standardmäßig
#   aktiv und kann deaktiviert werden.
# =============================================================================

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .merger import merge_json_files


def run_merge(
    inputs: list[Path],
    output: Path,
    deduplicate: bool = True,
    log: Callable[[str], None] = print,
) -> None:
    """
    Execute the full JSON merge pipeline: validate inputs → merge → write output.

    Called by both the CLI and the GUI. The log parameter accepts any callable
    that takes a single string — defaults to print for CLI use.

    Args:
        inputs:      List of input JSON file paths (at least one required).
        output:      Destination path for the merged JSON file.
        deduplicate: Remove duplicate issues by their "id" field (default: True).
        log:         Callable for progress and warning messages.
    """
    missing = [p for p in inputs if not p.exists()]
    if missing:
        for p in missing:
            log(f"ERROR: Input file not found: {p}")
        return

    try:
        merge_json_files(inputs=inputs, output=output, deduplicate=deduplicate, log=log)
    except ValueError as exc:
        log(f"ERROR: {exc}")
        return

    log(f"Done. Output: {output}")


def main() -> None:
    """Entry point for CLI mode (called by __main__.py when args are present)."""
    parser = argparse.ArgumentParser(
        prog="python -m helper",
        description="Merge multiple Jira REST API JSON files into one.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        metavar="FILE",
        help="Input JSON files (Jira REST API format). At least one required.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        metavar="FILE",
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        default=False,
        help="Disable deduplication by issue id (keep all issues including duplicates).",
    )

    args = parser.parse_args()

    run_merge(
        inputs=args.inputs,
        output=args.output,
        deduplicate=not args.no_dedup,
    )

    missing = [p for p in args.inputs if not p.exists()]
    if missing:
        sys.exit(1)
