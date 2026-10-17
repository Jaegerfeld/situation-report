# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.10.2026
# Geändert:       17.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Freigabe eines KI-Entwurfs (R3, Leitplanke a „bis zur Freigabe"): Eine
#   Markdown-Entwurfsdatei trägt seit v0.53.0 einen maschinenlesbaren Marker
#   (sr-ai-draft/1) und den sichtbaren Banner. `llm approve DATEI --by TEAM`
#   setzt den Marker auf geprüft (Team, Datum, redigiert ja/nein), ersetzt den
#   Banner durch die Freigabe-Zeile (Art. 50 Abs. 4 KI-VO: redaktionelle
#   Kontrolle mit benannter Verantwortung) und schreibt die Freigabe in den
#   Betreiber-Nachweis. Ob redigiert wurde, zeigt der Hash: stimmt der Text
#   unter dem Banner noch mit der Ausgabe des Modells überein, war niemand
#   dran — dann warnt das Werkzeug und gibt nur mit --as-is frei. Teams, nie
#   Personen (Leitplanke b) — das Werkzeug kann es nicht prüfen, die Doku
#   sagt es.
# =============================================================================

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .audit import AUDIT_FILENAME, append_approval
from .guard import MARKER_RE, marker_comment, read_markers

#: Return code when the draft was not edited and --as-is is missing.
RC_UNEDITED = 3

APPROVAL_LINE = {
    "de": "Freigegeben durch {team} am {day} — KI-Entwurf, redaktionell geprüft (Art. 50 Abs. 4 KI-VO).",
    "en": "Approved by {team} on {day} — AI draft, editorially reviewed (Art. 50(4) AI Act).",
    "ro": "Aprobat de {team} la {day} — schiță AI, verificată editorial (art. 50 alin. 4 Regulamentul AI).",
    "pt": "Aprovado por {team} em {day} — rascunho de IA, revisto editorialmente (art. 50.º n.º 4 Regulamento IA).",
    "fr": "Approuvé par {team} le {day} — brouillon IA, relu éditorialement (art. 50 par. 4 règlement IA).",
}


@dataclass
class ApprovalReport:
    path: Path
    markers: int = 0
    edited: bool | None = None            # None: several drafts, not decidable per file
    reviewed_by: str = ""
    day: str = ""
    already_reviewed: bool = False
    text: str = ""
    messages: list[str] = field(default_factory=list)


def _draft_region(text: str, banner_pos: int) -> str:
    """The text under a banner up to the next '---' line, headings removed, stripped."""
    rest = text[banner_pos:].split("\n", 1)[1] if "\n" in text[banner_pos:] else ""
    lines = []
    for line in rest.split("\n"):
        if line.strip() == "---":
            break
        if line.startswith("## "):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def inspect(text: str) -> tuple[list[dict[str, object]], bool | None]:
    """Markers of a file and whether its (single) draft was edited (None: not decidable)."""
    markers = read_markers(text)
    if len(markers) != 1:
        return markers, None
    m = MARKER_RE.search(text)
    assert m is not None
    banner_pos = text.find("\n> ", m.end())
    if banner_pos == -1:
        return markers, None
    region = _draft_region(text, banner_pos + 1)
    digest = hashlib.sha256(region.encode("utf-8")).hexdigest()
    return markers, digest != markers[0].get("output_sha256")


def approve_text(text: str, team: str, day: date | None = None,
                 note: str = "") -> tuple[str, ApprovalReport]:
    """Rewrite markers and banners of a draft text; nothing is written here."""
    rep = ApprovalReport(path=Path("-"))
    markers, edited = inspect(text)
    rep.markers, rep.edited = len(markers), edited
    if not markers:
        raise ValueError("No AI-draft marker (sr-ai-draft) in the file - nothing to approve.")
    if any(m.get("reviewed") for m in markers):
        rep.already_reviewed = True
        raise ValueError("The file is already approved (marker says reviewed: true).")
    team = re.sub(r"\s+", " ", team).strip()
    if not team:
        raise ValueError("Give the approving team with --by.")
    rep.reviewed_by, rep.day = team, (day or date.today()).isoformat()
    out = text
    for m in markers:
        old = marker_comment(m)
        new_m = dict(m)
        new_m.update({"reviewed": True, "reviewed_by": team, "reviewed_on": rep.day,
                      "edited": edited})
        if note:
            new_m["note"] = re.sub(r"\s+", " ", note).strip()[:200]
        if old not in out:                        # key order may differ - match by regex
            match = MARKER_RE.search(out)
            assert match is not None
            old = match.group(0)
        pos = out.find(old)
        banner_at = out.find("\n> ", pos + len(old))
        lang = str(m.get("lang", "de"))
        line = APPROVAL_LINE.get(lang, APPROVAL_LINE["en"]).format(team=team, day=rep.day)
        if banner_at != -1:
            end = out.find("\n", banner_at + 1)
            end = len(out) if end == -1 else end
            out = out[:banner_at + 1] + f"> {line}" + out[end:]
        out = out.replace(old, marker_comment(new_m), 1)
    rep.text = out
    return out, rep


def approve_file(path: Path, team: str, note: str = "", as_is: bool = False,
                 audit_path: Path | None = None, day: date | None = None) -> ApprovalReport:
    """
    Approve one Markdown draft in place.

    Raises:
        ValueError: no marker, already approved, empty team.
        OSError:    read/write problems.
    Returns an ApprovalReport; when the single draft was NOT edited and
    ``as_is`` is False, nothing is written and the report says so
    (``messages``), so the CLI can return RC_UNEDITED.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    markers, edited = inspect(text)
    rep = ApprovalReport(path=path, markers=len(markers), edited=edited)
    if markers and edited is False and not as_is:
        rep.messages.append("The draft is unchanged since the model wrote it - approve without "
                            "editing? Re-run with --as-is to confirm.")
        return rep
    new_text, rep2 = approve_text(text, team, day=day, note=note)
    rep2.path, rep2.edited = path, edited
    path.write_text(new_text, encoding="utf-8")
    audit = Path(audit_path) if audit_path else path.parent / AUDIT_FILENAME
    append_approval(audit, path.name, rep2.reviewed_by,
                    str(markers[0].get("output_sha256", "")), new_text, edited,
                    purpose=str(markers[0].get("purpose", "")))
    rep2.messages.append(f"approved: {path.name} by {rep2.reviewed_by} on {rep2.day} "
                         f"({'edited' if edited else 'as is' if edited is False else 'several drafts'})")
    rep2.messages.append(f"audit: {audit}")
    return rep2


def marker_summary(path: Path) -> str:
    """One line per marker of a file (for the CLI's --show)."""
    markers = read_markers(Path(path).read_text(encoding="utf-8"))
    if not markers:
        return "no AI-draft marker"
    return "\n".join(json.dumps(m, ensure_ascii=False, sort_keys=True) for m in markers)
