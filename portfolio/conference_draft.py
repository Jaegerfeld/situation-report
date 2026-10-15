# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   D8 — KI-Entwurf für die Konferenzmappe (Entscheidung Robert 12.10.2026):
#   fünf Teile — eine Einleitung über alle vier Inputs und je Input ein
#   Absatz —, erzeugt NUR auf ausdrücklichen Schalter, und der Ort ist
#   wählbar: als separate Entwurfsdatei neben der Mappe (Standard, der
#   vorsichtige Weg: die vorgelesene Unterlage bleibt deterministisch) oder
#   gekennzeichnet in der Mappe selbst. Jeder Teil hat seinen eigenen
#   deterministischen Contract aus denselben Registern, die die Mappe
#   zeigt; Zahlen entstehen nur hier, das Modell formuliert. Zahlen-Wächter,
#   Art.-50-Banner und Betreiber-Nachweis kommen unumgehbar aus
#   llm/narrate.py (Zweck d8_conference). Owner, Befragte, Personen tauchen
#   in keinem Contract auf. Scheitert ein Teil, fehlt er — die anderen und
#   die Mappe stehen.
# =============================================================================

from __future__ import annotations

import html as _html
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm.guard import text_as_data as _data

from .report_texts import DEFAULT_LANG, t

if TYPE_CHECKING:  # pragma: no cover - nur fuer Typen
    from .solution_config import SolutionConfig

#: Audit purpose tag of every conference draft part.
PURPOSE = "d8_conference"

#: Where the draft goes: a separate editing file only, or also into the page.
PLACE_FILE = "file"
PLACE_INLINE = "inline"
PLACES = (PLACE_FILE, PLACE_INLINE)

#: The five parts, in page order. ``intro`` precedes the first input block.
PART_INTRO = "intro"
PARTS = (PART_INTRO, "input1", "input2", "input3", "input4")


@dataclass
class ConferenceDraft:
    """The drafted parts (None = that part failed or was not requested)."""
    parts: dict[str, Any] = field(default_factory=dict)      # part -> Narration
    failures: dict[str, str] = field(default_factory=dict)   # part -> reason

    @property
    def empty(self) -> bool:
        return not self.parts


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _counts(entries: list[Any], attr: str) -> str:
    counter = Counter(str(getattr(e, attr)) for e in entries)
    return ", ".join(f"{k} {n}" for k, n in sorted(counter.items())) or "none"


def _conference_line(conference_date: date | None, today: date) -> str:
    if conference_date is None:
        return "Conference date: not set."
    days = (conference_date - today).days
    return f"Conference date: {conference_date.isoformat()} ({days} days from {today.isoformat()})."


def conference_contracts(
    config: SolutionConfig,
    conference_date: date | None = None,
    today: date | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, str]:
    """
    The deterministic contracts, one per part — built from the same
    collectors the pre-read renders, so draft and page can never disagree.

    Every contract names units, teams, ARTs, solutions and registers; owner
    fields and raisers are deliberately absent (aggregate boundary, as D1).
    """
    from .aggregator import (
        _collect_capabilities,
        _collect_dependencies,
        _collect_flow_problems,
        _collect_risks,
        _collect_slo,
        _collect_themes,
    )
    from .exec_summary import _metric_line
    from .snapshot import build_snapshot

    today = today or date.today()
    conference_date = conference_date or config.conference_date
    quiet = log if log is not print else (lambda m: None)
    snap = build_snapshot(config, as_of=today, log=quiet)
    head = [f"# Conference pre-read contract - {config.name} ({config.kind})",
            _conference_line(conference_date, today), ""]

    # Input 1 - current data
    in1 = head + ["## Part: Input 1 - current data",
                  f"Cycle-time target {snap.target_ct} days.", "### Overall (pooled)",
                  _metric_line(snap.total), "### Units"]
    in1 += [_metric_line(u) for u in snap.units]
    if snap.sources:
        in1 += ["### Source confidence"]
        in1 += [f"- {s.get('label', '?')}: {s.get('confidence', '?')}"
                + (f" (data as of {s.get('data_as_of')})" if s.get("data_as_of") else "")
                for s in snap.sources]

    # Input 2 - impediment backlog & governance
    flow = [p for _, p in _collect_flow_problems(config, log=quiet)]
    risks = [r for _, r in _collect_risks(config, log=quiet)]
    deps = [d for _, d in _collect_dependencies(config, log=quiet)]
    survived = [p for p in flow if p.survived]
    cross = [p for p in flow if p.cross_vs]
    in2 = head + ["## Part: Input 2 - impediment backlog and governance",
                  f"- flow problems: {len(flow)} ({_counts(flow, 'status')})",
                  f"- flow problems unresolved for 3 or more conferences: {len(survived)}"]
    # Leitplanke (e): titles and names from the registers are data, never instructions
    in2 += [f"  - {_data(p.title)} (conferences {p.conferences}, value streams "
            f"{', '.join(_data(v, 60) for v in p.value_streams)})" for p in survived]
    in2 += [f"- cross-value-stream problems: {len(cross)}",
            f"- ROAM risks: {len(risks)} ({_counts(risks, 'roam')})",
            f"- dependencies: {len(deps)} ({_counts(deps, 'status')})"]
    overdue = [d for d in deps if d.due and d.due < today
               and str(d.status) not in ("done", "resolved")]
    in2 += [f"- dependencies overdue: {len(overdue)}"]

    # Input 3 - business objectives
    caps = [c for _, c in _collect_capabilities(config, log=quiet)]
    slos = [s for _, s in _collect_slo(config, log=quiet)]
    in3 = head + ["## Part: Input 3 - business objectives",
                  f"- capabilities: {len(caps)} ({_counts(caps, 'health')})"]
    in3 += [f"  - {_data(c.title)}: {c.health}" for c in caps if str(c.health) != "ok"]
    in3 += [f"- SLOs: {len(slos)} services"]
    for s in slos:
        sli = f"{_fmt(s.sli_pct)} %" if s.sli_pct is not None else "no indicator"
        in3.append(f"  - {_data(s.service, 80)}: target {_fmt(s.target_pct)} %, current {sli}")

    # Input 4 - roadmap & themes
    themes, epics = _collect_themes(config, log=quiet)
    theme_list = [th for _, th in themes]
    epic_list = [e for _, e in epics]
    used = {e.theme for e in epic_list if e.theme}
    forgotten = [th for th in theme_list if th.theme_id not in used]
    zombies = [e for e in epic_list if not e.theme]
    in4 = head + ["## Part: Input 4 - integrated roadmap and strategic themes",
                  f"- strategic themes: {len(theme_list)}, without any epic: {len(forgotten)}",
                  f"- epics: {len(epic_list)} ({_counts(epic_list, 'status')}); "
                  f"by horizon: {_counts(epic_list, 'horizon')}",
                  f"- epics without a strategic theme: {len(zombies)}"]
    in4 += [f"  - {_data(e.title)} ({_data(e.train, 60)}, {e.horizon})" for e in zombies]

    intro = head + ["## Part: Introduction over all four inputs",
                    "### Current data", _metric_line(snap.total),
                    f"- units: {len(snap.units)}; sources with low confidence: "
                    f"{sum(1 for s in snap.sources if s.get('confidence') == 'low')} "
                    f"of {len(snap.sources)}",
                    "### Impediment backlog",
                    f"- flow problems {len(flow)}, unresolved for 3 or more conferences "
                    f"{len(survived)}, cross-value-stream {len(cross)}",
                    f"- risks {len(risks)} ({_counts(risks, 'roam')}); dependencies {len(deps)}, "
                    f"overdue {len(overdue)}",
                    "### Business objectives",
                    f"- capabilities {len(caps)} ({_counts(caps, 'health')}); SLOs {len(slos)}",
                    "### Roadmap",
                    f"- themes {len(theme_list)} (without epic {len(forgotten)}); epics "
                    f"{len(epic_list)}, without theme {len(zombies)}"]
    return {PART_INTRO: "\n".join(intro) + "\n", "input1": "\n".join(in1) + "\n",
            "input2": "\n".join(in2) + "\n", "input3": "\n".join(in3) + "\n",
            "input4": "\n".join(in4) + "\n"}


def draft_conference(
    contracts: dict[str, str],
    provider_id: str,
    lang: str = DEFAULT_LANG,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    audit_path: Path | None = None,
    log: Callable[[str], None] = print,
) -> ConferenceDraft:
    """
    Draft every part; a part whose draft fails (provider error, numbers
    guard after one retry) is recorded in ``failures`` and left out — the
    other parts and the page itself stand.
    """
    from llm.base import provider_config
    from llm.guard import NumbersGuardError
    from llm.narrate import narrate
    from llm.prompts import conference_system_prompt

    draft = ConferenceDraft()
    for part in PARTS:
        contract = contracts.get(part)
        if not contract:
            continue
        last: Exception | None = None
        for attempt in (1, 2):
            log(f"Conference draft '{part}' via '{provider_id}' (attempt {attempt}) ...")
            try:
                draft.parts[part] = narrate(
                    contract, provider_id=provider_id, lang=lang,
                    config=provider_config(llm_model, llm_base_url),
                    audit_path=audit_path,
                    system_prompt=conference_system_prompt(lang), purpose=PURPOSE)
                last = None
                break
            except NumbersGuardError as exc:
                last = exc
                log("  numbers guard rejected the draft")
            except RuntimeError as exc:
                last = exc
                break
        if last is not None:
            draft.failures[part] = str(last)
            log(f"  WARNING: part '{part}' skipped - {last}")
    return draft


def part_title(part: str, lang: str) -> str:
    """The labeled heading of one part, in the page language."""
    if part == PART_INTRO:
        return t("vsc.draft.intro", lang)
    return t("vsc.draft.part", lang, input=t(f"vsc.{part}", lang))


def draft_html_section(narration: Any, title: str) -> str:
    """Banner (Art. 50) plus text — the same markup as every other draft."""
    return (f"<div class='sr-draft'><h2 style='font-size:1.05rem;margin:14px 0 4px'>"
            f"{_html.escape(title)}</h2>"
            "<p style='background:#fff3cd;border:1px solid #d0a900;"
            "padding:6px 10px;font-weight:600'>🤖 "
            f"{_html.escape(narration.banner)}</p>"
            f"<p>{_html.escape(narration.text)}</p></div>")


def draft_to_markdown(draft: ConferenceDraft, lang: str = DEFAULT_LANG) -> str:
    """The editing file: every drafted part with its banner, failures named."""
    lines = [f"# {t('vsc.draft.file_title', lang)}", ""]
    for part in PARTS:
        narration = draft.parts.get(part)
        if narration is None:
            continue
        lines += [f"## {part_title(part, lang)}", "", f"> {narration.banner}", "",
                  narration.text, ""]
    for part, reason in draft.failures.items():
        lines.append(f"<!-- {part_title(part, lang)}: {t('vsc.draft.failed', lang)} {reason} -->")
    return "\n".join(lines).rstrip() + "\n"


def insert_inline(html_doc: str, draft: ConferenceDraft, lang: str = DEFAULT_LANG) -> str:
    """
    Place the parts into the pre-read: the introduction before the first
    input block, each input's paragraph right under its heading. A part
    whose anchor is missing (empty input, no block rendered) is left out
    of the page — it stays in the editing file.
    """
    out = html_doc
    intro = draft.parts.get(PART_INTRO)
    if intro is not None:
        section = draft_html_section(intro, part_title(PART_INTRO, lang))
        marker = out.find("<h1 style='font-size:1.25rem")
        if marker == -1:
            marker = out.find("</body>")
        out = out[:marker] + section + out[marker:] if marker != -1 else out + section
    for part in PARTS[1:]:
        narration = draft.parts.get(part)
        if narration is None:
            continue
        anchor = f"{_html.escape(t(f'vsc.{part}', lang))}</h1>"
        pos = out.find(anchor)
        if pos == -1:
            continue
        pos += len(anchor)
        out = out[:pos] + draft_html_section(narration, part_title(part, lang)) + out[pos:]
    return out
