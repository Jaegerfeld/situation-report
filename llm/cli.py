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
from pathlib import Path

from .audit import AUDIT_FILENAME
from .base import discover_providers, provider_config
from .narrate import narrate
from .prompts import TRANSLATION_LANGS
from .translate import translate_text


def run_providers(_args: argparse.Namespace) -> int:
    """List every discovered provider with model and deployment class."""
    for provider_id, provider in discover_providers().items():
        print(f"{provider_id}: default={provider.default_model} "
              f"({provider.deployment_class})")
    return 0


def _normalise(name: str) -> str:
    """Compare model names the way the naming scheme means them, not literally."""
    try:
        from .providers.ollama import normalise_model
        return normalise_model(name)
    except Exception:  # noqa: BLE001 - a listing must not fail over a marker
        return name


def run_models(args: argparse.Namespace) -> int:
    """
    List the models a provider has available (Ollama: what has been pulled).

    Not every backend can enumerate its models without credentials, so this
    is an optional provider capability rather than part of the contract.
    """
    providers = discover_providers()
    provider = providers.get(args.llm)
    if provider is None:
        print(f"ERROR: unknown provider '{args.llm}'. Known: "
              f"{', '.join(providers)}", file=sys.stderr)
        return 1
    lister = getattr(provider, "list_models", None)
    if lister is None:
        print(f"{args.llm} cannot list its models; default is "
              f"{provider.default_model}.")
        return 0
    models = lister(provider_config(base_url=args.base_url))
    if not models:
        print(f"No models reported by '{args.llm}'. Is it running and "
              f"reachable? (default would be {provider.default_model})",
              file=sys.stderr)
        return 1
    default = _normalise(provider.default_model)
    for name in models:
        marker = "  <- default" if _normalise(name) == default else ""
        print(f"{name}{marker}")
    return 0


def run_test(args: argparse.Namespace) -> int:
    """One guarded sample completion (the post-install wiring check)."""
    sample = ("# Delta Briefing - Probe\n"
              "- Solution Demo - Completed: 12 -> 34\n"
              "- [Demo] D-1: sample dependency - at_risk -> blocked\n")
    try:
        narration = narrate(sample, provider_id=args.llm, lang=args.lang,
                            config=provider_config(args.model,
                                                   args.base_url))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    out = f"[{narration.banner}]\n\n{narration.text}"
    try:
        print(out)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(out.encode("utf-8") + b"\n")
    return 0


def _print_utf8(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")


def run_translate(args: argparse.Namespace) -> int:
    """
    Translate a briefing/draft file into house languages (D6).

    The typical workflow: a human edits and approves the German draft,
    then hands the FINAL wording to this command for delivery in the
    other languages — each output carries the target-language AI banner
    and its own audit record (purpose d6_translation).
    """
    source = Path(args.file)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    audit = source.parent / AUDIT_FILENAME
    for lang in args.to:
        try:
            narration = translate_text(
                text, lang, provider_id=args.llm,
                config=provider_config(args.model, args.base_url),
                audit_path=audit)
        except (ValueError, RuntimeError) as exc:
            print(f"ERROR [{lang}]: {exc}", file=sys.stderr)
            return 1
        target = source.with_suffix(source.suffix + f".{lang}.md")
        target.write_text(f"> {narration.banner}\n\n{narration.text}\n",
                          encoding="utf-8")
        _print_utf8(f"{lang}: {target}")
    _print_utf8(f"audit: {audit}")
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

    models = sub.add_parser(
        "models", help="List the models a provider has available.")
    models.add_argument("--llm", default="ollama",
                        help="Provider id (default: ollama).")
    models.add_argument("--base-url", default=None, dest="base_url",
                        metavar="URL",
                        help="Ollama address (default: $OLLAMA_HOST, else "
                             "http://localhost:11434).")
    models.set_defaults(func=run_models)

    test = sub.add_parser("test", help="Run one guarded sample completion.")
    test.add_argument("--llm", default="ollama",
                      help="Provider id (default: ollama).")
    test.add_argument("--model", default=None,
                      help="Model override (default: provider default). "
                           "Use the name as 'ollama list' prints it, tag "
                           "included, e.g. llama3.1:8b.")
    test.add_argument("--base-url", default=None, dest="base_url",
                      metavar="URL",
                      help="Ollama address (default: $OLLAMA_HOST, else "
                           "http://localhost:11434).")
    test.add_argument("--lang", default="de", choices=["de", "en"],
                      help="Narration language (default: de).")
    test.set_defaults(func=run_test)

    translate = sub.add_parser(
        "translate",
        help="Translate a briefing/draft file into house languages "
             "(writes <file>.<lang>.md with the target-language AI "
             "banner; audit purpose d6_translation).")
    translate.add_argument("file", help="Text file to translate "
                                        "(e.g. an edited draft .md).")
    translate.add_argument("--to", nargs="+", required=True,
                           choices=sorted(TRANSLATION_LANGS),
                           help="Target language(s).")
    translate.add_argument("--llm", default="ollama",
                           help="Provider id (default: ollama).")
    translate.add_argument("--model", default=None,
                           help="Model override (default: provider "
                                "default). Use the name as 'ollama list' "
                                "prints it, tag included.")
    translate.add_argument("--base-url", default=None, dest="base_url",
                           metavar="URL",
                           help="Ollama address (default: $OLLAMA_HOST, "
                                "else http://localhost:11434).")
    translate.set_defaults(func=run_translate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
