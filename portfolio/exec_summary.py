# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   D1 — LLM-Executive-Summary: der deterministische Summary-Contract
#   (Kennzahlen aus summary.py, eingefroren über build_snapshot, plus
#   Quell-Konfidenz und Governance-Kopfzahlen) als Markdown-Eingabe für
#   die KI-Schicht, und das Einfügen des gekennzeichneten Entwurfs
#   DIREKT UNTER der Management-Summary-Tabelle des Reports. Zahlen
#   entstehen ausschließlich hier im Datenpfad — das LLM formuliert nur
#   (Zahlen-Wächter, Art.-50-Banner und Audit kommen unumgehbar aus
#   llm/narrate.py). Der Contract nennt Einheiten und Registerzählungen,
#   nie Personen (Aggregat-Grenze strukturell: Owner-Felder tauchen im
#   Contract gar nicht auf).
# =============================================================================

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .snapshot import Snapshot, build_snapshot

if TYPE_CHECKING:  # pragma: no cover - nur fuer Typen
    from .solution_config import SolutionConfig

#: Register → Statusfeld für die Kopfzahlen des Contracts.
_REGISTER_STATUS_FIELDS = {
    "risks": "roam",
    "dependencies": "status",
    "nfr": "status",
    "runway": "status",
    "capabilities": "health",
    "decisions": "status",
    "flow_problems": "status",
    "epics": "status",
}


def _fmt(value: Any) -> str:
    """Display formatting of a metric (floats at one decimal, like delta)."""
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _metric_line(row: dict[str, Any]) -> str:
    return (f"- {row.get('label', '?')}: items {row.get('items')}, "
            f"completed {row.get('completed')}, open {row.get('open')}, "
            f"median CT {_fmt(row.get('median_ct'))} d, "
            f"P85 {_fmt(row.get('p85_ct'))} d, "
            f"P95 {_fmt(row.get('p95_ct'))} d, "
            f"target-CT share {_fmt(row.get('target_ct_pct'))} %, "
            f"median LT {_fmt(row.get('median_lt'))} d")


def summary_to_markdown(snap: Snapshot) -> str:
    """
    The deterministic exec-summary contract (D1 input, teams only).

    Everything the LLM may talk about stands in this text: pooled and
    per-unit metrics from summary.py, source confidence, and per-register
    head counts by status. Owner fields are deliberately absent.
    """
    lines = [
        f"# Executive-Summary-Contract - {snap.name} ({snap.kind})",
        f"As of {snap.as_of.isoformat()}; cycle-time target "
        f"{snap.target_ct} days.",
        "",
        "## Overall (pooled)",
        _metric_line(snap.total),
        "",
        "## Units",
    ]
    lines += [_metric_line(u) for u in snap.units]
    if snap.sources:
        lines += ["", "## Source confidence"]
        lines += [
            f"- {s.get('label', '?')}: {s.get('confidence', '?')}"
            + (f" (data as of {s.get('data_as_of')})"
               if s.get("data_as_of") else "")
            for s in snap.sources
        ]
    governance_lines = []
    for register, status_field in _REGISTER_STATUS_FIELDS.items():
        entries = snap.governance.get(register) or []
        if not entries:
            continue
        counts = Counter(str(e.get(status_field, "?")) for e in entries)
        parts = ", ".join(f"{status} {n}"
                          for status, n in sorted(counts.items()))
        governance_lines.append(f"- {register}: {len(entries)} ({parts})")
    slo_entries = snap.governance.get("slo") or []
    if slo_entries:
        governance_lines.append(f"- slo: {len(slo_entries)} services")
    if governance_lines:
        lines += ["", "## Governance head counts"] + governance_lines
    return "\n".join(lines)


def insert_after_summary(html_doc: str, section_html: str) -> str:
    """
    Insert a section right below the Management-Summary table.

    Falls back to the end of the page when the anchor is missing (a
    report variant without the summary block must never lose the draft).
    """
    marker = html_doc.find("Management Summary")
    if marker != -1:
        end = html_doc.find("</table>", marker)
        if end != -1:
            end += len("</table>")
            return html_doc[:end] + section_html + html_doc[end:]
    if "</body></html>" in html_doc:
        return html_doc.replace("</body></html>",
                                section_html + "</body></html>", 1)
    return html_doc + section_html


def attach_exec_summary(
    html_doc: str,
    config: SolutionConfig,
    provider_id: str,
    lang: str = "de",
    llm_model: str | None = None,
    audit_path: Path | None = None,
    as_of: date | None = None,
    target_ct: int = 90,
    attempts: int = 2,
    log: Callable[[str], None] = print,
) -> tuple[str, Any]:
    """
    Compute the contract, draft the exec summary and insert it (D1).

    Shared by CLI and GUI so the labeling can never diverge. Returns the
    page with the labeled draft section plus the Narration (for the
    separate ``.exec_summary.md`` editing file).

    A numbers-guard rejection is retried once by default: models are
    sampled, so a single unlucky draft should not cost the whole
    summary. Every attempt — including the rejected one — is written to
    the operator evidence, so the retry stays visible.

    Raises:
        RuntimeError:      Provider failure.
        NumbersGuardError: Every attempt invented numbers (the last
                           error is raised).
    """
    from llm.guard import NumbersGuardError
    from llm.narrate import narrate
    from llm.prompts import exec_summary_system_prompt

    from .cli import narration_html_section

    snap = build_snapshot(config, as_of=as_of, target_ct=target_ct,
                          log=lambda m: None)
    contract = summary_to_markdown(snap)
    for attempt in range(1, max(1, attempts) + 1):
        log(f"Executive summary draft via '{provider_id}' "
            f"(attempt {attempt}) ...")
        try:
            narration = narrate(
                contract, provider_id=provider_id, lang=lang,
                config={"model": llm_model} if llm_model else None,
                audit_path=audit_path,
                system_prompt=exec_summary_system_prompt(lang),
                purpose="d1_exec_summary")
        except NumbersGuardError:
            if attempt >= max(1, attempts):
                raise
            log("  numbers guard rejected the draft — retrying once")
            continue
        section = narration_html_section(
            narration, title="Executive Summary (Entwurf)")
        return insert_after_summary(html_doc, section), narration
    raise AssertionError("unreachable")  # pragma: no cover
