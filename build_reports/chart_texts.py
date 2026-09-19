# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       19.09.2026
# Geändert:       19.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Sprachkatalog für die Beschriftungen *innerhalb* der Diagramme: Achsen,
#   Diagrammtitel, Kurvennamen, Kopf- und Fußzeilen. Bis 0.32.0 waren sie fest
#   englisch — mit zwei deutschen Einsprengseln, die niemand gewählt hatte:
#   die Monatsabkürzungen (in zwei Modulen doppelt gepflegt) und „Methode A".
#
#   **Grenze, die hier gezogen wird:** Einen Katalogschlüssel bekommt nur, was
#   im Code entsteht. Alles, was aus den Daten kommt — Stage-Namen aus der
#   Workflow-Konfiguration, Issue-Typen, Projektkürzel, Value-Stream-Namen —
#   läuft **unübersetzt durch**. Ein Stage heißt so, wie er in Jira heißt;
#   ihn zu übersetzen hieße, eine fremde Konfiguration zu verfälschen.
#
#   Dieses Modul ist zugleich die einzige Stelle, an der die Sprachliste des
#   Projekts steht; `portfolio/report_texts.py` importiert sie von hier. Die
#   Abhängigkeit läuft ohnehin so herum (portfolio → build_reports).
# =============================================================================

from __future__ import annotations

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

#: Sprachen in der Reihenfolge der GUI-Flaggen.
LANGUAGES: tuple[str, ...] = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)

#: Vorgabe, wenn niemand eine Sprache nennt.
DEFAULT_LANG = LANG_EN


def normalise(lang: str | None) -> str:
    """Eine unbekannte oder fehlende Sprachangabe fällt auf die Vorgabe."""
    return lang if lang in LANGUAGES else DEFAULT_LANG


#: Monatsabkürzungen für die Achsenbeschriftung, Index 1–12.
#: Bis 0.32.0 standen sie **deutsch und doppelt** in cfd.py und flow_time.py.
#: Keine `%b`-Formatierung: die liefert die Monatsnamen der C-Locale, also
#: englische Namen in einem französischen Report.
MONTHS: dict[str, tuple[str, ...]] = {
    LANG_DE: ("", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
              "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"),
    LANG_EN: ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    LANG_RO: ("", "ian", "feb", "mar", "apr", "mai", "iun",
              "iul", "aug", "sep", "oct", "noi", "dec"),
    LANG_PT: ("", "jan", "fev", "mar", "abr", "mai", "jun",
              "jul", "ago", "set", "out", "nov", "dez"),
    LANG_FR: ("", "janv", "févr", "mars", "avr", "mai", "juin",
              "juil", "août", "sept", "oct", "nov", "déc"),
}


def month_abbr(lang: str = DEFAULT_LANG) -> tuple[str, ...]:
    """Die Monatsabkürzungen der Sprache, Index 1–12 (Index 0 ist leer)."""
    return MONTHS[normalise(lang)]


_TEXTS: dict[str, dict[str, str]] = {

    # -- Achsen --------------------------------------------------------------
    "axis.count": {
        LANG_DE: "Anzahl", LANG_EN: "Count", LANG_RO: "Număr",
        LANG_PT: "Contagem", LANG_FR: "Nombre",
    },
    "axis.count_lower": {
        LANG_DE: "Anzahl", LANG_EN: "count", LANG_RO: "număr",
        LANG_PT: "contagem", LANG_FR: "nombre",
    },
    "axis.date": {
        LANG_DE: "Datum", LANG_EN: "Date", LANG_RO: "Dată", LANG_PT: "Data",
        LANG_FR: "Date",
    },
    "axis.cycle_days": {
        LANG_DE: "Zykluszeit (Tage)", LANG_EN: "CycleDays",
        LANG_RO: "Zile de ciclu", LANG_PT: "Dias de ciclo",
        LANG_FR: "Jours de cycle",
    },
    "axis.days": {
        LANG_DE: "Tage", LANG_EN: "days", LANG_RO: "zile", LANG_PT: "dias",
        LANG_FR: "jours",
    },
    "axis.freq": {
        LANG_DE: "Häufigkeit", LANG_EN: "Freq", LANG_RO: "Frecv.",
        LANG_PT: "Freq.", LANG_FR: "Fréq.",
    },
    "axis.week": {
        LANG_DE: "Woche", LANG_EN: "Week", LANG_RO: "Săptămână",
        LANG_PT: "Semana", LANG_FR: "Semaine",
    },
    "axis.quarter": {
        LANG_DE: "Quartal", LANG_EN: "Quarter", LANG_RO: "Trimestru",
        LANG_PT: "Trimestre", LANG_FR: "Trimestre",
    },
    "axis.stage": {
        LANG_DE: "Stage", LANG_EN: "Stage", LANG_RO: "Stage", LANG_PT: "Stage",
        LANG_FR: "Stage",
    },
    "axis.total_age": {
        LANG_DE: "Gesamtalter (Tage)", LANG_EN: "Total Age (days)",
        LANG_RO: "Vârstă totală (zile)", LANG_PT: "Idade total (dias)",
        LANG_FR: "Âge total (jours)",
    },
    "axis.wip": {
        LANG_DE: "Work in Progress", LANG_EN: "Work in Progress",
        LANG_RO: "Work in Progress", LANG_PT: "Work in Progress",
        LANG_FR: "Work in Progress",
    },
    "axis.feature_per_day": {
        LANG_DE: "Features pro Tag", LANG_EN: "Feature per Day",
        LANG_RO: "Features pe zi", LANG_PT: "Features por dia",
        LANG_FR: "Features par jour",
    },

    # -- CFD -----------------------------------------------------------------
    "cfd.inflow": {
        LANG_DE: "Zufluss-Trend", LANG_EN: "Inflow trend",
        LANG_RO: "Tendință de intrare", LANG_PT: "Tendência de entrada",
        LANG_FR: "Tendance des entrées",
    },
    "cfd.outflow": {
        LANG_DE: "Abfluss-Trend", LANG_EN: "Outflow trend",
        LANG_RO: "Tendință de ieșire", LANG_PT: "Tendência de saída",
        LANG_FR: "Tendance des sorties",
    },
    "cfd.ratio": {
        LANG_DE: "Verhältnis Zu-/Abfluss  {ratio} : 1",
        LANG_EN: "Ratio In/out  {ratio} : 1",
        LANG_RO: "Raport intrări/ieșiri  {ratio} : 1",
        LANG_PT: "Rácio entradas/saídas  {ratio} : 1",
        LANG_FR: "Rapport entrées/sorties  {ratio} : 1",
    },

    # -- Flow Debt -----------------------------------------------------------
    "debt.assumptions_ok": {
        LANG_DE: "Little's Law, Annahmen 1 + 3: erfüllt",
        LANG_EN: "Little's Law assumptions 1 + 3: OK",
        LANG_RO: "Legea lui Little, ipotezele 1 + 3: îndeplinite",
        LANG_PT: "Lei de Little, pressupostos 1 + 3: cumpridos",
        LANG_FR: "Loi de Little, hypothèses 1 + 3 : remplies",
    },
    "debt.assumptions_violated": {
        LANG_DE: "Little's Law, Annahmen 1 + 3: VERLETZT — Befund nicht belastbar",
        LANG_EN: "Little's Law assumptions 1 + 3: VIOLATED — verdict not dependable",
        LANG_RO: "Legea lui Little, ipotezele 1 + 3: ÎNCĂLCATE — verdict nesigur",
        LANG_PT: "Lei de Little, pressupostos 1 + 3: VIOLADOS — veredicto não fiável",
        LANG_FR: "Loi de Little, hypothèses 1 + 3 : NON REMPLIES — verdict non fiable",
    },
    "debt.accumulating": {
        LANG_DE: "Flow Debt wird aufgebaut", LANG_EN: "accumulating Flow Debt",
        LANG_RO: "se acumulează Flow Debt", LANG_PT: "a acumular Flow Debt",
        LANG_FR: "accumulation de Flow Debt",
    },
    "debt.paying_off": {
        LANG_DE: "Flow Debt wird abgebaut", LANG_EN: "paying off Flow Debt",
        LANG_RO: "se reduce Flow Debt", LANG_PT: "a reduzir Flow Debt",
        LANG_FR: "réduction de Flow Debt",
    },
    "debt.stable": {
        LANG_DE: "stabil", LANG_EN: "stable", LANG_RO: "stabil",
        LANG_PT: "estável", LANG_FR: "stable",
    },
    "debt.wip_range": {
        LANG_DE: "WIP ({first} → {closed})", LANG_EN: "WIP ({first} → {closed})",
        LANG_RO: "WIP ({first} → {closed})", LANG_PT: "WIP ({first} → {closed})",
        LANG_FR: "WIP ({first} → {closed})",
    },
    "debt.header": {
        LANG_DE: "{assumptions}<br>Genäherte mittlere CT: {approx}T | "
                 "Exakte mittlere CT: {exact}T | <b>{verdict}</b>",
        LANG_EN: "{assumptions}<br>Approx. mean CT: {approx}d | "
                 "Exact mean CT: {exact}d | <b>{verdict}</b>",
        LANG_RO: "{assumptions}<br>CT medie aproximativă: {approx}z | "
                 "CT medie exactă: {exact}z | <b>{verdict}</b>",
        LANG_PT: "{assumptions}<br>CT média aproximada: {approx}d | "
                 "CT média exata: {exact}d | <b>{verdict}</b>",
        LANG_FR: "{assumptions}<br>CT moyenne approchée : {approx}j | "
                 "CT moyenne exacte : {exact}j | <b>{verdict}</b>",
    },

    # -- Flow Distribution ---------------------------------------------------
    "dist.by_type": {
        LANG_DE: "Nach Vorgangsart", LANG_EN: "By Issue Type",
        LANG_RO: "După tipul elementului", LANG_PT: "Por tipo de item",
        LANG_FR: "Par type d'élément",
    },
    "dist.avg_ct_by_type": {
        LANG_DE: "Mittlere Zykluszeit nach Vorgangsart (Tage)",
        LANG_EN: "Avg Cycle Time by Type (days)",
        LANG_RO: "Zile de ciclu medii pe tip",
        LANG_PT: "Tempo de ciclo médio por tipo (dias)",
        LANG_FR: "Temps de cycle moyen par type (jours)",
    },
    "dist.title": {
        LANG_DE: "{label}  (n={total})", LANG_EN: "{label}  (n={total})",
        LANG_RO: "{label}  (n={total})", LANG_PT: "{label}  (n={total})",
        LANG_FR: "{label}  (n={total})",
    },
    "dist.stage_prominence": {
        LANG_DE: "Stage-Gewicht (n={total})", LANG_EN: "Stage Prominence (n={total})",
        LANG_RO: "Ponderea stage-urilor (n={total})",
        LANG_PT: "Peso dos stages (n={total})",
        LANG_FR: "Poids des stages (n={total})",
    },

    # -- Flow Load -----------------------------------------------------------
    "load.header": {
        LANG_DE: "Flow Load: alternde laufende Arbeit  |  Mittel {mean} | "
                 "Median: {median} | # nicht fertige Vorgänge: {open}",
        LANG_EN: "Flow Load: Aging Work in Progress  |  Mean {mean} | "
                 "Median: {median} | # Not done items: {open}",
        LANG_RO: "Flow Load: lucru în curs care îmbătrânește  |  Medie {mean} | "
                 "Mediană: {median} | # elemente nefinalizate: {open}",
        LANG_PT: "Flow Load: trabalho em curso a envelhecer  |  Média {mean} | "
                 "Mediana: {median} | # itens não concluídos: {open}",
        LANG_FR: "Flow Load : travail en cours qui vieillit  |  Moyenne {mean} | "
                 "Médiane : {median} | # éléments non terminés : {open}",
    },
    "load.ct_reference": {
        LANG_DE: "Zykluszeit-Referenz<br>(aus abgeschlossenen Vorgängen)",
        LANG_EN: "Cycle Time Reference<br>(from closed issues)",
        LANG_RO: "Referință timp de ciclu<br>(din elemente închise)",
        LANG_PT: "Referência de tempo de ciclo<br>(de itens fechados)",
        LANG_FR: "Référence temps de cycle<br>(éléments clos)",
    },
    "load.ct_footer": {
        LANG_DE: "Zykluszeit-Referenz | Median: {median}T | P85: {p85}T | "
                 "Ziel-CT: {target}T | # fertige Vorgänge: {done}",
        LANG_EN: "Cycle Time Reference | Median: {median}d | P85: {p85}d | "
                 "Target CT: {target}d | # Done items: {done}",
        LANG_RO: "Referință timp de ciclu | Mediană: {median}z | P85: {p85}z | "
                 "CT țintă: {target}z | # elemente finalizate: {done}",
        LANG_PT: "Referência de tempo de ciclo | Mediana: {median}d | "
                 "P85: {p85}d | CT alvo: {target}d | # itens concluídos: {done}",
        LANG_FR: "Référence temps de cycle | Médiane : {median}j | "
                 "P85 : {p85}j | CT cible : {target}j | # éléments terminés : {done}",
    },
    "load.ct_median": {
        LANG_DE: "CT Median: {value}T", LANG_EN: "CT Median: {value}d",
        LANG_RO: "CT mediană: {value}z", LANG_PT: "CT mediana: {value}d",
        LANG_FR: "CT médiane : {value}j",
    },
    "load.ct_p85": {
        LANG_DE: "CT P85: {value}T", LANG_EN: "CT P85: {value}d",
        LANG_RO: "CT P85: {value}z", LANG_PT: "CT P85: {value}d",
        LANG_FR: "CT P85 : {value}j",
    },
    "load.target_ct": {
        LANG_DE: "Ziel-CT: {value}T", LANG_EN: "Target CT: {value}d",
        LANG_RO: "CT țintă: {value}z", LANG_PT: "CT alvo: {value}d",
        LANG_FR: "CT cible : {value}j",
    },

    # -- Flow Time -----------------------------------------------------------
    "time.method": {
        LANG_DE: "Methode {method}", LANG_EN: "Method {method}",
        LANG_RO: "Metoda {method}", LANG_PT: "Método {method}",
        LANG_FR: "Méthode {method}",
    },
    "time.header": {
        LANG_DE: "{label} ({method})<br>"
                 "<span style='font-size:10px'>{clock}</span><br>"
                 "Min: {min} | Q1: {q1} | Mittel: {mean} | Median: {median} | "
                 "Q3: {q3} | Max: {max} | #Vorgänge: {count} | "
                 "Ziel-CT ({target_ct}T): {target_pct}% | SD: {sd} | "
                 "SD%(CV): {cv} | Nulltage-Vorgänge entfernt: {zero}",
        LANG_EN: "{label} ({method})<br>"
                 "<span style='font-size:10px'>{clock}</span><br>"
                 "Min: {min} | Q1: {q1} | Mean: {mean} | Median: {median} | "
                 "Q3: {q3} | Max: {max} | #Items: {count} | "
                 "Target CT ({target_ct}d): {target_pct}% | SD: {sd} | "
                 "SD%(CV): {cv} | Zero Day Issues removed: {zero}",
        LANG_RO: "{label} ({method})<br>"
                 "<span style='font-size:10px'>{clock}</span><br>"
                 "Min: {min} | Q1: {q1} | Medie: {mean} | Mediană: {median} | "
                 "Q3: {q3} | Max: {max} | #Elemente: {count} | "
                 "CT țintă ({target_ct}z): {target_pct}% | SD: {sd} | "
                 "SD%(CV): {cv} | Elemente de zero zile eliminate: {zero}",
        LANG_PT: "{label} ({method})<br>"
                 "<span style='font-size:10px'>{clock}</span><br>"
                 "Mín: {min} | Q1: {q1} | Média: {mean} | Mediana: {median} | "
                 "Q3: {q3} | Máx: {max} | #Itens: {count} | "
                 "CT alvo ({target_ct}d): {target_pct}% | SD: {sd} | "
                 "SD%(CV): {cv} | Itens de zero dias removidos: {zero}",
        LANG_FR: "{label} ({method})<br>"
                 "<span style='font-size:10px'>{clock}</span><br>"
                 "Min : {min} | Q1 : {q1} | Moyenne : {mean} | "
                 "Médiane : {median} | Q3 : {q3} | Max : {max} | "
                 "#Éléments : {count} | CT cible ({target_ct}j) : {target_pct}% | "
                 "SD : {sd} | SD%(CV) : {cv} | "
                 "Éléments à zéro jour retirés : {zero}",
    },
    "time.trend": {
        LANG_DE: "Trend (LOESS)", LANG_EN: "Trend (LOESS)",
        LANG_RO: "Tendință (LOESS)", LANG_PT: "Tendência (LOESS)",
        LANG_FR: "Tendance (LOESS)",
    },
    "time.median": {
        LANG_DE: "Median: {value}", LANG_EN: "Median: {value}",
        LANG_RO: "Mediană: {value}", LANG_PT: "Mediana: {value}",
        LANG_FR: "Médiane : {value}",
    },
    "time.p85": {
        LANG_DE: "85. Perz.: {value}", LANG_EN: "85th %: {value}",
        LANG_RO: "Perc. 85: {value}", LANG_PT: "Perc. 85: {value}",
        LANG_FR: "85e perc. : {value}",
    },
    "time.p95": {
        LANG_DE: "95. Perz.: {value}", LANG_EN: "95th %: {value}",
        LANG_RO: "Perc. 95: {value}", LANG_PT: "Perc. 95: {value}",
        LANG_FR: "95e perc. : {value}",
    },

    # -- Zykluszeit-Grenzen (AA1) --------------------------------------------
    # Die Stage-Namen in {first}/{closed} kommen aus der Workflow-Konfiguration
    # und bleiben unübersetzt — sie heißen so, wie sie in Jira heißen.
    "clock.end_undeclared": {
        LANG_DE: "die letzte Stage (Endgrenze nicht erklärt)",
        LANG_EN: "the last stage (end boundary not declared)",
        LANG_RO: "ultimul stage (limita de final nedeclarată)",
        LANG_PT: "o último stage (limite final não declarado)",
        LANG_FR: "le dernier stage (limite de fin non déclarée)",
    },
    "clock.method_b": {
        LANG_DE: "Uhr: Verweildauer über alle Stages vor {end} summiert — "
                 "keine Startgrenze",
        LANG_EN: "Clock: dwell time summed over all stages before {end} — "
                 "no start boundary",
        LANG_RO: "Ceas: timpul de staționare însumat peste toate stage-urile "
                 "înainte de {end} — fără limită de start",
        LANG_PT: "Relógio: tempo de permanência somado em todos os stages "
                 "antes de {end} — sem limite inicial",
        LANG_FR: "Horloge : temps de séjour cumulé sur tous les stages avant "
                 "{end} — pas de limite de départ",
    },
    "clock.method_a": {
        LANG_DE: "Uhr: erster Eintritt in '{first}' → letzter Eintritt in {end}",
        LANG_EN: "Clock: first entry into '{first}' → last entry into {end}",
        LANG_RO: "Ceas: prima intrare în '{first}' → ultima intrare în {end}",
        LANG_PT: "Relógio: primeira entrada em '{first}' → última entrada em {end}",
        LANG_FR: "Horloge : première entrée dans '{first}' → dernière entrée "
                 "dans {end}",
    },
    "clock.no_start": {
        LANG_DE: "Uhr: Startgrenze nicht erklärt (--workflow angeben) → "
                 "letzter Eintritt in {end}",
        LANG_EN: "Clock: start boundary not declared (pass --workflow) → "
                 "last entry into {end}",
        LANG_RO: "Ceas: limita de start nedeclarată (folosiți --workflow) → "
                 "ultima intrare în {end}",
        LANG_PT: "Relógio: limite inicial não declarado (use --workflow) → "
                 "última entrada em {end}",
        LANG_FR: "Horloge : limite de départ non déclarée (passez --workflow) "
                 "→ dernière entrée dans {end}",
    },
    "clock.line": {
        LANG_DE: "{clock} | {note}", LANG_EN: "{clock} | {note}",
        LANG_RO: "{clock} | {note}", LANG_PT: "{clock} | {note}",
        LANG_FR: "{clock} | {note}",
    },
    "boundary.needs_files": {
        LANG_DE: "Grenzprüfung braucht --workflow und --transitions",
        LANG_EN: "boundary check needs --workflow and --transitions",
        LANG_RO: "verificarea limitelor necesită --workflow și --transitions",
        LANG_PT: "a verificação de limites precisa de --workflow e --transitions",
        LANG_FR: "la vérification des limites exige --workflow et --transitions",
    },
    "boundary.never_entered": {
        LANG_DE: "{n} von {total} Vorgängen sind nie in '{stage}' eingetreten",
        LANG_EN: "{n} of {total} items never entered '{stage}'",
        LANG_RO: "{n} din {total} elemente nu au intrat niciodată în '{stage}'",
        LANG_PT: "{n} de {total} itens nunca entraram em '{stage}'",
        LANG_FR: "{n} éléments sur {total} ne sont jamais entrés dans '{stage}'",
    },
    "boundary.effect_b": {
        LANG_DE: "Teilnahme über eine abgeleitete Grenze",
        LANG_EN: "taking part on a derived boundary",
        LANG_RO: "participare pe o limită derivată",
        LANG_PT: "participação através de um limite derivado",
        LANG_FR: "participation sur une limite dérivée",
    },
    "boundary.effect_a": {
        LANG_DE: "Uhr aus einer Nachbar-Stage abgeleitet",
        LANG_EN: "clock derived from a neighbouring stage",
        LANG_RO: "ceas derivat dintr-un stage vecin",
        LANG_PT: "relógio derivado de um stage vizinho",
        LANG_FR: "horloge dérivée d'un stage voisin",
    },
    "boundary.findings": {
        LANG_DE: "{findings} — {effect}", LANG_EN: "{findings} — {effect}",
        LANG_RO: "{findings} — {effect}", LANG_PT: "{findings} — {effect}",
        LANG_FR: "{findings} — {effect}",
    },
    "boundary.all_entered": {
        LANG_DE: "alle {total} Vorgänge sind in {stages} eingetreten",
        LANG_EN: "all {total} items entered {stages}",
        LANG_RO: "toate cele {total} elemente au intrat în {stages}",
        LANG_PT: "todos os {total} itens entraram em {stages}",
        LANG_FR: "les {total} éléments sont tous entrés dans {stages}",
    },
    "boundary.and": {
        LANG_DE: " und ", LANG_EN: " and ", LANG_RO: " și ", LANG_PT: " e ",
        LANG_FR: " et ",
    },

    # -- Flow Velocity -------------------------------------------------------
    "velocity.per_week": {
        LANG_DE: "{label}: Features pro Woche",
        LANG_EN: "{label}: Feature per week",
        LANG_RO: "{label}: features pe săptămână",
        LANG_PT: "{label}: features por semana",
        LANG_FR: "{label} : features par semaine",
    },
    "velocity.per_pi": {
        LANG_DE: "{label}: Features pro PI.  Mittel = {avg}",
        LANG_EN: "{label}: Feature per PI.  Average = {avg}",
        LANG_RO: "{label}: features pe PI.  Medie = {avg}",
        LANG_PT: "{label}: features por PI.  Média = {avg}",
        LANG_FR: "{label} : features par PI.  Moyenne = {avg}",
    },
    "velocity.daily": {
        LANG_DE: "{label}:  von:  {start}  bis:  {end}  Liefertage:  {days}",
        LANG_EN: "{label}:  from:  {start}  to:  {end}  Days delivered:  {days}",
        LANG_RO: "{label}:  de la:  {start}  până la:  {end}  Zile livrate:  {days}",
        LANG_PT: "{label}:  de:  {start}  até:  {end}  Dias entregues:  {days}",
        LANG_FR: "{label} :  du :  {start}  au :  {end}  Jours livrés :  {days}",
    },
    "velocity.avg": {
        LANG_DE: "Mittel: {value}", LANG_EN: "Avg: {value}",
        LANG_RO: "Medie: {value}", LANG_PT: "Média: {value}",
        LANG_FR: "Moyenne : {value}",
    },

    # -- Process Flow --------------------------------------------------------
    "pf.forward": {
        LANG_DE: "Vorwärts-Übergang", LANG_EN: "Forward transition",
        LANG_RO: "Tranziție înainte", LANG_PT: "Transição para a frente",
        LANG_FR: "Transition avant",
    },
    "pf.backward": {
        LANG_DE: "Rückwärts / Nacharbeit", LANG_EN: "Backward / rework",
        LANG_RO: "Înapoi / refacere", LANG_PT: "Para trás / retrabalho",
        LANG_FR: "Retour / reprise",
    },
    "pf.self_loop": {
        LANG_DE: "Selbstschleife", LANG_EN: "Self-loop",
        LANG_RO: "Buclă proprie", LANG_PT: "Auto-ciclo", LANG_FR: "Boucle propre",
    },
    "pf.fast": {
        LANG_DE: "Schnell (kurze Verweildauer)", LANG_EN: "Fast (short dwell)",
        LANG_RO: "Rapid (staționare scurtă)", LANG_PT: "Rápido (permanência curta)",
        LANG_FR: "Rapide (séjour court)",
    },
    "pf.medium": {
        LANG_DE: "Mittel", LANG_EN: "Medium", LANG_RO: "Mediu",
        LANG_PT: "Médio", LANG_FR: "Moyen",
    },
    "pf.slow": {
        LANG_DE: "Langsam (Engpass)", LANG_EN: "Slow (bottleneck)",
        LANG_RO: "Lent (blocaj)", LANG_PT: "Lento (estrangulamento)",
        LANG_FR: "Lent (goulot)",
    },
    "pf.no_data": {
        LANG_DE: "Keine Daten", LANG_EN: "No data", LANG_RO: "Fără date",
        LANG_PT: "Sem dados", LANG_FR: "Aucune donnée",
    },
    "pf.transitions": {
        LANG_DE: "{issues} Vorgänge, {transitions} Übergänge, {pairs} "
                 "eindeutige Paare",
        LANG_EN: "{issues} issues, {transitions} transitions, {pairs} "
                 "unique pairs",
        LANG_RO: "{issues} elemente, {transitions} tranziții, {pairs} "
                 "perechi unice",
        LANG_PT: "{issues} itens, {transitions} transições, {pairs} "
                 "pares únicos",
        LANG_FR: "{issues} éléments, {transitions} transitions, {pairs} "
                 "paires uniques",
    },
    "pf.transitions_only": {
        LANG_DE: "{issues} Vorgänge, {transitions} eindeutige Übergänge",
        LANG_EN: "{issues} issues, {transitions} unique transitions",
        LANG_RO: "{issues} elemente, {transitions} tranziții unice",
        LANG_PT: "{issues} itens, {transitions} transições únicas",
        LANG_FR: "{issues} éléments, {transitions} transitions uniques",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: object) -> str:
    """
    Den Diagrammtext zu ``key`` in ``lang`` liefern, Platzhalter eingesetzt.

    Wie in `portfolio/report_texts.py`: Ein unbekannter Schlüssel ist ein
    Programmierfehler und fliegt; eine unbekannte Sprache kommt aus einer
    Einstellung und fällt still auf die Vorgabe zurück.

    Args:
        key:    Schlüssel aus dem Katalog.
        lang:   Sprachkürzel; unbekannt oder None → DEFAULT_LANG.
        kwargs: Werte für die Platzhalter der Vorlage.

    Returns:
        Der fertige Text.
    """
    return (_TEXTS[key][normalise(lang)].format(**kwargs) if kwargs
            else _TEXTS[key][normalise(lang)])


def keys() -> tuple[str, ...]:
    """Alle Katalogschlüssel (für Vollständigkeitsprüfungen in den Tests)."""
    return tuple(_TEXTS)
