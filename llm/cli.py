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
        from .guard import draft_markdown
        target = source.with_suffix(source.suffix + f".{lang}.md")
        target.write_text(draft_markdown(narration, "d6_translation", lang),
                          encoding="utf-8")
        _print_utf8(f"{lang}: {target}")
    _print_utf8(f"audit: {audit}")
    return 0


def run_check(args: argparse.Namespace) -> int:
    """
    Check an external model's answer against its exported prompt bundle
    (the return path of the prompt export): numbers guard, questions guard
    for red-team answers, labelled draft file, audit record. Exit code 2
    when a guard rejects the answer - nothing is written then.
    """
    from .check import MODEL_UNKNOWN, find_bundle, read_clipboard
    from .check import run_check as _run

    if args.clipboard:
        answer = read_clipboard()
        if not answer.strip():
            print("ERROR: the clipboard is empty.", file=sys.stderr)
            return 1
        folder = Path(args.bundle).parent if args.bundle else Path.cwd()
    else:
        if not args.answer:
            print("ERROR: give the answer file or --clipboard.", file=sys.stderr)
            return 1
        try:
            answer = Path(args.answer).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        folder = Path(args.answer).parent
    bundle = Path(args.bundle) if args.bundle else find_bundle(folder)
    if bundle is None or not bundle.is_file():
        print(f"ERROR: no exported prompt bundle (prompt_*.md) found in {folder}; "
              f"name it with --bundle.", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else (
        Path(args.answer).with_suffix(Path(args.answer).suffix + ".checked.md")
        if args.answer else None)
    try:
        report = _run(answer, bundle, out_path=out, model=args.model or MODEL_UNKNOWN,
                      lang=args.lang, log=_print_utf8)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0 if report.passed else 2


def run_approve(args: argparse.Namespace) -> int:
    """
    Approve an AI draft file (R3): the marker turns to reviewed (team, date,
    edited yes/no), the banner becomes the approval line, the operator
    evidence records the release. Exit code 3 when the draft was never
    edited and --as-is is missing - nothing is written then.
    """
    from .approve import RC_UNEDITED, approve_file, marker_summary

    path = Path(args.file)
    if args.show:
        try:
            _print_utf8(marker_summary(path))
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0
    if not args.by:
        print("ERROR: give the approving team with --by (teams, never persons).", file=sys.stderr)
        return 1
    try:
        report = approve_file(path, args.by, note=args.note or "", as_is=args.as_is,
                              audit_path=Path(args.audit) if args.audit else None)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for line in report.messages:
        _print_utf8(line)
    if not report.reviewed_by:
        return RC_UNEDITED
    return 0


def run_literacy(args: argparse.Namespace) -> int:
    """
    AI literacy record (R4, Art. 4 AI Act): build the Markdown report from an
    ai_literacy.json log - status per team, measures, needs picture from the
    operator evidence, offer per topic. Exit code 2 when a team is due for a
    refresh or has no measure at all. --example writes a sample log instead.
    """
    import json
    from datetime import date

    from .literacy import example_log
    from .literacy import run_literacy as _run

    path = Path(args.log)
    if args.example:
        if path.exists() and not args.force:
            print(f"ERROR: {path} exists - use --force to overwrite.", file=sys.stderr)
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(example_log(), indent=2, ensure_ascii=False), encoding="utf-8")
        _print_utf8(f"example log written: {path}")
        return 0
    try:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        since = date.fromisoformat(args.since) if args.since else None
        text, rc = _run(path, as_of=as_of, audit_path=Path(args.audit) if args.audit else None,
                        since=since, output=Path(args.output) if args.output else None, lang=args.lang)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.output:
        _print_utf8(f"literacy report written: {args.output}" + (" (a team is due or has no measure)" if rc else ""))
    else:
        _print_utf8(text)
    return rc


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

    check = sub.add_parser(
        "check",
        help="Check an external model's answer against its exported prompt "
             "bundle (numbers guard; questions guard for d5_red_team), write "
             "the labelled draft <answer>.checked.md and an audit record. "
             "Exit code 2 = rejected, nothing written.")
    check.add_argument("answer", nargs="?", default=None,
                       help="File with the model's answer (or use --clipboard).")
    check.add_argument("--clipboard", action="store_true",
                       help="Read the answer from the clipboard instead of a file.")
    check.add_argument("--bundle", default=None, metavar="FILE",
                       help="The prompt_*.md bundle the answer belongs to "
                            "(default: newest one next to the answer).")
    check.add_argument("--model", default=None,
                       help="Name of the model that produced the answer, as you "
                            "know it (default: unbekannt). Goes into banner and audit.")
    check.add_argument("--out", default=None, metavar="FILE",
                       help="Where to write the labelled draft (default: "
                            "<answer>.checked.md, or <bundle>.checked.md with --clipboard).")
    check.add_argument("--lang", default=None, choices=["de", "en", "ro", "pt", "fr"],
                       help="Banner language (default: the bundle's draft language).")
    check.set_defaults(func=run_check)

    approve = sub.add_parser(
        "approve",
        help="Approve an AI draft file (R3): marker -> reviewed by TEAM, banner -> "
             "approval line (Art. 50(4)), audit record. Exit code 3 = the draft was "
             "never edited; confirm with --as-is.")
    approve.add_argument("file", help="The Markdown draft (.exec_summary.md, .narration.md, "
                                      ".ask.md, .checked.md, ...).")
    approve.add_argument("--by", default=None, metavar="TEAM",
                         help="The approving team (never a person).")
    approve.add_argument("--note", default=None, help="Optional short note stored in the marker.")
    approve.add_argument("--as-is", action="store_true", dest="as_is",
                         help="Approve although the text was not edited since the model wrote it.")
    approve.add_argument("--audit", default=None, metavar="FILE",
                         help="Operator evidence file (default: llm_audit.jsonl next to the draft).")
    approve.add_argument("--show", action="store_true",
                         help="Only print the file's AI markers, change nothing.")
    approve.set_defaults(func=run_approve)

    literacy = sub.add_parser(
        "literacy",
        help="AI literacy record (R4, Art. 4 AI Act): report from an ai_literacy.json log - "
             "status per team (current / refresh due / no measure), measures, needs picture "
             "from the operator evidence (--audit), offer per topic. Exit code 2 = a team is "
             "due or without measure. --example writes a sample log.")
    literacy.add_argument("log", help="The ai_literacy.json log (teams and counts, never names).")
    literacy.add_argument("--as-of", default=None, dest="as_of", metavar="DATE",
                          help="Reference date (default: today).")
    literacy.add_argument("--audit", default=None, metavar="FILE",
                          help="Operator evidence (llm_audit.jsonl) for the needs picture.")
    literacy.add_argument("--since", default=None, metavar="DATE",
                          help="Count only evidence records from this date on.")
    literacy.add_argument("--output", default=None, metavar="FILE",
                          help="Write the Markdown report here (default: print).")
    literacy.add_argument("--lang", default="de", choices=["de", "en"], help="Report language.")
    literacy.add_argument("--example", action="store_true",
                          help="Write an example log to LOG and exit.")
    literacy.add_argument("--force", action="store_true", help="With --example: overwrite an existing file.")
    literacy.set_defaults(func=run_literacy)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
