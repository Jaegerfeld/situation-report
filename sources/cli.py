# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   CLI des Quellen-Frameworks (C1/C2). "fetch" holt Kennzahlen einer Art
#   (slo/dora/quality) gemäß einer Quellen-Config und schreibt das
#   normierte Register-JSON; die Config darf MEHRERE Quellen enthalten —
#   deren Records werden zusammengeführt (Kombinierbarkeit), jede Zeile
#   behält ihre Herkunft. "providers" listet alle entdeckten Provider —
#   eine neue Quelle erscheint hier, sobald ihre Datei in
#   sources/providers/ liegt.
# =============================================================================

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .base import KINDS, discover_providers, record_to_dict

SOURCES_SCHEMA_VERSION = 1


def fetch_records(kind: str, source_configs: list[dict],
                  log=print) -> list[dict]:
    """
    Fetch and merge records of ``kind`` from one or more source configs.

    Each config carries a ``provider`` key; unknown providers or providers
    that cannot deliver the kind raise RuntimeError with the known options.

    Returns:
        Serialised records (dicts), sources concatenated in config order.
    """
    providers = discover_providers()
    records: list[dict] = []
    for cfg in source_configs:
        provider_id = str(cfg.get("provider", ""))
        provider = providers.get(provider_id)
        if provider is None:
            raise RuntimeError(
                f"Unknown provider '{provider_id}' — known: "
                f"{', '.join(providers)}.")
        if kind not in provider.kinds:
            raise RuntimeError(
                f"Provider '{provider_id}' delivers "
                f"{', '.join(provider.kinds)} — not '{kind}'.")
        log(f"Quelle '{provider_id}' ...")
        records.extend(record_to_dict(r)
                       for r in provider.fetch(kind, cfg, log))
    return records


def run_fetch(args: argparse.Namespace) -> int:
    """Execute the fetch sub-command; returns the process exit code."""
    try:
        raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read config: {exc}", file=sys.stderr)
        return 1
    source_configs = raw.get("sources") if isinstance(raw, dict) else None
    if not isinstance(source_configs, list):
        source_configs = [raw] if isinstance(raw, dict) else []
    if not source_configs:
        print("ERROR: config needs a source object or a 'sources' list.",
              file=sys.stderr)
        return 1

    try:
        records = fetch_records(args.kind, source_configs)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(
        {"schema": SOURCES_SCHEMA_VERSION, "kind": args.kind,
         "records": records},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(records)} {args.kind} records "
          f"from {len(source_configs)} source(s) -> {output}")
    return 0


def run_providers(_args: argparse.Namespace) -> int:
    """List all discovered providers with the kinds they deliver."""
    for provider_id, provider in discover_providers().items():
        print(f"{provider_id}: {', '.join(provider.kinds)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the sources CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m sources",
        description="Fetch external metrics (SLO/DORA/quality) from "
                    "pluggable sources into normalised register JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch records of one kind.")
    fetch.add_argument("--kind", choices=list(KINDS), required=True,
                       help="What to fetch: slo, dora or quality.")
    fetch.add_argument("--config", required=True, type=Path,
                       help="Source config JSON: one source object with a "
                            "'provider' key, or {'sources': [...]} to "
                            "combine several sources into one register.")
    fetch.add_argument("--output", required=True, type=Path,
                       help="Destination register JSON.")
    fetch.set_defaults(func=run_fetch)

    providers = sub.add_parser(
        "providers", help="List every discovered source provider.")
    providers.set_defaults(func=run_providers)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
