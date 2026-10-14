# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Der Rückweg des Prompt-Exports („llm check", Auftrag Robert 14.10.2026).
#   Eine Antwort, die ein fremdes Modell auf einem anderen Rechner zu einem
#   exportierten Prompt-Bündel erzeugt hat, wird gegen den Contract aus dem
#   Bündel geprüft, bevor sie in einen Report darf: Zahlen-Wächter immer,
#   Fragen-Wächter für Red-Team-Antworten (D5). Besteht die Antwort, wird sie
#   mit dem Banner „extern erzeugt" als Entwurfsdatei geschrieben und im
#   Betreiber-Nachweis festgehalten — mit demselben Eingabe-Hash wie der
#   Export-Eintrag, so sind Hin- und Rückweg verknüpft. Fällt sie durch, wird
#   nichts geschrieben (Rückgabewert 2), der Nachweis trägt guard_passed=false.
#   Dasselbe Verhalten wie bei einem direkten Modellaufruf, der verworfen wird.
#   Das Werkzeug hat das Modell nie gesehen: Betriebsklasse external_answer,
#   Modellname kommt vom Menschen.
# =============================================================================

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .audit import AUDIT_FILENAME, append_audit
from .base import DEPLOYMENT_EXTERNAL_ANSWER, LlmResult
from .guard import ai_banner_text, question_violations, verify_numbers

#: Provider id written to the audit trail for answers the tool never requested.
PROVIDER_EXTERNAL = "external"
#: What the operator writes when the model is not known.
MODEL_UNKNOWN = "unbekannt"
#: Exported bundles are named prompt_<purpose>_<stamp>.md (see llm.export).
BUNDLE_GLOB = "prompt_*.md"
#: Audit purposes whose answers must consist of questions only (D5).
QUESTION_PURPOSES = ("d5_red_team",)
#: Suffix of the file llm check writes next to the answer.
CHECKED_SUFFIX = ".checked.md"

_HEAD_RE = re.compile(r"^# Prompt[- ][Ee]xport — (?P<purpose>.+?) — (?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2})",
                      re.M)
_LANG_RE = re.compile(r"(?:Sprache des Entwurfs|Draft language): (\w+)\.")
_SHA_RE = re.compile(r"SHA-256\): ([0-9a-f]{64})")
_SYSTEM_HEADINGS = ("## Systemprompt", "## System prompt")
_INPUT_HEADINGS = ("## Eingabe (Contract)", "## Input (contract)")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Bundle:
    """A parsed prompt-export bundle (llm.export.build_bundle)."""
    purpose: str
    lang: str
    system: str
    contract: str
    checksum: str = ""          # from the bundle head; "" for bundles before 0.45.0
    stamp: str = ""
    path: Path | None = None

    @property
    def checksum_ok(self) -> bool | None:
        """True/False when the head carries a checksum, None for older bundles."""
        if not self.checksum:
            return None
        return sha256_text(self.contract) == self.checksum


def _find_heading(text: str, headings: tuple[str, ...]) -> int:
    for heading in headings:
        idx = text.find(heading)
        if idx >= 0:
            return idx
    return -1


def _fenced_after(text: str, start: int, fence: str, last: bool) -> str:
    """The content of the fenced block that opens after ``start``."""
    opening = text.find(f"```{fence}\n", start)
    if opening < 0:
        raise ValueError(f"Bundle has no ```{fence} block after position {start}.")
    body_start = opening + len(fence) + 4
    closing = text.rfind("\n```", body_start) if last else text.find("\n```", body_start)
    if closing < 0:
        raise ValueError(f"Bundle's ```{fence} block is not closed.")
    return text[body_start:closing]


def parse_bundle(text: str, path: Path | None = None) -> Bundle:
    """
    Read purpose, language, system prompt and the verbatim contract out of an
    exported bundle. The contract is taken from the LAST closing fence, so a
    contract that itself contains fences survives.

    Raises:
        ValueError: Not a prompt-export bundle (head or sections missing).
    """
    head = _HEAD_RE.search(text)
    if head is None:
        raise ValueError("Not a prompt-export bundle: the first line should read "
                         "'# Prompt-Export — <purpose> — <stamp>'.")
    sys_at = _find_heading(text, _SYSTEM_HEADINGS)
    in_at = _find_heading(text, _INPUT_HEADINGS)
    if sys_at < 0 or in_at < 0:
        raise ValueError("Bundle lacks the system-prompt or the input section.")
    lang = _LANG_RE.search(text)
    sha = _SHA_RE.search(text)
    return Bundle(purpose=head.group("purpose").strip(), lang=lang.group(1) if lang else "de",
                  system=_fenced_after(text, sys_at, "text", last=False),
                  contract=_fenced_after(text, in_at, "markdown", last=True),
                  checksum=sha.group(1) if sha else "", stamp=head.group("stamp"), path=path)


def load_bundle(path: Path) -> Bundle:
    return parse_bundle(Path(path).read_text(encoding="utf-8"), Path(path))


def find_bundle(folder: Path, purpose: str | None = None) -> Path | None:
    """The newest exported bundle in ``folder`` (optionally of one purpose)."""
    candidates = [p for p in Path(folder).glob(BUNDLE_GLOB) if p.is_file()]
    if purpose:
        candidates = [p for p in candidates if p.name.startswith(f"prompt_{purpose}_")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


def read_clipboard() -> str:
    """The clipboard text via tkinter; "" when there is none or no display."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            text = root.clipboard_get()
        finally:
            root.destroy()
        return str(text)
    except Exception:  # noqa: BLE001 - "nothing on the clipboard" is the only outcome
        return ""


@dataclass
class CheckReport:
    """Outcome of one check; ``passed`` decides whether anything is written."""
    bundle: Bundle
    answer: str
    model: str = MODEL_UNKNOWN
    number_violations: list[str] = field(default_factory=list)
    question_violations: list[str] = field(default_factory=list)
    written: Path | None = None

    @property
    def passed(self) -> bool:
        return not self.number_violations and not self.question_violations

    @property
    def violations(self) -> list[str]:
        return ([f"Zahl nicht im Contract: {n}" for n in self.number_violations]
                + [f"Keine Frage: {line}" for line in self.question_violations])

    def result(self) -> LlmResult:
        """The answer dressed as an LlmResult for banner and audit."""
        return LlmResult(text=self.answer, provider_id=PROVIDER_EXTERNAL, model=self.model,
                         deployment_class=DEPLOYMENT_EXTERNAL_ANSWER, duration_s=0.0, endpoint="")


def check_answer(answer: str, bundle: Bundle, model: str = MODEL_UNKNOWN) -> CheckReport:
    """
    Run the guards an in-tool draft would have faced: numbers against the
    contract, questions-only for red-team purposes. Nothing is written here.
    """
    report = CheckReport(bundle=bundle, answer=answer, model=model or MODEL_UNKNOWN)
    if not answer.strip():
        report.number_violations = ["<leere Antwort>"]
        return report
    report.number_violations = verify_numbers(answer, bundle.contract)
    if bundle.purpose in QUESTION_PURPOSES:
        report.question_violations = question_violations(answer)
    return report


def checked_text(report: CheckReport, lang: str | None = None) -> str:
    """Banner plus the answer — the draft file a human then edits."""
    banner = ai_banner_text(report.result(), lang or report.bundle.lang)
    return f"> {banner}\n\n{report.answer.strip()}\n"


def record_check(report: CheckReport, audit_path: Path) -> None:
    """One operator-evidence line; input hash = the contract, as in the export record."""
    append_audit(Path(audit_path), report.result(), report.bundle.contract,
                 report.bundle.purpose, guard_passed=report.passed)


def run_check(
    answer: str,
    bundle_path: Path,
    out_path: Path | None = None,
    model: str = MODEL_UNKNOWN,
    lang: str | None = None,
    audit_path: Path | None = None,
    log: Callable[[str], None] = print,
) -> CheckReport:
    """
    The whole return path: parse the bundle, run the guards, write the
    labelled draft when they pass, record the check either way.

    Args:
        answer:      The external model's answer (file content or clipboard).
        bundle_path: The exported prompt bundle the answer belongs to.
        out_path:    Where the labelled draft goes when the guards pass
                     (default: <bundle>.checked.md next to the bundle).
        model:       Model name as the operator knows it (the tool cannot know).
        lang:        Banner language (default: the bundle's draft language).
        audit_path:  Operator evidence (default: llm_audit.jsonl next to the bundle).

    Raises:
        OSError, ValueError: Unreadable or malformed bundle.
    """
    bundle = load_bundle(Path(bundle_path))
    report = check_answer(answer, bundle, model=model)
    audit = Path(audit_path) if audit_path else Path(bundle_path).parent / AUDIT_FILENAME
    if bundle.checksum_ok is False:
        log("WARNING: the bundle's contract does not match its checksum - the bundle "
            "was edited after export; the check runs against the edited contract.")
    record_check(report, audit)
    if not report.passed:
        log(f"REJECTED ({bundle.purpose}): {len(report.violations)} violation(s)")
        for line in report.violations:
            log(f"  - {line}")
        log("Nothing written. Re-run the model, fix the prompt, or use the deterministic text.")
        return report
    target = Path(out_path) if out_path else Path(bundle_path).with_suffix(CHECKED_SUFFIX)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(checked_text(report, lang), encoding="utf-8")
    report.written = target
    log(f"PASSED ({bundle.purpose}): draft written to {target}")
    log(f"audit: {audit}")
    return report
