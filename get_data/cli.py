# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kommandozeileninterface für get_data (Roadmap C3) mit BEIDEN
#   Erhebungswegen als eigene Unterbefehle: "fetch" holt Issues direkt per
#   Jira-REST (Token aus einer Umgebungsvariable, nie als Argument im
#   Klartext in der Prozessliste), "check" prüft einen vorhandenen
#   manuellen Export auf Vollständigkeit. Beide Wege liefern/prüfen
#   dasselbe JSON-Format für transform_data.
# =============================================================================

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client import (
    API_V2,
    API_V3,
    AUTH_BEARER,
    AUTH_CLOUD,
    JiraConfig,
    fetch_to_file,
)
from .minimise import check_keep, minimise_file
from .validate import validate_export_file


def run_fetch(args: argparse.Namespace) -> int:
    """Execute the REST fetch sub-command; returns the process exit code."""
    token = os.environ.get(args.token_env, "")
    if not token:
        print(f"ERROR: environment variable {args.token_env} is empty — "
              f"set it to your Jira API token (never pass tokens as "
              f"command-line arguments).", file=sys.stderr)
        return 1
    try:
        keep = check_keep(tuple(args.keep or ()))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    config = JiraConfig(
        base_url=args.url,
        token=token,
        project=args.project or "",
        jql=args.jql or "",
        api_version=args.api,
        auth_mode=args.auth,
        email=args.email or "",
        max_issues=args.max_issues,
    )
    if keep:
        config.fields = tuple(dict.fromkeys(config.fields + keep))
    try:
        count = fetch_to_file(config, Path(args.output), keep=keep)
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{count} issues written to {args.output}")
    return 0


def run_minimise(args: argparse.Namespace) -> int:
    """Minimise a manual export (R1); the original file stays untouched."""
    try:
        target, report = minimise_file(Path(args.file), args.output,
                                       tuple(args.keep or ()))
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for line in report.lines():
        print(line)
    print(f"Minimised export written to {target}")
    if report.persons_total:
        print(f"NOTE: the original {args.file} still holds person data - "
              f"delete it once the minimised file is checked.")
    return 0


def run_check(args: argparse.Namespace) -> int:
    """Execute the export-check sub-command; returns the process exit code."""
    check = validate_export_file(Path(args.file))
    for warning in check.warnings:
        print(f"WARNING: {warning}")
    for error in check.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if check.ok:
        print(f"OK: {check.issue_count} issues, ready for transform_data.")
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    """Entry point for the get_data CLI (both acquisition paths)."""
    parser = argparse.ArgumentParser(
        prog="python -m get_data",
        description="Fetch Jira issues via REST, or check a manual export — "
                    "two equal acquisition paths ending in the same JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser(
        "fetch", help="Fetch issues directly from Jira via REST API.")
    fetch.add_argument("--url", required=True,
                       help="Jira base URL, e.g. https://company.atlassian.net")
    fetch.add_argument("--project", default="",
                       help="Project key (builds the default JQL).")
    fetch.add_argument("--jql", default="",
                       help="Explicit JQL (overrides --project).")
    fetch.add_argument("--api", choices=[API_V3, API_V2], default=API_V3,
                       help="Jira REST API version (default: v3).")
    fetch.add_argument("--auth", choices=[AUTH_CLOUD, AUTH_BEARER],
                       default=AUTH_CLOUD,
                       help="cloud = Basic (e-mail + API token, Jira Cloud); "
                            "bearer = PAT (Server/Data Center).")
    fetch.add_argument("--email", default="",
                       help="Account e-mail (required for --auth cloud).")
    fetch.add_argument("--token-env", default="JIRA_TOKEN", dest="token_env",
                       metavar="NAME",
                       help="Environment variable holding the API token "
                            "(default: JIRA_TOKEN).")
    fetch.add_argument("--max-issues", type=int, default=10000,
                       dest="max_issues",
                       help="Safety cap on fetched issues (default: 10000).")
    fetch.add_argument("--output", required=True, type=Path,
                       help="Destination JSON file (transform_data input).")
    fetch.add_argument("--keep", nargs="+", default=None, metavar="FIELD",
                       help="Extra non-person issue fields to fetch and keep "
                            "(e.g. summary labels). The export is always "
                            "minimised: person fields never reach the file.")
    fetch.set_defaults(func=run_fetch)

    check = sub.add_parser(
        "check", help="Validate an existing manual export JSON.")
    check.add_argument("file", type=Path, help="Export JSON to validate.")
    check.set_defaults(func=run_check)

    minimise = sub.add_parser(
        "minimise", help="Reduce a manual export to the fields transform_data "
                         "reads and anonymise persons in the changelog (R1).")
    minimise.add_argument("file", type=Path, help="Export JSON to minimise.")
    minimise.add_argument("--output", type=Path, default=None,
                          help="Target file (default: <name>_min.json next to "
                               "the source; the original stays untouched).")
    minimise.add_argument("--keep", nargs="+", default=None, metavar="FIELD",
                          help="Extra non-person issue fields to keep.")
    minimise.set_defaults(func=run_minimise)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
