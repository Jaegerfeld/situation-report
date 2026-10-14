# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Noise-Audit-Unterstützung (Roadmap D7, Entscheidungen Robert 14.10.2026):
#   Dieselbe Frage geht n-mal in leicht variierter Formulierung gegen
#   DENSELBEN Fakten-Index (D3). Weil jede Antwort ihre Pfade zitieren muss,
#   lässt sich die Streuung deterministisch messen — ohne ein zweites Modell,
#   das Ähnlichkeit beurteilt: Zitier-Konsistenz (paarweise Jaccard der
#   zitierten Pfadmengen), Kern-Pfade (von der Mehrheit zitiert), Streu-Pfade
#   (nur eine Antwort), Zahlen-Abweichungen je Pfad, Unbekannt- und
#   Verworfen-Quote. Verworfene Antworten zählen als Streuung, sie werden
#   nicht wiederholt. Varianten sind feste Rahmen je Sprache plus eigene aus
#   einer Datei; kein Modell paraphrasiert. Stabs-Einschätzungen aus einer
#   Datei stehen daneben — ohne Score, das Urteil über Menschen bleibt
#   menschlich. Keine Ampel, keine Deutung: die Zahlen stehen da.
# =============================================================================

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from llm.audit import AUDIT_FILENAME
from llm.guard import (
    CITATION_RE,
    UNKNOWN_ANSWERS,
    CitationGuardError,
    NumbersGuardError,
    extract_numbers,
    statements,
)

from .ask import AskResult, ask_question
from .facts import FactIndex, build_fact_index, sanitize_text
from .snapshot import Snapshot, build_snapshot

DEFAULT_RUNS = 5
NOISE_SUFFIX = ".noise.md"

#: Reformulation frames per language; run 1 is always the unchanged question.
VARIANT_FRAMES = {
    "de": ("Kurz gefasst: {q}", "Für die Value-Stream-Konferenz: {q}",
           "Nur mit Zitaten aus dem Index beantworten: {q}", "Was sagt der Stand zu: {q}",
           "Sachlich und knapp: {q}", "Welche Fakten belegen: {q}"),
    "en": ("In short: {q}", "For the value-stream conference: {q}",
           "Answer only with citations from the index: {q}", "What does the stand say about: {q}",
           "Sober and brief: {q}", "Which facts support: {q}"),
}

_T = {
    "de": {"title": "Noise-Audit", "question": "Frage", "variants": "Varianten", "runs": "Läufe",
           "run": "Lauf", "variant": "Variante", "model": "Modell", "cites": "Zitate", "numbers": "Zahlen",
           "result": "Ergebnis", "passed": "bestanden", "rejected": "verworfen", "unknown": "keine Angabe",
           "consistency": "Zitier-Konsistenz (mittlere paarweise Jaccard-Ähnlichkeit)",
           "core": "Kern — von der Mehrheit zitiert", "scattered": "Streuung — nur eine Antwort zitiert",
           "conflicts": "Zahlen-Abweichungen je Pfad", "rates": "Quoten", "none": "keine",
           "views": "Einschätzungen des Stabs (ohne Bewertung durch das Werkzeug)",
           "answers": "Alle Antworten (KI-Entwürfe)", "stand": "Stand", "facts": "Fakten im Index",
           "digest": "Index-Prüfsumme (SHA-256)", "too_few": "weniger als zwei gültige Antworten — kein Maß",
           "note": "Die Streuung ist ein Befund über das Modell und die Frage, kein Urteil über die Lage. "
                   "Was daraus folgt, entscheidet der Mensch."},
    "en": {"title": "Noise audit", "question": "Question", "variants": "Variants", "runs": "Runs",
           "run": "Run", "variant": "Variant", "model": "Model", "cites": "Citations", "numbers": "Numbers",
           "result": "Result", "passed": "passed", "rejected": "rejected", "unknown": "no information",
           "consistency": "Citation consistency (mean pairwise Jaccard similarity)",
           "core": "Core — cited by the majority", "scattered": "Scatter — cited by one answer only",
           "conflicts": "Number conflicts per path", "rates": "Rates", "none": "none",
           "views": "Staff assessments (not evaluated by the tool)",
           "answers": "All answers (AI drafts)", "stand": "Stand", "facts": "Facts in the index",
           "digest": "Index checksum (SHA-256)", "too_few": "fewer than two valid answers — no measure",
           "note": "The spread is a finding about the model and the question, not a judgement about the "
                   "situation. What follows from it is a human decision."},
}


def _t(lang: str, key: str) -> str:
    return _T.get(lang, _T["en"])[key]


def question_variants(question: str, n: int, lang: str = "de",
                      extra: Sequence[str] = ()) -> list[str]:
    """
    n phrasings: the question itself first, then the user's own variants,
    then the fixed frames; when n exceeds the supply, phrasings repeat (an
    identical question asked twice measures the model's own temperature).
    """
    if n < 1:
        raise ValueError("n must be at least 1.")
    q = sanitize_text(question, 500)
    pool = [q] + [sanitize_text(e, 500) for e in extra if sanitize_text(e, 500)]
    pool += [frame.format(q=q) for frame in VARIANT_FRAMES.get(lang, VARIANT_FRAMES["en"])]
    return [pool[i % len(pool)] for i in range(n)]


def read_variants(path: Path) -> list[str]:
    """One variant per non-empty line."""
    return [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def read_views(path: Path) -> list[str]:
    """Staff assessments: one per paragraph (blank line separated)."""
    text = Path(path).read_text(encoding="utf-8")
    return [sanitize_text(p.replace("\n", " "), 1000) for p in text.split("\n\n") if p.strip()]


@dataclass
class Run:
    """One phrasing, one answer (or its rejection)."""
    variant: str
    answer: str = ""
    banner: str = ""
    model: str = ""
    rejected: str = ""                    # guard message when discarded
    cited: set[str] = field(default_factory=set)
    numbers_by_path: dict[str, set[str]] = field(default_factory=dict)
    statements_by_path: dict[str, list[str]] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.rejected

    @property
    def unknown(self) -> bool:
        return self.valid and self.answer.strip() in UNKNOWN_ANSWERS.values()


def analyse_answer(run: Run) -> None:
    """Fill cited paths, numbers and statements per path from the answer."""
    for stmt in statements(run.answer):
        paths = CITATION_RE.findall(stmt)
        nums = extract_numbers(CITATION_RE.sub("", stmt))
        for p in paths:
            run.cited.add(p)
            run.numbers_by_path.setdefault(p, set()).update(nums)
            run.statements_by_path.setdefault(p, []).append(stmt)


@dataclass
class NoiseReport:
    question: str
    runs: list[Run]
    index: FactIndex
    views: list[str] = field(default_factory=list)

    @property
    def valid_runs(self) -> list[Run]:
        return [r for r in self.runs if r.valid]

    @property
    def consistency(self) -> float | None:
        """Mean pairwise Jaccard of cited-path sets over valid runs, 0–100."""
        sets = [r.cited for r in self.valid_runs]
        if len(sets) < 2:
            return None
        sims = []
        for a, b in combinations(sets, 2):
            if not a and not b:
                sims.append(1.0)
            else:
                sims.append(len(a & b) / len(a | b))
        return round(100 * sum(sims) / len(sims), 1)

    def _counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.valid_runs:
            for p in r.cited:
                counts[p] = counts.get(p, 0) + 1
        return counts

    @property
    def core(self) -> list[str]:
        valid = len(self.valid_runs)
        if valid < 2:
            return []
        need = math.ceil(valid / 2)
        return sorted(p for p, c in self._counts().items() if c >= need)

    @property
    def scattered(self) -> dict[str, list[tuple[int, str]]]:
        """path -> [(run number, statement)] for paths only one valid answer cites."""
        if len(self.valid_runs) < 2:
            return {}
        singles = {p for p, c in self._counts().items() if c == 1}
        out: dict[str, list[tuple[int, str]]] = {}
        for i, r in enumerate(self.runs, start=1):
            for p in singles & r.cited:
                out.setdefault(p, []).extend((i, s) for s in r.statements_by_path.get(p, []))
        return dict(sorted(out.items()))

    @property
    def number_conflicts(self) -> dict[str, list[set[str]]]:
        """path -> distinct non-empty number sets when valid answers disagree."""
        per_path: dict[str, list[set[str]]] = {}
        for r in self.valid_runs:
            for p, nums in r.numbers_by_path.items():
                if nums:
                    per_path.setdefault(p, []).append(nums)
        return {p: [set(s) for s in {frozenset(x) for x in sets}]
                for p, sets in sorted(per_path.items()) if len({frozenset(x) for x in sets}) > 1}

    @property
    def unknown_rate(self) -> float:
        return round(100 * sum(1 for r in self.runs if r.unknown) / len(self.runs), 1) if self.runs else 0.0

    @property
    def rejected_rate(self) -> float:
        return round(100 * sum(1 for r in self.runs if not r.valid) / len(self.runs), 1) if self.runs else 0.0


def run_noise_audit(
    config: Any,
    question: str,
    n: int = DEFAULT_RUNS,
    provider_id: str = "ollama",
    lang: str = "de",
    snapshot: Snapshot | None = None,
    prev_snapshot: Snapshot | None = None,
    reference: date | None = None,
    target_ct: int = 90,
    scope: str = "all",
    extra_variants: Sequence[str] = (),
    views: Iterable[str] = (),
    audit_path: Path | None = None,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    log: Callable[[str], None] = print,
) -> NoiseReport:
    """
    Ask the same question n times (varied phrasings) against ONE stand and
    measure the spread of the cited facts.

    Raises:
        ValueError:   n < 1, empty question, or the export provider (it writes
                      bundles instead of answering - nothing to compare).
        RuntimeError: Provider failure (not noise - aborts).
    """
    if provider_id == "export":
        raise ValueError("A noise audit needs a model that answers; 'export' writes prompt bundles.")
    quiet: Callable[[str], None] = lambda m: None  # noqa: E731
    snap = snapshot or build_snapshot(config, as_of=reference, target_ct=target_ct, log=quiet)
    variants = question_variants(question, n, lang, extra_variants)
    runs: list[Run] = []
    index: FactIndex | None = None
    for i, variant in enumerate(variants, start=1):
        log(f"Noise audit run {i}/{n}: {variant[:70]}")
        run = Run(variant=variant)
        try:
            res: AskResult = ask_question(config, variant, provider_id=provider_id, lang=lang,
                                          snapshot=snap, prev_snapshot=prev_snapshot, scope=scope,
                                          audit_path=audit_path, llm_model=llm_model,
                                          llm_base_url=llm_base_url, log=quiet)
            run.answer, run.banner, run.model = res.answer, res.banner, res.result.model
            index = index or res.index
            analyse_answer(run)
        except (CitationGuardError, NumbersGuardError) as exc:
            run.rejected = str(exc).split(":", 1)[0] + ": " + "; ".join(getattr(exc, "violations", [])[:3])
        runs.append(run)
    if index is None:
        index = build_fact_index(snap, prev=prev_snapshot, scope=scope, lang=lang)
    return NoiseReport(question=sanitize_text(question, 500), runs=runs, index=index, views=list(views))


def noise_to_markdown(rep: NoiseReport, lang: str = "de") -> str:
    """The .noise.md protocol."""
    k = "de" if lang == "de" else "en"
    lines = [f"# {_t(k, 'title')} — {rep.index.name} ({rep.index.as_of})", "",
             f"**{_t(k, 'question')}:** {rep.question}", "", _t(k, "note"), "",
             f"## {_t(k, 'runs')} ({len(rep.runs)})", "",
             f"| {_t(k, 'run')} | {_t(k, 'variant')} | {_t(k, 'model')} | {_t(k, 'cites')} | "
             f"{_t(k, 'numbers')} | {_t(k, 'result')} |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rep.runs, start=1):
        nums = sorted({n for s in r.numbers_by_path.values() for n in s})
        result = (_t(k, "rejected") if not r.valid else _t(k, "unknown") if r.unknown else _t(k, "passed"))
        lines.append(f"| {i} | {r.variant} | {r.model or '-'} | {len(r.cited)} | "
                     f"{', '.join(nums) or '-'} | {result} |")
    cons = rep.consistency
    lines += ["", f"## {_t(k, 'consistency')}", "",
              f"**{cons} / 100**" if cons is not None else f"_{_t(k, 'too_few')}_", "",
              f"## {_t(k, 'core')}", ""]
    lines += [f"- [{p}]" for p in rep.core] or [f"_{_t(k, 'none')}_"]
    lines += ["", f"## {_t(k, 'scattered')}", ""]
    scattered = rep.scattered
    if scattered:
        for p, items in scattered.items():
            lines.append(f"- [{p}]")
            lines += [f"  - {_t(k, 'run')} {i}: {s}" for i, s in items]
    else:
        lines.append(f"_{_t(k, 'none')}_")
    lines += ["", f"## {_t(k, 'conflicts')}", ""]
    conflicts = rep.number_conflicts
    lines += [f"- [{p}]: " + " | ".join("{" + ", ".join(sorted(s)) + "}" for s in sets)
              for p, sets in conflicts.items()] or [f"_{_t(k, 'none')}_"]
    lines += ["", f"## {_t(k, 'rates')}", "",
              f"- {_t(k, 'unknown')}: {rep.unknown_rate} %", f"- {_t(k, 'rejected')}: {rep.rejected_rate} %"]
    if rep.views:
        lines += ["", f"## {_t(k, 'views')}", ""]
        lines += [f"{i}. {v}" for i, v in enumerate(rep.views, start=1)]
    lines += ["", f"## {_t(k, 'answers')}", ""]
    for i, r in enumerate(rep.runs, start=1):
        lines += [f"### {_t(k, 'run')} {i} — {r.variant}", ""]
        if r.valid:
            lines += [f"> {r.banner}", "", r.answer.strip(), ""]
        else:
            lines += [f"_{_t(k, 'rejected')}: {r.rejected}_", ""]
    lines += ["---", f"{_t(k, 'stand')}: S1 = {rep.index.as_of}"
              + (f", S0 = {rep.index.prev_as_of}" if rep.index.prev_as_of else "")
              + f" · {_t(k, 'facts')}: {len(rep.index)} · {_t(k, 'digest')}: {rep.index.digest()}", ""]
    return "\n".join(lines)


def run_noise(config: Any, question: str, output: Path, n: int = DEFAULT_RUNS, **kw: Any) -> NoiseReport:
    """Run the audit and write the protocol next to ``output`` (audit beside it)."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lang = kw.get("lang", "de")
    rep = run_noise_audit(config, question, n=n, audit_path=output.parent / AUDIT_FILENAME, **kw)
    output.write_text(noise_to_markdown(rep, lang), encoding="utf-8")
    log = kw.get("log", print)
    log(f"Noise audit written: {output} (consistency {rep.consistency})")
    return rep
