# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Beispiel-Arbeitsbereich für den Harmonisierungs-Score: ein generischer
#   Katalog mit 3 × 8 Fragen, vier End-to-End-Prozesse mit APQC-üblichen
#   Namen, drei Bewertungen und zwei Board-Entscheidungen. Der Katalog ist
#   eine ILLUSTRATION der Struktur (3 Dimensionen × 8 Fragen je Prozess) — die Fragen des Erstnutzers sind nicht bekannt
#   und stehen bewusst nicht hier. Keine Inhalte eines realen Konzerns.
#   Jede Frage ist so formuliert, dass hohe Zustimmung FÜR eine
#   Harmonisierung spricht; nur so sind die Werte einer Dimension addierbar.
# =============================================================================

from __future__ import annotations

from datetime import date
from pathlib import Path

from .model import (
    ASSESSMENTS_DIR,
    CATALOGUE_FILE,
    DECISION_BRAND_SPECIFIC,
    DECISION_STANDARDISE,
    DECISIONS_FILE,
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
    EVIDENCE_HEARSAY,
    PROCESSES_FILE,
    SCHEMA_VERSION,
    Answer,
    Assessment,
    Decision,
    Process,
    assessment_filename,
    assessment_to_json,
    decisions_to_json,
    processes_to_json,
    write_json,
)


def _q(qid: str, de: str, en: str) -> dict:
    return {"id": qid, "text": {"de": de, "en": en}}


EXAMPLE_CATALOGUE: dict = {
    "schema_version": SCHEMA_VERSION,
    "name": "Beispielkatalog Harmonisierungs-Score (3 × 8)",
    "note": ("Illustration der Struktur: drei Dimensionen, acht Fragen je Prozess. Hohe "
             "Zustimmung spricht für eine Harmonisierung. Ersetzen Sie die Fragen "
             "durch Ihren eigenen Katalog — diese Datei ist Daten, nicht Code."),
    "dimensions": [
        {
            "id": "business_value",
            "name": {"de": "Business Value", "en": "Business value",
                     "ro": "Valoare de business", "pt": "Valor de negócio",
                     "fr": "Valeur métier"},
            "questions": [
                _q("bv1", "Der Prozess liefert in allen Marken bzw. Einheiten dasselbe Kundenergebnis.",
                   "The process delivers the same customer outcome in every brand or unit."),
                _q("bv2", "Die Unterschiede zwischen den Varianten schaffen keinen erkennbaren Kundennutzen.",
                   "The differences between the variants create no recognisable customer benefit."),
                _q("bv3", "Doppelte Umsetzungen binden Budget, das anderswo fehlt.",
                   "Duplicate implementations tie up budget that is missing elsewhere."),
                _q("bv4", "Kunden oder Partner erleben die Unterschiede heute als Reibung.",
                   "Customers or partners experience the differences as friction today."),
                _q("bv5", "Eine gemeinsame Lösung ließe sich schneller weiterentwickeln als die Varianten.",
                   "A shared solution could be evolved faster than the variants."),
                _q("bv6", "Regulatorik oder Berichtspflichten verlangen ein einheitliches Vorgehen.",
                   "Regulation or reporting duties call for a uniform approach."),
                _q("bv7", "Die Geschäftsseite trägt eine Harmonisierung mit und hat einen benannten Owner.",
                   "The business side backs harmonisation and has a named owner."),
                _q("bv8", "Der Nutzen ist in Zahlen beschrieben (Kosten, Zeit, Qualität).",
                   "The benefit is described in numbers (cost, time, quality)."),
            ],
        },
        {
            "id": "transparency",
            "name": {"de": "Transparenz", "en": "Transparency", "ro": "Transparență",
                     "pt": "Transparência", "fr": "Transparence"},
            "questions": [
                _q("tr1", "Der Ist-Prozess ist je Variante dokumentiert.",
                   "The as-is process is documented per variant."),
                _q("tr2", "Alle beteiligten Anwendungen sind einem Katalog zugeordnet.",
                   "Every application involved is mapped in a catalogue."),
                _q("tr3", "Redundante Anwendungen oder Schritte sind benannt.",
                   "Redundant applications or steps are named."),
                _q("tr4", "Je Variante gibt es einen benannten Prozess-Owner.",
                   "Each variant has a named process owner."),
                _q("tr5", "Kennzahlen zum Prozess werden regelmäßig erhoben.",
                   "Process metrics are collected regularly."),
                _q("tr6", "Die Schnittstellen zu den Nachbarprozessen sind beschrieben.",
                   "The interfaces to neighbouring processes are described."),
                _q("tr7", "Budget und Kostenstellen des Prozesses sind zuordenbar.",
                   "The process's budget and cost centres can be attributed."),
                _q("tr8", "Die Unterschiede zwischen den Varianten sind erklärt — warum, nicht nur dass.",
                   "The differences between the variants are explained — why, not only that."),
            ],
        },
        {
            "id": "it_operations",
            "name": {"de": "IT und Betrieb", "en": "IT and operations",
                     "ro": "IT și operare", "pt": "TI e operações",
                     "fr": "IT et exploitation"},
            "questions": [
                _q("it1", "Die Varianten laufen auf unterschiedlichen Systemen für dieselbe Funktion.",
                   "The variants run on different systems for the same function."),
                _q("it2", "Mindestens eine Variante läuft auf Technik mit auslaufendem Support.",
                   "At least one variant runs on technology with expiring support."),
                _q("it3", "Daten müssen zwischen den Varianten manuell oder über Sonderlösungen abgeglichen werden.",
                   "Data has to be reconciled between variants manually or through special solutions."),
                _q("it4", "Betrieb und Support sind mehrfach aufgebaut (Teams, Verträge, Bereitschaft).",
                   "Operations and support exist several times over (teams, contracts, on-call)."),
                _q("it5", "Sicherheits- und Compliance-Nachweise werden je Variante getrennt geführt.",
                   "Security and compliance evidence is kept separately per variant."),
                _q("it6", "Eine gemeinsame Plattform oder Lösung existiert bereits in mindestens einer Einheit.",
                   "A shared platform or solution already exists in at least one unit."),
                _q("it7", "Die Teams der Varianten teilen keinen Architekturstandard.",
                   "The variants' teams share no architecture standard."),
                _q("it8", "Eine Migration ist technisch absehbar machbar; harte Blocker sind nicht bekannt.",
                   "A migration is technically feasible as far as can be seen; no hard blockers are known."),
            ],
        },
    ],
}

EXAMPLE_PROCESSES = (
    Process("o2d", "Order-to-Delivery", "Head of Logistics", ("Brand A", "Brand B", "Brand C")),
    Process("c2o", "Customer-to-Order", "Head of Sales", ("Brand A", "Brand B", "Brand C")),
    Process("p2p", "Procure-to-Pay", "CPO", ("Brand A", "Brand B")),
    Process("h2r", "Hire-to-Retire", "CHRO", ("Brand A", "Brand B", "Brand C")),
)


def _answers(values: dict[str, int | None], evidence: dict[str, str] | None = None,
             default: str = EVIDENCE_ESTIMATED) -> dict[str, Answer]:
    ev = evidence or {}
    return {qid: Answer(v, ev.get(qid, default)) for qid, v in values.items()}


EXAMPLE_ASSESSMENTS = (
    # Order-to-Delivery: zwei Bewertungen, die sich beim Business Value unterscheiden —
    # die Spannweite in der Matrix ist Absicht.
    Assessment("o2d", "Logistik-Leitung", date(2026, 9, 15), _answers(
        {"bv1": 4, "bv2": 3, "bv3": 4, "bv4": 3, "bv5": 3, "bv6": 2, "bv7": 4, "bv8": 2,
         "tr1": 3, "tr2": 4, "tr3": 3, "tr4": 4, "tr5": 2, "tr6": 2, "tr7": 3, "tr8": 1,
         "it1": 4, "it2": 3, "it3": 4, "it4": 4, "it5": 3, "it6": 2, "it7": 3, "it8": 2},
        {"bv3": EVIDENCE_DOCUMENTED, "tr2": EVIDENCE_DOCUMENTED, "tr4": EVIDENCE_DOCUMENTED,
         "tr7": EVIDENCE_DOCUMENTED, "it1": EVIDENCE_DOCUMENTED, "it2": EVIDENCE_DOCUMENTED,
         "it4": EVIDENCE_DOCUMENTED, "it5": EVIDENCE_DOCUMENTED}),
        "Sicht der Logistik; Zahlen aus dem Anwendungskatalog 09/2026."),
    Assessment("o2d", "IT-Architektur", date(2026, 9, 22), _answers(
        {"bv1": 3, "bv2": 1, "bv3": 4, "bv4": 1, "bv5": 3, "bv6": 2, "bv7": 2, "bv8": None,
         "tr1": 3, "tr2": 4, "tr3": 4, "tr4": 3, "tr5": 2, "tr6": 3, "tr7": 3, "tr8": 2,
         "it1": 4, "it2": 4, "it3": 4, "it4": 4, "it5": 3, "it6": 3, "it7": 4, "it8": 3},
        {"tr2": EVIDENCE_DOCUMENTED, "tr3": EVIDENCE_DOCUMENTED, "tr6": EVIDENCE_DOCUMENTED,
         "it1": EVIDENCE_DOCUMENTED, "it2": EVIDENCE_DOCUMENTED, "it3": EVIDENCE_DOCUMENTED,
         "it4": EVIDENCE_DOCUMENTED, "it6": EVIDENCE_DOCUMENTED, "it7": EVIDENCE_DOCUMENTED,
         "bv4": EVIDENCE_HEARSAY, "bv7": EVIDENCE_HEARSAY}),
        "Sicht der Architektur; Kundennutzen der Unterschiede unklar, Nutzen in Zahlen fehlt."),
    # Customer-to-Order: eine Bewertung, viel unbekannt — Konfidenz bleibt niedrig.
    Assessment("c2o", "Vertriebs-Leitung", date(2026, 9, 29), _answers(
        {"bv1": 1, "bv2": 0, "bv3": 2, "bv4": 0, "bv5": 1, "bv6": 1, "bv7": 1, "bv8": None,
         "tr1": 2, "tr2": None, "tr3": None, "tr4": 3, "tr5": 1, "tr6": None, "tr7": 2, "tr8": 3,
         "it1": 3, "it2": None, "it3": 2, "it4": 3, "it5": None, "it6": 0, "it7": 3, "it8": None},
        {"tr4": EVIDENCE_DOCUMENTED, "tr8": EVIDENCE_DOCUMENTED}),
        "Marken differenzieren sich bewusst im Vertrieb; Unterschiede sind gewollt."),
)

EXAMPLE_DECISIONS = {
    "o2d": Decision("o2d", DECISION_STANDARDISE,
                    "Prozess und Kernsystem gemeinsam; markenspezifisch nur die Zustellfenster",
                    date(2026, 10, 6), "Board"),
    "c2o": Decision("c2o", DECISION_BRAND_SPECIFIC,
                    "Nur die Schnittstelle zu Order-to-Delivery wird vereinheitlicht",
                    date(2026, 10, 6), "Board"),
}


def write_example(root: Path) -> list[Path]:
    """
    Write the example workspace into ``root`` (created if missing).

    Returns the files written. Existing files are overwritten — this is a
    demo workspace, not a place for real assessments.
    """
    root = Path(root)
    written: list[Path] = []
    write_json(root / CATALOGUE_FILE, EXAMPLE_CATALOGUE)
    written.append(root / CATALOGUE_FILE)
    write_json(root / PROCESSES_FILE, processes_to_json(EXAMPLE_PROCESSES))
    written.append(root / PROCESSES_FILE)
    for a in EXAMPLE_ASSESSMENTS:
        path = root / ASSESSMENTS_DIR / assessment_filename(a)
        write_json(path, assessment_to_json(a))
        written.append(path)
    write_json(root / DECISIONS_FILE, decisions_to_json(EXAMPLE_DECISIONS))
    written.append(root / DECISIONS_FILE)
    return written
