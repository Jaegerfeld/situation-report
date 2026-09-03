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
from .validate import validate_export_file


def run_fetch(args: argparse.Namespace) -> int:
    """Execute the REST fetch sub-command; returns the process exit code."""
    token = os.environ.get(args.token_env, "")
    if not token:
        print(f"ERROR: environment variable {args.token_env} is empty — "
              f"set it to your Jira API token (never pass tokens as "
              f"command-line arguments).", file=sys.stderr)
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
    try:
        count = fetch_to_file(config, Path(args.output))
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{count} issues written to {args.output}")
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
    fetch.set_defaults(func=run_fetch)

    check = sub.add_parser(
        "check", help="Validate an existing manual export JSON.")
    check.add_argument("file", type=Path, help="Export JSON to validate.")
    check.set_defaults(func=run_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
