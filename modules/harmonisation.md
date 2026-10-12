# harmonisation

Harmonisierungs-Score je End-to-End-Prozess: ein strukturiertes Assessment in drei
Dimensionen (**Business Value · Transparenz · IT und Betrieb**), versioniert abgelegt,
je Dimension ein Score mit Konfidenz, gerendert als **Entscheider-Matrix** fürs Board.
Herkunft: Roadmap, Priorität P3.

!!! info "Befund, kein Urteil"
    Das Modul empfiehlt nichts — weder *was* harmonisiert wird noch *in welcher Tiefe*.
    Es rechnet den Befund und hält fest, was das Board entschieden hat. Die Urteilszeile
    bleibt beim Menschen, dieselbe Nicht-Funktion wie der fehlende Empfehlungs-Button in
    der KI-Schicht.

## Start

```bash
python -m harmonisation
```

Öffnet die Oberfläche: Arbeitsbereich wählen oder **Beispiel anlegen**, Prozesse pflegen,
Bewertung erfassen, Entscheidung eintragen, Matrix erzeugen.

```bash
python -m harmonisation <ordner> --lang de --browser
python -m harmonisation <ordner> --example      # Beispiel-Arbeitsbereich anlegen und rendern
```

| Option | Bedeutung |
|---|---|
| `--output FILE` | HTML-Datei (Standard: `<ordner>/matrix.<lang>.html`) |
| `--lang de\|en\|ro\|pt\|fr` | Sprache der Matrix (Standard: de) |
| `--example` | schreibt den Beispiel-Arbeitsbereich in den Ordner |
| `--browser` | öffnet die Matrix im Browser |

## Arbeitsbereich

Ein Ordner mit vier Dingen, alles JSON mit `schema_version`:

```
<ordner>/
├── catalogue.json      Fragenkatalog: Dimensionen → Fragen (Text je Sprache)
├── processes.json      End-to-End-Prozesse (id, name, owner, brands)
├── decisions.json      Entscheidung des Boards je Prozess (optional)
└── assessments/        eine Datei je Bewertung: Prozess, Befragte(r), Datum, Antworten
```

**Der Katalog ist Daten, nicht Code.** Der mitgelieferte Beispielkatalog mit 3 × 8 Fragen
ist eine Illustration der Struktur; die eigenen Fragen kommen in dieselbe Datei.
Jede Frage ist so formuliert, dass hohe Zustimmung *für* eine Harmonisierung spricht —
nur so sind die Werte einer Dimension addierbar.

## Antworten und Rechnung

- **Skala je Frage:** 0 „trifft nicht zu" … 4 „trifft voll zu" — und **„unbekannt" als
  zulässige Antwort**. Ein Lagebild, das Unwissen nicht ausweisen kann, täuscht Sicherheit vor.
- **Beleggrad je Antwort:** belegt (Dokument, Messung) · geschätzt · Hörensagen.
- **Score je Dimension:** Mittel der beantworteten Fragen, 0–100; dazu „n von 8 beantwortet".
- **Konfidenz:** Anteil belegter Antworten an *allen* Fragen der Dimension — hoch ab ⅔,
  mittel ab ⅓, sonst niedrig. „Unbekannt" senkt die Konfidenz, nicht den Score.
- **Mehrere Bewertungen desselben Prozesses:** **Median** als Score, **Spanne** (max − min)
  daneben. Zwei Befragte, die denselben Prozess völlig verschieden sehen, sind ein Befund,
  kein Rauschen, das man wegmittelt.
- **Kein Gesamtscore** über die Dimensionen: drei Zahlen nebeneinander sind ehrlicher als
  eine, die drei verschiedene Dinge verrechnet.

## Die Matrix

Zeilen = Prozesse, Spalten = Dimensionen; je Zelle Score (blau abgestuft — ein Befund,
keine Ampel), Zahl der Bewertungen, beantwortete Fragen, Spanne und die Konfidenz als
Ampel-Badge. Rechts die Spalten, die **das Board ausfüllt**: Entscheidung (standardisieren ·
markenspezifisch · offen) und Tiefe im Wortlaut des Boards. Farbschlüssel und Legende stehen
vor der ersten Tabelle. Darunter die zweite Lesart: jede Bewertung mit jeder Antwort und
ihrem Beleggrad.

## Was bewusst fehlt

- Kein Harmonisierungs-Vorschlag, keine Rangliste, keine empfohlene Tiefe.
- Keine KI: nur Standardbibliothek, deterministisch, reproduzierbar.
- Kein Gesamtscore.

## Tests

```bash
python -m pytest tests/harmonisation/
```
