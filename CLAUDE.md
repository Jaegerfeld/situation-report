# Arbeitsregeln für Claude in diesem Repo

Diese Datei wird in jeder Sitzung geladen. Sie hält die Regeln fest, die nicht aus dem Code
ablesbar sind. Erste Fassung 14.10.2026 nach vier eigenmächtigen Releases (v0.44.0–v0.46.0).

## 1. Merge, Tag und Release entscheidet Robert — nie Claude

- Claude erstellt den Branch von `origin/main`, baut, testet, öffnet den PR und lässt die Checks laufen.
- Dann **hält Claude an** und legt die **neuen Texte zur Freigabe** vor: CHANGELOG-Eintrag,
  mkdocs-Abschnitte, Manual-Absätze, Onepager, Roadmap-Zeilen, PR-Beschreibung
  (Grundsatz 6 „Freigabe zuletzt").
- `gh pr merge`, `git tag`, `git push` von Tags, `gh release` laufen **nur auf Roberts Wort**.
  Ein Hook (`~/.claude/hooks/release_gate.py`) blockiert diese Schritte, bis Robert die Marker-Datei
  `~/.claude/release_ok` angelegt hat — ein Marker, ein Schritt.
- „Grün" heißt „bereit für Roberts Entscheidung", nicht „mergen".
- Das gilt auch für reine Doku-PRs: Deploy Docs veröffentlicht sofort.

## 2. Branches und Git

- Branch immer von `origin/main` nach `git fetch`; vorher `git status -sb` (kein „ahead").
- **Niemals `git stash -u` oder `-a`** — `Quellen/`, `Ideen/`, `feedback/`, `site/`,
  `local test data/` sind gitignored und lokal; ein Stash mit untracked Dateien hat 2026 fast
  alles gelöscht.
- Commit- und PR-Texte als Datei schreiben und per `-F` / `--body-file` übergeben.
- Bei gestapelten PRs beim untersten PR kein `--delete-branch`.

## 3. Tests und Werkzeuge

- Python nur aus der Projekt-venv: `.venv/Scripts/python.exe -m pytest tests --basetemp=.pytest_tmp -p no:cacheprovider`;
  das globale `python` hat weder pytest noch mypy.
- Vor jedem Commit: `python -m ruff check .` und `.venv/Scripts/python.exe -m mypy` (der Pre-Commit-Hook tut es auch).
- Tests lesen nur getrackte Daten unter `tests/testdata/`; GUI-Tests laufen mit isolierten Präferenzen
  (`tests/conftest.py::isolate_user_prefs`).
- Ein einzelner Tk-Fehler (`TclError … tk8.6`) im Gesamtlauf ist ein bekannter Umgebungs-Flake: Test einzeln
  wiederholen, nicht „reparieren".

## 4. Dokumentation je Feature

- Jedes Feature: Archiv `Ideen/Archiv/<Feature>_<Datum>/README.md` (lokal), Manual-Generator
  (`docs/generate_*_manual.py`, fünf Sprachen), mkdocs `docs/modules/<modul>.md` **und** `.de.md`
  (einzeln editieren — `modules/*.md` und `docs/modules/*.md` sind keine Spiegelkopien, nie `copyfile`),
  CHANGELOG, Roadmap, Onepager DE/EN über `docs/generate_feature_onepagers.py`.
- Erzeugte PDFs nach dem Bau per pypdf-Textsuche prüfen.

## 5. UX-Arbeit (Beta-Phase, seit 23.10.2026)

- Die UX-Überarbeitung läuft auf dem Branch `beta/ux-redesign`, bis Robert etwas anderes sagt.
  Inventur und Vorschläge: `docs/beta/`.
- Jede Änderung an etwas, das ein Mensch sieht oder bedient (Fenster, Dialog, Report, Einseiter),
  beginnt mit dem **UX read** aus dem Skill `ux-preflight` (Nutzer und Ziel, primäre Aktion, drei bis
  sechs Gesetze als konkrete Vorgaben, Zustände) **vor dem ersten Edit** und endet mit dem UX check.
- Befunde nur mit Beleg (`file:line` oder gemessener Wert) aus `ux-audit`, abgelegt unter
  `docs/beta/audits/`; Umsetzung über `ux-fix` nur für Befunde, die Robert freigegeben hat.
- Die Laws-of-UX-Skills liegen auf Nutzer-Ebene (`~/.claude/skills/`), sind proprietär und kommen
  **nie ins Repo**; Ergebnisse tragen die Credit-Zeile „Based on Laws of UX by Jon Yablonski,
  lawsofux.com. Published by Pip Decks."
- Ebenfalls auf Nutzer-Ebene liegt der eigene Skill `ux-korpus` (seit 31.10.2026): die Abgleichstabellen
  der vier Kapitelanalysen zu Chlebek, Thesmann und Stapelkamp aus `Quellen/Buchanalysen/`. Er wird bei
  jedem UX read, Audit und Fix **mitgeladen**; er korrigiert einzelne Karten mit Quellen (Miller, Jakob,
  Doherty), liefert Prüfwerte, die das Deck nicht hat (Farbe, Schrift, Meldungsklassen, ISO 9241,
  Kompetenzgrade, Styleguide, Barrierefreiheit, Testmethodik), und die Auflösung der Streitfälle
  (`references/widersprueche.md`). Quellen aus dem Korpus mit Kürzel und Seite zitieren (CH, TH, ST1, ST2);
  Lehrbuchstudien ohne Methodik als „laut …" kennzeichnen.

## 6. Veröffentlichte Texte

- Herkunft aus dem Praxis-Workshop nur als „Praxis-Workshop" oder „Workshop-Analyse" nennen —
  nie Ort und Datum, nie Kundennamen.
- Wahrheitsregel: keine Allaussagen oder Hype-Wörter ohne Beleg, Zahlen exakt, Einschätzungen als
  solche kennzeichnen, Fehler zugeben statt mit neuer Geschichte verteidigen.
- Teams, ARTs, Value Streams — nie Personen (Leitplanke b, im Code per Test erzwungen).
