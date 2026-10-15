# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.10.2026
# Geändert:       15.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Datenminimierung ab Quelle (Rechts-Kandidat R1, nach Rohrlich „KI und
#   Recht", B.9): Ein Jira-Export wird auf die Felder reduziert, die
#   transform_data liest (Allowlist), und der Changelog bleibt VOLLSTÄNDIG
#   erhalten — jede Historie, jedes Item —, nur die Personen darin werden
#   anonymisiert: der Autor je Historie wird ein fester Platzhalter (kein
#   Pseudonym je Person: das bliebe personenbezogen), Items zu Personen-
#   feldern behalten den Feldnamen und verlieren die Werte, Items zu
#   Freitextfeldern verlieren ihre Textwerte. Der REST-Abruf minimiert immer;
#   der manuelle Export über den Unterbefehl `minimise`. Ein Report zählt,
#   was entfernt wurde; die Pipeline dahinter bleibt unverändert (Contract-
#   Test: roh und minimiert liefern dieselben Kennzahlen). Entscheidungen
#   Robert 15.10.2026: Allowlist, Changelog anonymisieren statt kürzen, kein
#   Opt-out beim Abruf, neue Datei statt Überschreiben.
# =============================================================================

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The one value every person reference becomes (a constant, not a pseudonym).
ANONYMISED = "anonymised"
#: Field names that identify people (issue fields and changelog item fields).
PERSON_FIELDS = frozenset({"assignee", "reporter", "creator", "author", "watches", "watchers",
                           "votes", "voters", "worklog", "comment", "lastviewed"})
#: Changelog item fields whose values are free text that may name people.
TEXT_FIELDS = frozenset({"description", "summary", "comment", "environment"})
#: Issue fields transform_data reads — and the sub-keys kept of each (None = whole value).
ALLOWED_FIELDS: dict[str, tuple[str, ...] | None] = {
    "project": ("key", "name"), "issuetype": ("name",), "status": ("name",),
    "created": None, "resolution": ("name",), "components": ("name",),
}
#: Issue-level keys kept besides fields and changelog.
_ISSUE_KEYS = ("id", "key")
#: Changelog item keys kept (values of person/text items are masked or dropped).
_ITEM_KEYS = ("field", "fieldtype", "fieldId", "from", "fromString", "to", "toString")
_ITEM_VALUE_KEYS = ("from", "fromString", "to", "toString")


@dataclass
class MinimiseReport:
    """What the minimisation removed or masked, as counts."""
    issues: int = 0
    dropped_fields: Counter = field(default_factory=Counter)      # field -> issues
    person_fields: Counter = field(default_factory=Counter)       # field -> issues
    authors: int = 0                                              # histories anonymised
    person_items: Counter = field(default_factory=Counter)        # item field -> items
    text_items: Counter = field(default_factory=Counter)          # item field -> items
    kept_extra: tuple[str, ...] = ()

    @property
    def persons_total(self) -> int:
        return sum(self.person_fields.values()) + self.authors + sum(self.person_items.values())

    @property
    def changed(self) -> bool:
        return bool(self.dropped_fields or self.authors or self.person_items or self.text_items)

    def lines(self) -> list[str]:
        """Human-readable summary (CLI and GUI log)."""
        out = [f"Data minimisation: {self.issues} issues"]
        if self.person_fields:
            out.append("  person fields removed: " + ", ".join(
                f"{k} ({n} issues)" for k, n in sorted(self.person_fields.items())))
        if self.authors:
            out.append(f"  changelog authors anonymised: {self.authors} entries")
        if self.person_items:
            out.append("  changelog person items masked: " + ", ".join(
                f"{k} ({n})" for k, n in sorted(self.person_items.items())))
        if self.text_items:
            out.append("  changelog text items emptied: " + ", ".join(
                f"{k} ({n})" for k, n in sorted(self.text_items.items())))
        other = {k: n for k, n in self.dropped_fields.items() if k not in self.person_fields}
        if other:
            out.append(f"  other fields dropped: {len(other)} ({', '.join(sorted(other))})")
        if self.kept_extra:
            out.append(f"  kept on request: {', '.join(self.kept_extra)}")
        if not self.changed:
            out.append("  nothing to remove - the export was already minimal")
        return out


def check_keep(keep: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Validate extra fields to keep: no person field may be kept."""
    cleaned = tuple(dict.fromkeys(k.strip() for k in keep if k.strip()))
    bad = [k for k in cleaned if k.lower() in PERSON_FIELDS]
    if bad:
        raise ValueError(f"Person fields cannot be kept: {', '.join(bad)} "
                         f"(data minimisation at the source, R1).")
    return cleaned


def _reduce_value(value: Any, keys: tuple[str, ...] | None) -> Any:
    if keys is None or value is None:
        return value
    if isinstance(value, list):
        return [_reduce_value(v, keys) for v in value]
    if isinstance(value, dict):
        return {k: value[k] for k in keys if k in value}
    return value


def _minimise_fields(fields: dict[str, Any], keep: tuple[str, ...], rep: MinimiseReport) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, value in fields.items():
        if name in ALLOWED_FIELDS:
            out[name] = _reduce_value(value, ALLOWED_FIELDS[name])
        elif name in keep:
            out[name] = value
        else:
            rep.dropped_fields[name] += 1
            if name.lower() in PERSON_FIELDS:
                rep.person_fields[name] += 1
    return out


def _minimise_history(history: dict[str, Any], rep: MinimiseReport) -> dict[str, Any]:
    out: dict[str, Any] = {k: history[k] for k in ("id", "created") if k in history}
    author = history.get("author")
    if isinstance(author, dict) and author.get("displayName") != ANONYMISED or (
            author is not None and not isinstance(author, dict)):
        rep.authors += 1
    if "author" in history:
        out["author"] = {"displayName": ANONYMISED}
    items = []
    for item in history.get("items") or []:
        if not isinstance(item, dict):
            continue
        new = {k: item[k] for k in _ITEM_KEYS if k in item}
        fname = str(item.get("field", "")).lower()
        if fname in PERSON_FIELDS:
            if any(item.get(k) not in (None, ANONYMISED) for k in _ITEM_VALUE_KEYS):
                rep.person_items[item.get("field", "?")] += 1
            for k in _ITEM_VALUE_KEYS:
                if k in new:
                    new[k] = ANONYMISED
        elif fname in TEXT_FIELDS:
            if any(item.get(k) for k in _ITEM_VALUE_KEYS):
                rep.text_items[item.get("field", "?")] += 1
            for k in _ITEM_VALUE_KEYS:
                new.pop(k, None)
        items.append(new)
    out["items"] = items
    return out


def minimise_export(data: Any, keep: tuple[str, ...] | list[str] = ()) -> tuple[Any, MinimiseReport]:
    """
    Reduce a parsed Jira export to what transform_data reads; anonymise the changelog.

    Accepts the export envelope ({..., "issues": [...]}) or a bare issue list and
    returns the same shape. Idempotent: a minimised export passes through
    unchanged with an empty report.

    Raises:
        ValueError: ``keep`` names a person field, or the data is no export.
    """
    kept = check_keep(keep)
    if isinstance(data, list):
        issues, envelope = data, None
    elif isinstance(data, dict) and isinstance(data.get("issues"), list):
        issues, envelope = data["issues"], data
    else:
        raise ValueError("Not a Jira export: expected an object with an 'issues' list "
                         "(or a bare issue list).")
    rep = MinimiseReport(issues=len(issues), kept_extra=kept)
    new_issues = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        new: dict[str, Any] = {k: issue[k] for k in _ISSUE_KEYS if k in issue}
        new["fields"] = _minimise_fields(issue.get("fields") or {}, kept, rep)
        changelog = issue.get("changelog")
        if isinstance(changelog, dict):
            new["changelog"] = {
                **{k: changelog[k] for k in ("startAt", "maxResults", "total") if k in changelog},
                "histories": [_minimise_history(h, rep) for h in changelog.get("histories") or []
                              if isinstance(h, dict)],
            }
        new_issues.append(new)
    if envelope is None:
        return new_issues, rep
    out = {k: v for k, v in envelope.items() if k != "issues"}
    out["issues"] = new_issues
    return out, rep


def person_field_hits(data: Any) -> Counter:
    """
    Count person data still present (for the export check): issue fields,
    un-anonymised changelog authors and unmasked person items.
    """
    hits: Counter = Counter()
    issues = data if isinstance(data, list) else (data.get("issues") if isinstance(data, dict) else None)
    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        for name, value in (issue.get("fields") or {}).items():
            if name.lower() in PERSON_FIELDS and value not in (None, "", [], {}):
                hits[f"fields.{name}"] += 1
        for history in (issue.get("changelog") or {}).get("histories") or []:
            if not isinstance(history, dict):
                continue
            author = history.get("author")
            if author and not (isinstance(author, dict) and author.get("displayName") == ANONYMISED
                               and len(author) == 1):
                hits["changelog.author"] += 1
            for item in history.get("items") or []:
                if isinstance(item, dict) and str(item.get("field", "")).lower() in PERSON_FIELDS \
                        and any(item.get(k) not in (None, ANONYMISED) for k in _ITEM_VALUE_KEYS):
                    hits[f"changelog.items.{item.get('field')}"] += 1
    return hits


def default_output(source: Path) -> Path:
    """<name>_min.json next to the source — the original stays untouched."""
    return source.with_name(f"{source.stem}_min{source.suffix or '.json'}")


def minimise_file(source: Path, output: Path | None = None,
                  keep: tuple[str, ...] | list[str] = ()) -> tuple[Path, MinimiseReport]:
    """Read, minimise and write ``source``; returns (written path, report)."""
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    data, rep = minimise_export(data, keep)
    target = Path(output) if output else default_output(Path(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target, rep
