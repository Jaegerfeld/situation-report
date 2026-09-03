# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   CLI des KI-Frameworks: "providers" listet die entdeckten Anbieter
#   (Inventar — eine neue Datei in llm/providers/ erscheint hier), und
#   "test" macht einen kurzen, gekennzeichneten Probelauf gegen einen
#   Provider — der Verkabelungs-Check nach der Ollama-Installation.
# =============================================================================

from __future__ import annotations

import argparse
import sys

from .base import discover_providers
from .narrate import narrate


def run_providers(_args: argparse.Namespace) -> int:
    """List every discovered provider with model and deployment class."""
    for provider_id, provider in discover_providers().items():
        print(f"{provider_id}: default={provider.default_model} "
              f"({provider.deployment_class})")
    return 0


def run_test(args: argparse.Namespace) -> int:
    """One guarded sample completion (the post-install wiring check)."""
    sample = ("# Delta Briefing - Probe\n"
              "- Solution Demo - Completed: 12 -> 34\n"
              "- [Demo] D-1: sample dependency - at_risk -> blocked\n")
    try:
        narration = narrate(sample, provider_id=args.llm, lang=args.lang,
                            config={"model": args.model} if args.model else None)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    out = f"[{narration.banner}]\n\n{narration.text}"
    try:
        print(out)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(out.encode("utf-8") + b"\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the llm CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m llm",
        description="Pluggable LLM layer: list providers, run a labeled "
                    "test completion.")
    sub = parser.add_subparsers(dest="command", required=True)

    providers = sub.add_parser("providers",
                               help="List every discovered LLM provider.")
    providers.set_defaults(func=run_providers)

    test = sub.add_parser("test", help="Run one guarded sample completion.")
    test.add_argument("--llm", default="ollama",
                      help="Provider id (default: ollama).")
    test.add_argument("--model", default=None,
                      help="Model override (default: provider default).")
    test.add_argument("--lang", default="de", choices=["de", "en"],
                      help="Narration language (default: de).")
    test.set_defaults(func=run_test)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
