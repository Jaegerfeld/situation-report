# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       19.09.2026
# Geändert:       19.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Sprachkatalog für die Reportschicht des portfolio-Moduls. Bis 0.31.0 waren
#   die Beschriftungen fest englisch, der Kopf der Konferenzmappe dagegen
#   deutsch — eine Seite, zwei Sprachen. Hier steht jeder sichtbare Text einmal
#   je Sprache; `t(key, lang)` liefert ihn. Aufbau bewusst wie
#   `build_reports/terminology.py`: ein Dict, eine Funktion, kein Framework.
#
#   Zusammengesetzte Sätze stehen als **ganze Vorlage mit Platzhaltern**, nicht
#   als aneinandergehängte Bruchstücke — sonst lässt sich die Wortstellung
#   anderer Sprachen nicht abbilden.
# =============================================================================

from __future__ import annotations

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

#: Sprachen in der Reihenfolge der GUI-Flaggen.
LANGUAGES: tuple[str, ...] = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)

#: Vorgabe, wenn niemand eine Sprache nennt. Englisch, weil die Reporttexte
#: bis 0.31.0 englisch waren — so bleibt eine unveränderte Aufrufstelle bei
#: ihrer bisherigen Ausgabe.
DEFAULT_LANG = LANG_EN


def normalise(lang: str | None) -> str:
    """Eine unbekannte oder fehlende Sprachangabe fällt auf die Vorgabe."""
    return lang if lang in LANGUAGES else DEFAULT_LANG


_TEXTS: dict[str, dict[str, str]] = {

    # -- Zellbausteine -------------------------------------------------------
    "cell.yes": {
        LANG_DE: "ja", LANG_EN: "yes", LANG_RO: "da", LANG_PT: "sim",
        LANG_FR: "oui",
    },
    "cell.no": {
        LANG_DE: "nein", LANG_EN: "no", LANG_RO: "nu", LANG_PT: "não",
        LANG_FR: "non",
    },
    "cell.overdue": {
        LANG_DE: " (überfällig)", LANG_EN: " (overdue)",
        LANG_RO: " (întârziat)", LANG_PT: " (em atraso)",
        LANG_FR: " (en retard)",
    },
    "cell.review_due": {
        LANG_DE: " (Wiedervorlage fällig)", LANG_EN: " (review due)",
        LANG_RO: " (revizuire scadentă)", LANG_PT: " (revisão pendente)",
        LANG_FR: " (revue à faire)",
    },
    "cell.supersedes": {
        LANG_DE: " (löst {id} ab)", LANG_EN: " (supersedes {id})",
        LANG_RO: " (înlocuiește {id})", LANG_PT: " (substitui {id})",
        LANG_FR: " (remplace {id})",
    },
    "cell.cross": {
        LANG_DE: "QUER: ", LANG_EN: "CROSS: ", LANG_RO: "TRANSVERSAL: ",
        LANG_PT: "TRANSVERSAL: ", LANG_FR: "TRANSVERSE : ",
    },
    "kind.decision": {
        LANG_DE: "Entscheidung", LANG_EN: "decision", LANG_RO: "decizie",
        LANG_PT: "decisão", LANG_FR: "décision",
    },
    "kind.assumption": {
        LANG_DE: "Annahme", LANG_EN: "assumption", LANG_RO: "ipoteză",
        LANG_PT: "pressuposto", LANG_FR: "hypothèse",
    },

    # -- Datumsformat --------------------------------------------------------
    # Bewusst rein numerisch: %b/%B würden die Monatsnamen der C-Locale
    # liefern, also englische Namen in einem französischen Report.
    "fmt.date": {
        LANG_DE: "%d.%m.%Y", LANG_EN: "%Y-%m-%d", LANG_RO: "%d.%m.%Y",
        LANG_PT: "%d/%m/%Y", LANG_FR: "%d/%m/%Y",
    },
    "fmt.none": {
        LANG_DE: "–", LANG_EN: "–", LANG_RO: "–", LANG_PT: "–", LANG_FR: "–",
    },

    # -- Spaltenköpfe, die mehrere Tabellen teilen ---------------------------
    "col.solution": {
        LANG_DE: "Solution", LANG_EN: "Solution", LANG_RO: "Soluție",
        LANG_PT: "Solução", LANG_FR: "Solution",
    },
    "col.status": {
        LANG_DE: "Status", LANG_EN: "Status", LANG_RO: "Stare",
        LANG_PT: "Estado", LANG_FR: "Statut",
    },
    "col.owner": {
        LANG_DE: "Verantwortlich (Team)", LANG_EN: "Owner (team)",
        LANG_RO: "Responsabil (echipă)", LANG_PT: "Responsável (equipa)",
        LANG_FR: "Responsable (équipe)",
    },
    "col.since": {
        LANG_DE: "Seit", LANG_EN: "Since", LANG_RO: "Din",
        LANG_PT: "Desde", LANG_FR: "Depuis",
    },
    "col.window": {
        LANG_DE: "Zeitfenster", LANG_EN: "Window", LANG_RO: "Fereastră",
        LANG_PT: "Janela", LANG_FR: "Fenêtre",
    },
    "col.source": {
        LANG_DE: "Datenquelle", LANG_EN: "Data source", LANG_RO: "Sursă de date",
        LANG_PT: "Fonte de dados", LANG_FR: "Source de données",
    },
    "col.unit": {
        LANG_DE: "Einheit", LANG_EN: "Unit", LANG_RO: "Unitate",
        LANG_PT: "Unidade", LANG_FR: "Unité",
    },

    # -- Management Summary --------------------------------------------------
    "summary.heading": {
        LANG_DE: "Management Summary", LANG_EN: "Management Summary",
        LANG_RO: "Sumar pentru management", LANG_PT: "Sumário executivo",
        LANG_FR: "Synthèse de direction",
    },
    "summary.items": {
        LANG_DE: "Vorgänge", LANG_EN: "Items", LANG_RO: "Elemente",
        LANG_PT: "Itens", LANG_FR: "Éléments",
    },
    "summary.completed": {
        LANG_DE: "Abgeschlossen", LANG_EN: "Completed", LANG_RO: "Finalizate",
        LANG_PT: "Concluídos", LANG_FR: "Terminés",
    },
    "summary.open_wip": {
        LANG_DE: "Offen (WIP)", LANG_EN: "Open (WIP)", LANG_RO: "Deschise (WIP)",
        LANG_PT: "Em aberto (WIP)", LANG_FR: "En cours (WIP)",
    },
    "summary.median_ct": {
        LANG_DE: "Median CT (T)", LANG_EN: "Median CT (d)",
        LANG_RO: "Mediană CT (z)", LANG_PT: "Mediana CT (d)",
        LANG_FR: "Médiane CT (j)",
    },
    "summary.p85_ct": {
        LANG_DE: "85. Perz. (T)", LANG_EN: "85th % (d)", LANG_RO: "Perc. 85 (z)",
        LANG_PT: "Perc. 85 (d)", LANG_FR: "85e perc. (j)",
    },
    "summary.p95_ct": {
        LANG_DE: "95. Perz. (T)", LANG_EN: "95th % (d)", LANG_RO: "Perc. 95 (z)",
        LANG_PT: "Perc. 95 (d)", LANG_FR: "95e perc. (j)",
    },
    "summary.target_ct": {
        LANG_DE: "≤ {days}T", LANG_EN: "≤ {days}d", LANG_RO: "≤ {days}z",
        LANG_PT: "≤ {days}d", LANG_FR: "≤ {days}j",
    },
    "summary.median_lt": {
        LANG_DE: "Median LT (T)", LANG_EN: "Median LT (d)",
        LANG_RO: "Mediană LT (z)", LANG_PT: "Mediana LT (d)",
        LANG_FR: "Médiane LT (j)",
    },
    "summary.p85_lt": {
        LANG_DE: "85. Perz. LT (T)", LANG_EN: "85th % LT (d)",
        LANG_RO: "Perc. 85 LT (z)", LANG_PT: "Perc. 85 LT (d)",
        LANG_FR: "85e perc. LT (j)",
    },

    # -- Datenqualität -------------------------------------------------------
    "quality.heading": {
        LANG_DE: "Datenqualität je Quelle", LANG_EN: "Data Quality per Source",
        LANG_RO: "Calitatea datelor pe sursă",
        LANG_PT: "Qualidade dos dados por fonte",
        LANG_FR: "Qualité des données par source",
    },
    "quality.coverage": {
        LANG_DE: "{title} — {delivered}/{total} Quellen haben Daten geliefert",
        LANG_EN: "{title} — {delivered}/{total} sources delivered data",
        LANG_RO: "{title} — {delivered}/{total} surse au livrat date",
        LANG_PT: "{title} — {delivered}/{total} fontes forneceram dados",
        LANG_FR: "{title} — {delivered}/{total} sources ont livré des données",
    },
    "quality.col.source": {
        LANG_DE: "Quelle", LANG_EN: "Source", LANG_RO: "Sursă",
        LANG_PT: "Fonte", LANG_FR: "Source",
    },
    "quality.col.records": {
        LANG_DE: "Datensätze", LANG_EN: "Records", LANG_RO: "Înregistrări",
        LANG_PT: "Registos", LANG_FR: "Enregistrements",
    },
    "quality.col.share": {
        LANG_DE: "Anteil", LANG_EN: "Share", LANG_RO: "Pondere",
        LANG_PT: "Quota", LANG_FR: "Part",
    },
    "quality.col.no_first": {
        LANG_DE: "Ohne Startdatum", LANG_EN: "No First Date",
        LANG_RO: "Fără dată de start", LANG_PT: "Sem data inicial",
        LANG_FR: "Sans date de début",
    },
    "quality.col.open_share": {
        LANG_DE: "Anteil offen", LANG_EN: "Open share",
        LANG_RO: "Pondere deschise", LANG_PT: "Quota em aberto",
        LANG_FR: "Part en cours",
    },
    "quality.col.cfd": {
        LANG_DE: "CFD", LANG_EN: "CFD", LANG_RO: "CFD", LANG_PT: "CFD",
        LANG_FR: "CFD",
    },
    "quality.col.as_of": {
        LANG_DE: "Datenstand", LANG_EN: "Data as of", LANG_RO: "Date la",
        LANG_PT: "Dados de", LANG_FR: "Données au",
    },
    "quality.col.confidence": {
        LANG_DE: "Konfidenz", LANG_EN: "Confidence", LANG_RO: "Încredere",
        LANG_PT: "Confiança", LANG_FR: "Confiance",
    },
    "quality.age": {
        LANG_DE: "{date} ({days}T)", LANG_EN: "{date} ({days}d)",
        LANG_RO: "{date} ({days}z)", LANG_PT: "{date} ({days}d)",
        LANG_FR: "{date} ({days}j)",
    },
    "conf.high": {
        LANG_DE: "hoch", LANG_EN: "high", LANG_RO: "ridicată",
        LANG_PT: "alta", LANG_FR: "élevée",
    },
    "conf.medium": {
        LANG_DE: "mittel", LANG_EN: "medium", LANG_RO: "medie",
        LANG_PT: "média", LANG_FR: "moyenne",
    },
    "conf.low": {
        LANG_DE: "niedrig", LANG_EN: "low", LANG_RO: "scăzută",
        LANG_PT: "baixa", LANG_FR: "faible",
    },

    # -- ROAM ----------------------------------------------------------------
    "roam.heading": {
        LANG_DE: "ROAM-Risikoboard", LANG_EN: "ROAM Risk Board",
        LANG_RO: "Tablou de riscuri ROAM", LANG_PT: "Quadro de riscos ROAM",
        LANG_FR: "Tableau des risques ROAM",
    },
    "roam.title": {
        LANG_DE: "{title} — {total} Risiken, {owned} übernommen",
        LANG_EN: "{title} — {total} risks, {owned} owned",
        LANG_RO: "{title} — {total} riscuri, {owned} asumate",
        LANG_PT: "{title} — {total} riscos, {owned} assumidos",
        LANG_FR: "{title} — {total} risques, {owned} pris en charge",
    },
    "roam.title.aging": {
        LANG_DE: ", {aging} übernommen > {days}T",
        LANG_EN: ", {aging} owned > {days}d",
        LANG_RO: ", {aging} asumate > {days}z",
        LANG_PT: ", {aging} assumidos > {days}d",
        LANG_FR: ", {aging} pris en charge > {days}j",
    },
    "roam.col.roam": {
        LANG_DE: "ROAM", LANG_EN: "ROAM", LANG_RO: "ROAM", LANG_PT: "ROAM",
        LANG_FR: "ROAM",
    },
    "roam.col.risk": {
        LANG_DE: "Risiko", LANG_EN: "Risk", LANG_RO: "Risc", LANG_PT: "Risco",
        LANG_FR: "Risque",
    },
    "roam.col.impact": {
        LANG_DE: "Auswirkung", LANG_EN: "Impact", LANG_RO: "Impact",
        LANG_PT: "Impacto", LANG_FR: "Impact",
    },
    "roam.resolved": {
        LANG_DE: "gelöst", LANG_EN: "resolved", LANG_RO: "rezolvat",
        LANG_PT: "resolvido", LANG_FR: "résolu",
    },
    "roam.owned": {
        LANG_DE: "übernommen", LANG_EN: "owned", LANG_RO: "asumat",
        LANG_PT: "assumido", LANG_FR: "pris en charge",
    },
    "roam.accepted": {
        LANG_DE: "hingenommen", LANG_EN: "accepted", LANG_RO: "acceptat",
        LANG_PT: "aceite", LANG_FR: "accepté",
    },
    "roam.mitigated": {
        LANG_DE: "abgemildert", LANG_EN: "mitigated", LANG_RO: "atenuat",
        LANG_PT: "mitigado", LANG_FR: "atténué",
    },
    "impact.high": {
        LANG_DE: "hoch", LANG_EN: "high", LANG_RO: "ridicat", LANG_PT: "alto",
        LANG_FR: "élevé",
    },
    "impact.medium": {
        LANG_DE: "mittel", LANG_EN: "medium", LANG_RO: "mediu",
        LANG_PT: "médio", LANG_FR: "moyen",
    },
    "impact.low": {
        LANG_DE: "gering", LANG_EN: "low", LANG_RO: "scăzut", LANG_PT: "baixo",
        LANG_FR: "faible",
    },

    # -- NFR & Runway --------------------------------------------------------
    "nfr.heading": {
        LANG_DE: "NFR & Architecture Runway", LANG_EN: "NFR & Architecture Runway",
        LANG_RO: "NFR & Architecture Runway", LANG_PT: "NFR & Architecture Runway",
        LANG_FR: "NFR & Architecture Runway",
    },
    "nfr.seg": {
        LANG_DE: "{total} NFRs ({violated} verletzt, {at_risk} gefährdet)",
        LANG_EN: "{total} NFRs ({violated} violated, {at_risk} at risk)",
        LANG_RO: "{total} NFR ({violated} încălcate, {at_risk} în risc)",
        LANG_PT: "{total} NFRs ({violated} violados, {at_risk} em risco)",
        LANG_FR: "{total} NFR ({violated} non tenus, {at_risk} menacés)",
    },
    "runway.seg": {
        LANG_DE: "{total} Runway-Elemente ({gaps} Lücken",
        LANG_EN: "{total} runway elements ({gaps} gaps",
        LANG_RO: "{total} elemente de runway ({gaps} lipsuri",
        LANG_PT: "{total} elementos de runway ({gaps} lacunas",
        LANG_FR: "{total} éléments de runway ({gaps} manques",
    },
    "runway.seg.overdue": {
        LANG_DE: ", {overdue} überfällig)", LANG_EN: ", {overdue} overdue)",
        LANG_RO: ", {overdue} întârziate)", LANG_PT: ", {overdue} em atraso)",
        LANG_FR: ", {overdue} en retard)",
    },
    "nfr.col.nfr": {
        LANG_DE: "NFR", LANG_EN: "NFR", LANG_RO: "NFR", LANG_PT: "NFR",
        LANG_FR: "NFR",
    },
    "nfr.col.target": {
        LANG_DE: "Ziel", LANG_EN: "Target", LANG_RO: "Țintă", LANG_PT: "Meta",
        LANG_FR: "Cible",
    },
    "nfr.col.actual": {
        LANG_DE: "Ist", LANG_EN: "Actual", LANG_RO: "Realizat",
        LANG_PT: "Efetivo", LANG_FR: "Réel",
    },
    "runway.col.element": {
        LANG_DE: "Runway-Element", LANG_EN: "Runway element",
        LANG_RO: "Element de runway", LANG_PT: "Elemento de runway",
        LANG_FR: "Élément de runway",
    },
    "runway.col.needed_by": {
        LANG_DE: "Benötigt bis", LANG_EN: "Needed by", LANG_RO: "Necesar până la",
        LANG_PT: "Necessário até", LANG_FR: "Requis pour",
    },
    "status.met": {
        LANG_DE: "erfüllt", LANG_EN: "met", LANG_RO: "îndeplinit",
        LANG_PT: "cumprido", LANG_FR: "tenu",
    },
    "status.at_risk": {
        LANG_DE: "gefährdet", LANG_EN: "at risk", LANG_RO: "în risc",
        LANG_PT: "em risco", LANG_FR: "menacé",
    },
    "status.violated": {
        LANG_DE: "verletzt", LANG_EN: "violated", LANG_RO: "încălcat",
        LANG_PT: "violado", LANG_FR: "non tenu",
    },
    "status.in_place": {
        LANG_DE: "vorhanden", LANG_EN: "in place", LANG_RO: "existent",
        LANG_PT: "implementado", LANG_FR: "en place",
    },
    "status.building": {
        LANG_DE: "im Aufbau", LANG_EN: "building", LANG_RO: "în construcție",
        LANG_PT: "em construção", LANG_FR: "en construction",
    },
    "status.gap": {
        LANG_DE: "Lücke", LANG_EN: "gap", LANG_RO: "lipsă", LANG_PT: "lacuna",
        LANG_FR: "manque",
    },

    # -- Capability Map ------------------------------------------------------
    "cap.heading": {
        LANG_DE: "Capability-Map & Gesundheit", LANG_EN: "Capability Map & Health",
        LANG_RO: "Harta capabilităților & sănătate",
        LANG_PT: "Mapa de capacidades & saúde",
        LANG_FR: "Carte des capacités & santé",
    },
    "cap.title": {
        LANG_DE: "{title} — {total} Capabilities ({critical} kritisch, "
                 "{at_risk} gefährdet)",
        LANG_EN: "{title} — {total} capabilities ({critical} critical, "
                 "{at_risk} at risk)",
        LANG_RO: "{title} — {total} capabilități ({critical} critice, "
                 "{at_risk} în risc)",
        LANG_PT: "{title} — {total} capacidades ({critical} críticas, "
                 "{at_risk} em risco)",
        LANG_FR: "{title} — {total} capacités ({critical} critiques, "
                 "{at_risk} menacées)",
    },
    "cap.title.uncovered": {
        LANG_DE: ", {uncovered} ohne ART", LANG_EN: ", {uncovered} uncovered",
        LANG_RO: ", {uncovered} neacoperite", LANG_PT: ", {uncovered} sem cobertura",
        LANG_FR: ", {uncovered} non couvertes",
    },
    "cap.col.capability": {
        LANG_DE: "Capability", LANG_EN: "Capability", LANG_RO: "Capabilitate",
        LANG_PT: "Capacidade", LANG_FR: "Capacité",
    },
    "cap.col.health": {
        LANG_DE: "Gesundheit", LANG_EN: "Health", LANG_RO: "Sănătate",
        LANG_PT: "Saúde", LANG_FR: "Santé",
    },
    "cap.col.arts": {
        LANG_DE: "Beteiligte ARTs", LANG_EN: "Contributing ARTs",
        LANG_RO: "ART-uri contribuitoare", LANG_PT: "ARTs contribuintes",
        LANG_FR: "ART contributeurs",
    },
    "cap.col.assessed": {
        LANG_DE: "Bewertet", LANG_EN: "Assessed", LANG_RO: "Evaluat",
        LANG_PT: "Avaliado", LANG_FR: "Évalué",
    },
    "health.healthy": {
        LANG_DE: "gesund", LANG_EN: "healthy", LANG_RO: "sănătos",
        LANG_PT: "saudável", LANG_FR: "sain",
    },
    "health.at_risk": {
        LANG_DE: "gefährdet", LANG_EN: "at risk", LANG_RO: "în risc",
        LANG_PT: "em risco", LANG_FR: "menacé",
    },
    "health.critical": {
        LANG_DE: "kritisch", LANG_EN: "critical", LANG_RO: "critic",
        LANG_PT: "crítico", LANG_FR: "critique",
    },

    # -- Abhängigkeiten ------------------------------------------------------
    "dep.heading": {
        LANG_DE: "Abhängigkeits- & Integrations-Heatmap",
        LANG_EN: "Dependency & Integration Heatmap",
        LANG_RO: "Heatmap de dependențe & integrare",
        LANG_PT: "Mapa de calor de dependências & integração",
        LANG_FR: "Carte de chaleur des dépendances & intégrations",
    },
    "dep.title": {
        LANG_DE: "{title} — {total} Abhängigkeiten ({blocked} blockiert, "
                 "{at_risk} gefährdet",
        LANG_EN: "{title} — {total} dependencies ({blocked} blocked, "
                 "{at_risk} at risk",
        LANG_RO: "{title} — {total} dependențe ({blocked} blocate, "
                 "{at_risk} în risc",
        LANG_PT: "{title} — {total} dependências ({blocked} bloqueadas, "
                 "{at_risk} em risco",
        LANG_FR: "{title} — {total} dépendances ({blocked} bloquées, "
                 "{at_risk} menacées",
    },
    "dep.title.overdue": {
        LANG_DE: ", {overdue} überfällig)", LANG_EN: ", {overdue} overdue)",
        LANG_RO: ", {overdue} întârziate)", LANG_PT: ", {overdue} em atraso)",
        LANG_FR: ", {overdue} en retard)",
    },
    "dep.col.dependency": {
        LANG_DE: "Abhängigkeit", LANG_EN: "Dependency", LANG_RO: "Dependență",
        LANG_PT: "Dependência", LANG_FR: "Dépendance",
    },
    "dep.col.from": {
        LANG_DE: "Von (braucht)", LANG_EN: "From (needs)", LANG_RO: "De la (are nevoie)",
        LANG_PT: "De (precisa)", LANG_FR: "De (a besoin)",
    },
    "dep.col.to": {
        LANG_DE: "An (liefert)", LANG_EN: "To (delivers)", LANG_RO: "Către (livrează)",
        LANG_PT: "Para (entrega)", LANG_FR: "Vers (livre)",
    },
    "dep.col.due": {
        LANG_DE: "Fällig", LANG_EN: "Due", LANG_RO: "Scadent",
        LANG_PT: "Prazo", LANG_FR: "Échéance",
    },
    "dep.grid.header": {
        LANG_DE: "braucht \\ liefert", LANG_EN: "needs \\ delivers",
        LANG_RO: "are nevoie \\ livrează", LANG_PT: "precisa \\ entrega",
        LANG_FR: "a besoin \\ livre",
    },
    "dep.blocked": {
        LANG_DE: "blockiert", LANG_EN: "blocked", LANG_RO: "blocat",
        LANG_PT: "bloqueado", LANG_FR: "bloqué",
    },
    "dep.on_track": {
        LANG_DE: "im Plan", LANG_EN: "on track", LANG_RO: "conform planului",
        LANG_PT: "dentro do plano", LANG_FR: "dans les temps",
    },
    "dep.done": {
        LANG_DE: "erledigt", LANG_EN: "done", LANG_RO: "finalizat",
        LANG_PT: "concluído", LANG_FR: "terminé",
    },

    # -- Entscheidungs- und Annahmenlog --------------------------------------
    "log.heading": {
        LANG_DE: "Entscheidungs- & Annahmenlog", LANG_EN: "Decision & Assumption Log",
        LANG_RO: "Jurnal de decizii & ipoteze",
        LANG_PT: "Registo de decisões & pressupostos",
        LANG_FR: "Journal des décisions & hypothèses",
    },
    "log.title": {
        LANG_DE: "{title} — {decisions} Entscheidungen, {assumptions} Annahmen",
        LANG_EN: "{title} — {decisions} decisions, {assumptions} assumptions",
        LANG_RO: "{title} — {decisions} decizii, {assumptions} ipoteze",
        LANG_PT: "{title} — {decisions} decisões, {assumptions} pressupostos",
        LANG_FR: "{title} — {decisions} décisions, {assumptions} hypothèses",
    },
    "log.title.due": {
        LANG_DE: " ({due} zur Wiedervorlage fällig)",
        LANG_EN: " ({due} due for review)",
        LANG_RO: " ({due} de revizuit)",
        LANG_PT: " ({due} para revisão)",
        LANG_FR: " ({due} à revoir)",
    },
    "log.col.type": {
        LANG_DE: "Art", LANG_EN: "Type", LANG_RO: "Tip", LANG_PT: "Tipo",
        LANG_FR: "Type",
    },
    "log.col.entry": {
        LANG_DE: "Eintrag", LANG_EN: "Entry", LANG_RO: "Intrare",
        LANG_PT: "Entrada", LANG_FR: "Entrée",
    },
    "log.col.logged": {
        LANG_DE: "Erfasst", LANG_EN: "Logged", LANG_RO: "Înregistrat",
        LANG_PT: "Registado", LANG_FR: "Consigné",
    },
    "log.col.review_by": {
        LANG_DE: "Wiedervorlage", LANG_EN: "Review by", LANG_RO: "Revizuire până la",
        LANG_PT: "Rever até", LANG_FR: "Revoir avant",
    },
    "log.proposed": {
        LANG_DE: "vorgeschlagen", LANG_EN: "proposed", LANG_RO: "propus",
        LANG_PT: "proposto", LANG_FR: "proposé",
    },
    "log.accepted": {
        LANG_DE: "angenommen", LANG_EN: "accepted", LANG_RO: "acceptat",
        LANG_PT: "aceite", LANG_FR: "accepté",
    },
    "log.superseded": {
        LANG_DE: "abgelöst", LANG_EN: "superseded", LANG_RO: "înlocuit",
        LANG_PT: "substituído", LANG_FR: "remplacé",
    },
    "log.open": {
        LANG_DE: "offen", LANG_EN: "open", LANG_RO: "deschis",
        LANG_PT: "em aberto", LANG_FR: "ouvert",
    },
    "log.confirmed": {
        LANG_DE: "bestätigt", LANG_EN: "confirmed", LANG_RO: "confirmat",
        LANG_PT: "confirmado", LANG_FR: "confirmé",
    },
    "log.invalidated": {
        LANG_DE: "widerlegt", LANG_EN: "invalidated", LANG_RO: "infirmat",
        LANG_PT: "invalidado", LANG_FR: "infirmé",
    },

    # -- SLO -----------------------------------------------------------------
    "slo.heading": {
        LANG_DE: "Service Levels & Fehlerbudgets",
        LANG_EN: "Service Levels & Error Budgets",
        LANG_RO: "Niveluri de serviciu & bugete de eroare",
        LANG_PT: "Níveis de serviço & orçamentos de erro",
        LANG_FR: "Niveaux de service & budgets d'erreur",
    },
    "slo.title": {
        LANG_DE: "{title} — {total} SLOs ({breached} verletzt, {at_risk} gefährdet)",
        LANG_EN: "{title} — {total} SLOs ({breached} breached, {at_risk} at risk)",
        LANG_RO: "{title} — {total} SLO ({breached} încălcate, {at_risk} în risc)",
        LANG_PT: "{title} — {total} SLOs ({breached} violados, {at_risk} em risco)",
        LANG_FR: "{title} — {total} SLO ({breached} non tenus, {at_risk} menacés)",
    },
    "slo.col.service": {
        LANG_DE: "Dienst", LANG_EN: "Service", LANG_RO: "Serviciu",
        LANG_PT: "Serviço", LANG_FR: "Service",
    },
    "slo.col.slo": {
        LANG_DE: "SLO", LANG_EN: "SLO", LANG_RO: "SLO", LANG_PT: "SLO",
        LANG_FR: "SLO",
    },
    "slo.col.target": {
        LANG_DE: "Ziel %", LANG_EN: "Target %", LANG_RO: "Țintă %",
        LANG_PT: "Meta %", LANG_FR: "Cible %",
    },
    "slo.col.sli": {
        LANG_DE: "SLI %", LANG_EN: "SLI %", LANG_RO: "SLI %", LANG_PT: "SLI %",
        LANG_FR: "SLI %",
    },
    "slo.col.budget": {
        LANG_DE: "Fehlerbudget %", LANG_EN: "Error budget %",
        LANG_RO: "Buget de eroare %", LANG_PT: "Orçamento de erro %",
        LANG_FR: "Budget d'erreur %",
    },
    "slo.breached": {
        LANG_DE: "verletzt", LANG_EN: "breached", LANG_RO: "încălcat",
        LANG_PT: "violado", LANG_FR: "non tenu",
    },
    "slo.unknown": {
        LANG_DE: "unbekannt", LANG_EN: "unknown", LANG_RO: "necunoscut",
        LANG_PT: "desconhecido", LANG_FR: "inconnu",
    },

    # -- DORA ----------------------------------------------------------------
    "dora.heading": {
        LANG_DE: "Delivery Performance (DORA) & Codequalität",
        LANG_EN: "Delivery Performance (DORA) & Code Quality",
        LANG_RO: "Performanța livrării (DORA) & calitatea codului",
        LANG_PT: "Desempenho de entrega (DORA) & qualidade do código",
        LANG_FR: "Performance de livraison (DORA) & qualité du code",
    },
    "dora.title": {
        LANG_DE: "{title} — {total} Einheiten (schlechteste Stufe: {worst})",
        LANG_EN: "{title} — {total} units (worst tier: {worst})",
        LANG_RO: "{title} — {total} unități (cel mai slab nivel: {worst})",
        LANG_PT: "{title} — {total} unidades (pior nível: {worst})",
        LANG_FR: "{title} — {total} unités (niveau le plus bas : {worst})",
    },
    "dora.col.overall": {
        LANG_DE: "Gesamt", LANG_EN: "Overall", LANG_RO: "General",
        LANG_PT: "Global", LANG_FR: "Global",
    },
    "quality.code.heading": {
        LANG_DE: "Codequalität", LANG_EN: "Code quality",
        LANG_RO: "Calitatea codului", LANG_PT: "Qualidade do código",
        LANG_FR: "Qualité du code",
    },
    "quality.col.coverage": {
        LANG_DE: "Abdeckung %", LANG_EN: "Coverage %", LANG_RO: "Acoperire %",
        LANG_PT: "Cobertura %", LANG_FR: "Couverture %",
    },
    "quality.col.maintainability": {
        LANG_DE: "Wartbarkeit", LANG_EN: "Maintainability",
        LANG_RO: "Mentenabilitate", LANG_PT: "Manutenibilidade",
        LANG_FR: "Maintenabilité",
    },
    "quality.col.critical": {
        LANG_DE: "Kritische Befunde", LANG_EN: "Critical issues",
        LANG_RO: "Probleme critice", LANG_PT: "Problemas críticos",
        LANG_FR: "Problèmes critiques",
    },
    "tier.elite": {
        LANG_DE: "elite", LANG_EN: "elite", LANG_RO: "elită", LANG_PT: "elite",
        LANG_FR: "élite",
    },
    "tier.high": {
        LANG_DE: "hoch", LANG_EN: "high", LANG_RO: "ridicat", LANG_PT: "alto",
        LANG_FR: "élevé",
    },
    "tier.medium": {
        LANG_DE: "mittel", LANG_EN: "medium", LANG_RO: "mediu",
        LANG_PT: "médio", LANG_FR: "moyen",
    },
    "tier.low": {
        LANG_DE: "niedrig", LANG_EN: "low", LANG_RO: "scăzut", LANG_PT: "baixo",
        LANG_FR: "faible",
    },
    "tier.unknown": {
        LANG_DE: "unbekannt", LANG_EN: "unknown", LANG_RO: "necunoscut",
        LANG_PT: "desconhecido", LANG_FR: "inconnu",
    },

    # -- Flussproblem-Backlog ------------------------------------------------
    "flow.heading": {
        LANG_DE: "Flussproblem-Backlog (Value-Stream-Konferenz)",
        LANG_EN: "Flow-Problem Backlog (Value-Stream Conference)",
        LANG_RO: "Backlog de probleme de flux (Value-Stream Conference)",
        LANG_PT: "Backlog de problemas de fluxo (Value-Stream Conference)",
        LANG_FR: "Backlog des problèmes de flux (Value-Stream Conference)",
    },
    "flow.title": {
        LANG_DE: "{title} — {total} Probleme ({unresolved} ungelöst, "
                 "{cross} Cross-VS, {survived} über ≥{threshold} Konferenzen)",
        LANG_EN: "{title} — {total} problems ({unresolved} unresolved, "
                 "{cross} cross-VS, {survived} survived ≥{threshold} conferences)",
        LANG_RO: "{title} — {total} probleme ({unresolved} nerezolvate, "
                 "{cross} cross-VS, {survived} peste ≥{threshold} conferințe)",
        LANG_PT: "{title} — {total} problemas ({unresolved} por resolver, "
                 "{cross} cross-VS, {survived} além de ≥{threshold} conferências)",
        LANG_FR: "{title} — {total} problèmes ({unresolved} non résolus, "
                 "{cross} cross-VS, {survived} au-delà de ≥{threshold} conférences)",
    },
    "flow.col.problem": {
        LANG_DE: "Problem", LANG_EN: "Problem", LANG_RO: "Problemă",
        LANG_PT: "Problema", LANG_FR: "Problème",
    },
    "flow.col.raised_by": {
        LANG_DE: "Eingebracht von", LANG_EN: "Raised by", LANG_RO: "Ridicat de",
        LANG_PT: "Levantado por", LANG_FR: "Soulevé par",
    },
    "flow.col.streams": {
        LANG_DE: "Value Streams", LANG_EN: "Value streams",
        LANG_RO: "Value streams", LANG_PT: "Value streams",
        LANG_FR: "Value streams",
    },
    "flow.col.commitment": {
        LANG_DE: "Zusage", LANG_EN: "Commitment", LANG_RO: "Angajament",
        LANG_PT: "Compromisso", LANG_FR: "Engagement",
    },
    "flow.col.follow_up": {
        LANG_DE: "Wiedervorlage-PI", LANG_EN: "Follow-up PI",
        LANG_RO: "PI de urmărire", LANG_PT: "PI de seguimento",
        LANG_FR: "PI de suivi",
    },
    "flow.col.conferences": {
        LANG_DE: "Konf.", LANG_EN: "Conf.", LANG_RO: "Conf.", LANG_PT: "Conf.",
        LANG_FR: "Conf.",
    },
    "flow.committed": {
        LANG_DE: "zugesagt", LANG_EN: "committed", LANG_RO: "angajat",
        LANG_PT: "comprometido", LANG_FR: "engagé",
    },
    "flow.dropped": {
        LANG_DE: "verworfen", LANG_EN: "dropped", LANG_RO: "abandonat",
        LANG_PT: "abandonado", LANG_FR: "abandonné",
    },

    # -- Strategic Themes & Roadmap ------------------------------------------
    "themes.heading": {
        LANG_DE: "Strategic Themes & integrierte Roadmap",
        LANG_EN: "Strategic Themes & Integrated Roadmap",
        LANG_RO: "Strategic Themes & roadmap integrat",
        LANG_PT: "Strategic Themes & roadmap integrado",
        LANG_FR: "Strategic Themes & roadmap intégrée",
    },
    "themes.title": {
        LANG_DE: "{title} — {themes} Themes, {epics} Epics "
                 "({orphans} verwaiste Themes, {zombies} Zombie-Epics)",
        LANG_EN: "{title} — {themes} themes, {epics} epics "
                 "({orphans} orphan themes, {zombies} zombie epics)",
        LANG_RO: "{title} — {themes} teme, {epics} epice "
                 "({orphans} teme orfane, {zombies} epice zombi)",
        LANG_PT: "{title} — {themes} temas, {epics} épicos "
                 "({orphans} temas órfãos, {zombies} épicos zombi)",
        LANG_FR: "{title} — {themes} thèmes, {epics} epics "
                 "({orphans} thèmes orphelins, {zombies} epics zombies)",
    },
    "themes.col.theme": {
        LANG_DE: "Theme", LANG_EN: "Theme", LANG_RO: "Temă", LANG_PT: "Tema",
        LANG_FR: "Thème",
    },
    "themes.col.description": {
        LANG_DE: "Beschreibung", LANG_EN: "Description", LANG_RO: "Descriere",
        LANG_PT: "Descrição", LANG_FR: "Description",
    },
    "themes.col.epics": {
        LANG_DE: "Epics", LANG_EN: "Epics", LANG_RO: "Epice", LANG_PT: "Épicos",
        LANG_FR: "Epics",
    },
    "themes.forgotten": {
        LANG_DE: "0 — erklärt & vergessen", LANG_EN: "0 — declared &amp; forgotten",
        LANG_RO: "0 — declarat & uitat", LANG_PT: "0 — declarado & esquecido",
        LANG_FR: "0 — déclaré & oublié",
    },
    "roadmap.heading": {
        LANG_DE: "Integrierte Roadmap (nah granular, fern grob)",
        LANG_EN: "Integrated roadmap (near-term granular, far-term coarse)",
        LANG_RO: "Roadmap integrat (aproape granular, departe grosier)",
        LANG_PT: "Roadmap integrado (perto granular, longe grosseiro)",
        LANG_FR: "Roadmap intégrée (proche granulaire, lointain grossier)",
    },
    "roadmap.grid.header": {
        LANG_DE: "Train \\ Horizont", LANG_EN: "Train \\ Horizon",
        LANG_RO: "Train \\ Orizont", LANG_PT: "Train \\ Horizonte",
        LANG_FR: "Train \\ Horizon",
    },
    "zombies.heading": {
        LANG_DE: "Zombie-Initiativen (ohne strategisches Zuhause)",
        LANG_EN: "Zombie initiatives (no strategic home)",
        LANG_RO: "Inițiative zombi (fără casă strategică)",
        LANG_PT: "Iniciativas zombi (sem casa estratégica)",
        LANG_FR: "Initiatives zombies (sans foyer stratégique)",
    },
    "epic.in_progress": {
        LANG_DE: "in Arbeit", LANG_EN: "in progress", LANG_RO: "în lucru",
        LANG_PT: "em curso", LANG_FR: "en cours",
    },
    "epic.done": {
        LANG_DE: "fertig", LANG_EN: "done", LANG_RO: "finalizat",
        LANG_PT: "concluído", LANG_FR: "terminé",
    },
    "epic.planned": {
        LANG_DE: "geplant", LANG_EN: "planned", LANG_RO: "planificat",
        LANG_PT: "planeado", LANG_FR: "planifié",
    },

    # -- Farblegende ---------------------------------------------------------
    "legend.key.title": {
        LANG_DE: "Farbschlüssel — was die eingefärbten Zellen bedeuten",
        LANG_EN: "Colour key — what the shaded cells mean",
        LANG_RO: "Cheia culorilor — ce înseamnă celulele colorate",
        LANG_PT: "Chave de cores — o que significam as células coloridas",
        LANG_FR: "Clé des couleurs — ce que signifient les cellules colorées",
    },
    "legend.key.note": {
        LANG_DE: "Jede Tabelle wiederholt den Schlüssel darunter mit ihren "
                 "eigenen Statuswörtern.",
        LANG_EN: "Each table repeats the key with its own status words "
                 "underneath.",
        LANG_RO: "Fiecare tabel repetă cheia dedesubt cu propriile cuvinte "
                 "de stare.",
        LANG_PT: "Cada tabela repete a chave por baixo com as suas próprias "
                 "palavras de estado.",
        LANG_FR: "Chaque tableau répète la clé en dessous avec ses propres "
                 "mots d'état.",
    },
    "legend.green": {
        LANG_DE: "im Plan — keine Handlung nötig",
        LANG_EN: "on plan — no action needed",
        LANG_RO: "conform planului — nicio acțiune necesară",
        LANG_PT: "dentro do plano — sem ação necessária",
        LANG_FR: "dans les temps — aucune action requise",
    },
    "legend.blue": {
        LANG_DE: "zugesagt — Handlung vereinbart, läuft",
        LANG_EN: "committed — action agreed, in progress",
        LANG_RO: "angajat — acțiune convenită, în curs",
        LANG_PT: "comprometido — ação acordada, em curso",
        LANG_FR: "engagé — action convenue, en cours",
    },
    "legend.yellow": {
        LANG_DE: "aufmerksam — offen, gefährdet oder unabgedeckt",
        LANG_EN: "watch — open, at risk or not yet covered",
        LANG_RO: "atenție — deschis, în risc sau neacoperit",
        LANG_PT: "atenção — em aberto, em risco ou sem cobertura",
        LANG_FR: "vigilance — ouvert, menacé ou non couvert",
    },
    "legend.red": {
        LANG_DE: "kritisch — verletzt, blockiert oder überfällig",
        LANG_EN: "critical — breached, blocked or overdue",
        LANG_RO: "critic — încălcat, blocat sau întârziat",
        LANG_PT: "crítico — violado, bloqueado ou em atraso",
        LANG_FR: "critique — non tenu, bloqué ou en retard",
    },
    "legend.grey": {
        LANG_DE: "erledigt oder bewusst hingenommen — keine Handlung",
        LANG_EN: "closed or deliberately accepted — no action",
        LANG_RO: "închis sau acceptat deliberat — nicio acțiune",
        LANG_PT: "fechado ou deliberadamente aceite — sem ação",
        LANG_FR: "clos ou délibérément accepté — aucune action",
    },
    "legend.outlier": {
        LANG_DE: "Ausreißer", LANG_EN: "Outlier", LANG_RO: "Valoare extremă",
        LANG_PT: "Valor atípico", LANG_FR: "Valeur aberrante",
    },
    "legend.outlier.text": {
        LANG_DE: "mehr als das {factor}-Fache des Spaltenmedians",
        LANG_EN: "more than {factor}x the median of that column",
        LANG_RO: "de peste {factor} ori mediana coloanei",
        LANG_PT: "mais de {factor}x a mediana dessa coluna",
        LANG_FR: "plus de {factor}× la médiane de cette colonne",
    },
    "legend.aging": {
        LANG_DE: "überaltert — länger offen als die Wiedervorlagefrist",
        LANG_EN: "aging — open beyond the review age",
        LANG_RO: "învechit — deschis peste termenul de revizuire",
        LANG_PT: "envelhecido — em aberto além do prazo de revisão",
        LANG_FR: "vieillissant — ouvert au-delà du délai de revue",
    },
    "legend.overdue": {
        LANG_DE: "überfällig — das Datum ist verstrichen",
        LANG_EN: "overdue — the date has passed",
        LANG_RO: "întârziat — data a trecut",
        LANG_PT: "em atraso — a data já passou",
        LANG_FR: "en retard — la date est dépassée",
    },
    "legend.uncovered": {
        LANG_DE: "ohne Abdeckung — kein ART liefert sie",
        LANG_EN: "uncovered — no ART delivers it",
        LANG_RO: "neacoperit — niciun ART nu o livrează",
        LANG_PT: "sem cobertura — nenhum ART a entrega",
        LANG_FR: "non couvert — aucun ART ne la livre",
    },
    "legend.review_due": {
        LANG_DE: "Wiedervorlage fällig", LANG_EN: "review is due",
        LANG_RO: "revizuire scadentă", LANG_PT: "revisão pendente",
        LANG_FR: "revue à effectuer",
    },
    "legend.survivor": {
        LANG_DE: "Überlebender — nach drei Konferenzen noch offen",
        LANG_EN: "survivor — still open after three conferences",
        LANG_RO: "supraviețuitor — încă deschis după trei conferințe",
        LANG_PT: "sobrevivente — ainda em aberto após três conferências",
        LANG_FR: "survivant — encore ouvert après trois conférences",
    },
    "legend.crit_issue": {
        LANG_DE: "mindestens ein kritischer Befund",
        LANG_EN: "at least one critical issue",
        LANG_RO: "cel puțin o problemă critică",
        LANG_PT: "pelo menos um problema crítico",
        LANG_FR: "au moins un problème critique",
    },
    "legend.theme_forgotten": {
        LANG_DE: "Theme erklärt, aber kein Epic zahlt darauf ein",
        LANG_EN: "theme declared but no epic carries it",
        LANG_RO: "temă declarată, dar niciun epic nu o susține",
        LANG_PT: "tema declarado mas nenhum épico o suporta",
        LANG_FR: "thème déclaré mais aucun epic ne le porte",
    },
    "legend.zombie": {
        LANG_DE: "Zombie — ohne strategisches Theme",
        LANG_EN: "zombie — no strategic theme",
        LANG_RO: "zombi — fără temă strategică",
        LANG_PT: "zombi — sem tema estratégico",
        LANG_FR: "zombie — sans thème stratégique",
    },
    "legend.worst_pair": {
        LANG_DE: "Zellfarbe = schlechtester Status des Paares",
        LANG_EN: "Cell colour = worst status of that pair",
        LANG_RO: "Culoarea celulei = cea mai slabă stare a perechii",
        LANG_PT: "Cor da célula = pior estado do par",
        LANG_FR: "Couleur de la cellule = pire statut de la paire",
    },
    "legend.marks": {
        LANG_DE: "Zeichen", LANG_EN: "Marks", LANG_RO: "Semne",
        LANG_PT: "Marcas", LANG_FR: "Signes",
    },
    "legend.marks.none": {
        LANG_DE: "(ohne Zeichen = geplant)", LANG_EN: "(no mark = planned)",
        LANG_RO: "(fără semn = planificat)", LANG_PT: "(sem marca = planeado)",
        LANG_FR: "(sans signe = planifié)",
    },
    "legend.rating": {
        LANG_DE: "Bewertung", LANG_EN: "Rating", LANG_RO: "Calificativ",
        LANG_PT: "Classificação", LANG_FR: "Note",
    },
    "legend.tier": {
        LANG_DE: "Stufe", LANG_EN: "Tier", LANG_RO: "Nivel", LANG_PT: "Nível",
        LANG_FR: "Niveau",
    },
    "legend.pressure": {
        LANG_DE: "Druck", LANG_EN: "Pressure", LANG_RO: "Presiune",
        LANG_PT: "Pressão", LANG_FR: "Pression",
    },

    # -- Entscheidungspunkt (P4) ---------------------------------------------
    "dp.heading": {
        LANG_DE: "Entscheidungspunkt — Abhängigkeitsdruck über Value Streams",
        LANG_EN: "Decision Point — Cross-Value-Stream Dependency Pressure",
        LANG_RO: "Punct de decizie — presiunea dependențelor între value streams",
        LANG_PT: "Ponto de decisão — pressão de dependências entre value streams",
        LANG_FR: "Point de décision — pression des dépendances entre value streams",
    },
    "dp.not_applicable": {
        LANG_DE: "Nur über mehrere Value Streams hinweg aussagekräftig — "
                 "diese Konfiguration kennt eine einzige Solution.",
        LANG_EN: "Only meaningful across value streams — this configuration "
                 "knows a single solution.",
        LANG_RO: "Relevant doar între mai multe value streams — această "
                 "configurație cunoaște o singură soluție.",
        LANG_PT: "Só faz sentido entre vários value streams — esta "
                 "configuração conhece uma única solução.",
        LANG_FR: "Pertinent uniquement entre plusieurs value streams — cette "
                 "configuration ne connaît qu'une seule solution.",
    },
    "dp.verdict.no_threshold": {
        LANG_DE: "Druck {value}. Noch kein Schwellenwert vereinbart — nur "
                 "Bericht, kein Alarm.",
        LANG_EN: "Pressure {value}. No threshold agreed yet — reporting only, "
                 "no alarm.",
        LANG_RO: "Presiune {value}. Niciun prag convenit încă — doar "
                 "raportare, fără alarmă.",
        LANG_PT: "Pressão {value}. Ainda sem limiar acordado — apenas relato, "
                 "sem alarme.",
        LANG_FR: "Pression {value}. Aucun seuil convenu — simple constat, pas "
                 "d'alerte.",
    },
    "dp.verdict.below": {
        LANG_DE: "Druck {value} von {threshold} — unter dem Schwellenwert.",
        LANG_EN: "Pressure {value} of {threshold} — below threshold.",
        LANG_RO: "Presiune {value} din {threshold} — sub prag.",
        LANG_PT: "Pressão {value} de {threshold} — abaixo do limiar.",
        LANG_FR: "Pression {value} sur {threshold} — sous le seuil.",
    },
    "dp.verdict.reached": {
        LANG_DE: "Druck {value} von {threshold} — Schwellenwert erreicht. "
                 "Value-Stream-Konferenz einberufen?",
        LANG_EN: "Pressure {value} of {threshold} — threshold reached. "
                 "Convene a Value Stream Conference?",
        LANG_RO: "Presiune {value} din {threshold} — prag atins. Se convoacă "
                 "o Value Stream Conference?",
        LANG_PT: "Pressão {value} de {threshold} — limiar atingido. Convocar "
                 "uma Value Stream Conference?",
        LANG_FR: "Pression {value} sur {threshold} — seuil atteint. Convoquer "
                 "une Value Stream Conference ?",
    },
    "dp.no_open": {
        LANG_DE: "Keine offenen Abhängigkeiten zwischen den Value Streams "
                 "dieses Portfolios.",
        LANG_EN: "No open dependencies between the value streams of this "
                 "portfolio.",
        LANG_RO: "Nicio dependență deschisă între value streams-urile acestui "
                 "portofoliu.",
        LANG_PT: "Sem dependências em aberto entre os value streams deste "
                 "portefólio.",
        LANG_FR: "Aucune dépendance ouverte entre les value streams de ce "
                 "portefeuille.",
    },
    "dp.col.id": {
        LANG_DE: "ID", LANG_EN: "ID", LANG_RO: "ID", LANG_PT: "ID",
        LANG_FR: "ID",
    },
    "dp.col.overdue": {
        LANG_DE: "Überfällig", LANG_EN: "Overdue", LANG_RO: "Întârziere",
        LANG_PT: "Atraso", LANG_FR: "Retard",
    },
    "dp.external": {
        LANG_DE: "{count} weitere offene Abhängigkeiten zeigen aus dem "
                 "Portfolio hinaus (Lieferanten, Fremdsysteme). Sie sind "
                 "realer Druck, aber keine Konferenz dieser Value Streams "
                 "kann darüber entscheiden — sie bleiben außerhalb des "
                 "Indikators.",
        LANG_EN: "{count} further open dependencies point outside the "
                 "portfolio (vendors, external systems). They are real "
                 "pressure, but no conference of these value streams can "
                 "decide about them — they are excluded from the indicator.",
        LANG_RO: "{count} dependențe deschise suplimentare ies din portofoliu "
                 "(furnizori, sisteme externe). Sunt presiune reală, dar "
                 "nicio conferință a acestor value streams nu poate decide "
                 "asupra lor — rămân în afara indicatorului.",
        LANG_PT: "{count} dependências em aberto apontam para fora do "
                 "portefólio (fornecedores, sistemas externos). São pressão "
                 "real, mas nenhuma conferência destes value streams pode "
                 "decidir sobre elas — ficam fora do indicador.",
        LANG_FR: "{count} dépendances ouvertes supplémentaires sortent du "
                 "portefeuille (fournisseurs, systèmes externes). Elles sont "
                 "une pression réelle, mais aucune conférence de ces value "
                 "streams ne peut en décider — elles restent hors de "
                 "l'indicateur.",
    },
    "dp.col.weight": {
        LANG_DE: "Gewicht", LANG_EN: "Weight", LANG_RO: "Pondere",
        LANG_PT: "Peso", LANG_FR: "Poids",
    },
    "dp.overdue": {
        LANG_DE: "überfällig", LANG_EN: "overdue", LANG_RO: "întârziat",
        LANG_PT: "em atraso", LANG_FR: "en retard",
    },

    # -- Delta-Briefing ------------------------------------------------------
    "delta.heading": {
        LANG_DE: "Delta-Briefing — {name}", LANG_EN: "Delta Briefing — {name}",
        LANG_RO: "Briefing delta — {name}", LANG_PT: "Briefing delta — {name}",
        LANG_FR: "Briefing delta — {name}",
    },
    "delta.meta": {
        LANG_DE: "{prev} → {now} ({days} Tage); {completed:+d} Vorgänge im "
                 "Zeitraum abgeschlossen.",
        LANG_EN: "{prev} → {now} ({days} days); {completed:+d} items completed "
                 "in the period.",
        LANG_RO: "{prev} → {now} ({days} zile); {completed:+d} elemente "
                 "finalizate în perioadă.",
        LANG_PT: "{prev} → {now} ({days} dias); {completed:+d} itens "
                 "concluídos no período.",
        LANG_FR: "{prev} → {now} ({days} jours) ; {completed:+d} éléments "
                 "terminés sur la période.",
    },
    "delta.quiet": {
        LANG_DE: "<b>Keine Änderungen</b> zwischen den beiden Snapshots.",
        LANG_EN: "<b>No changes</b> between the two snapshots.",
        LANG_RO: "<b>Nicio schimbare</b> între cele două snapshot-uri.",
        LANG_PT: "<b>Sem alterações</b> entre os dois snapshots.",
        LANG_FR: "<b>Aucun changement</b> entre les deux instantanés.",
    },
    "delta.metrics": {
        LANG_DE: "Kennzahlen", LANG_EN: "Metrics", LANG_RO: "Indicatori",
        LANG_PT: "Indicadores", LANG_FR: "Indicateurs",
    },
    "delta.col.before": {
        LANG_DE: "Vorher", LANG_EN: "Before", LANG_RO: "Înainte",
        LANG_PT: "Antes", LANG_FR: "Avant",
    },
    "delta.col.now": {
        LANG_DE: "Jetzt", LANG_EN: "Now", LANG_RO: "Acum", LANG_PT: "Agora",
        LANG_FR: "Maintenant",
    },
    "delta.col.metric": {
        LANG_DE: "Kennzahl", LANG_EN: "Metric", LANG_RO: "Indicator",
        LANG_PT: "Indicador", LANG_FR: "Indicateur",
    },
    "delta.improved": {
        LANG_DE: "Verbessert", LANG_EN: "Improved", LANG_RO: "Îmbunătățit",
        LANG_PT: "Melhorado", LANG_FR: "Amélioré",
    },
    "delta.worsened": {
        LANG_DE: "Verschlechtert", LANG_EN: "Worsened", LANG_RO: "Înrăutățit",
        LANG_PT: "Piorado", LANG_FR: "Dégradé",
    },
    "delta.legend.better": {
        LANG_DE: "in die gute Richtung bewegt",
        LANG_EN: "moved in the good direction",
        LANG_RO: "s-a mișcat în direcția bună",
        LANG_PT: "moveu-se na direção certa",
        LANG_FR: "a évolué dans le bon sens",
    },
    "delta.legend.worse": {
        LANG_DE: "in die schlechte Richtung bewegt",
        LANG_EN: "moved in the bad direction",
        LANG_RO: "s-a mișcat în direcția rea",
        LANG_PT: "moveu-se na direção errada",
        LANG_FR: "a évolué dans le mauvais sens",
    },
    "delta.legend.volume": {
        LANG_DE: "Mengenänderungen (Vorgänge, Abgeschlossen) bleiben "
                 "uneingefärbt — sie sind weder das eine noch das andere.",
        LANG_EN: "Volume changes (items, completed) stay unshaded — they are "
                 "neither.",
        LANG_RO: "Schimbările de volum (elemente, finalizate) rămân "
                 "necolorate — nu sunt nici una, nici alta.",
        LANG_PT: "Alterações de volume (itens, concluídos) ficam sem cor — "
                 "não são nem uma coisa nem outra.",
        LANG_FR: "Les variations de volume (éléments, terminés) restent sans "
                 "couleur — elles ne sont ni l'un ni l'autre.",
    },

    "delta.units": {
        LANG_DE: "Einheiten", LANG_EN: "Units", LANG_RO: "Unități",
        LANG_PT: "Unidades", LANG_FR: "Unités",
    },
    "delta.confidence": {
        LANG_DE: "Datenkonfidenz", LANG_EN: "Data confidence",
        LANG_RO: "Încrederea în date", LANG_PT: "Confiança nos dados",
        LANG_FR: "Confiance des données",
    },
    "delta.new": {
        LANG_DE: "neu", LANG_EN: "new", LANG_RO: "nou", LANG_PT: "novo",
        LANG_FR: "nouveau",
    },
    "delta.removed": {
        LANG_DE: "entfallen", LANG_EN: "removed", LANG_RO: "eliminat",
        LANG_PT: "removido", LANG_FR: "supprimé",
    },
    "delta.newly_overdue": {
        LANG_DE: "neu überfällig", LANG_EN: "newly overdue",
        LANG_RO: "nou întârziat", LANG_PT: "novo em atraso",
        LANG_FR: "nouvellement en retard",
    },
    "section.risks": {
        LANG_DE: "ROAM-Risiken", LANG_EN: "ROAM risks", LANG_RO: "Riscuri ROAM",
        LANG_PT: "Riscos ROAM", LANG_FR: "Risques ROAM",
    },
    "section.dependencies": {
        LANG_DE: "Abhängigkeiten", LANG_EN: "Dependencies",
        LANG_RO: "Dependănțe", LANG_PT: "Dependências",
        LANG_FR: "Dépendances",
    },
    "section.nfr": {
        LANG_DE: "NFRs", LANG_EN: "NFRs", LANG_RO: "NFR-uri", LANG_PT: "NFRs",
        LANG_FR: "NFR",
    },
    "section.runway": {
        LANG_DE: "Architecture Runway", LANG_EN: "Architecture runway",
        LANG_RO: "Architecture runway", LANG_PT: "Architecture runway",
        LANG_FR: "Architecture runway",
    },
    "section.capabilities": {
        LANG_DE: "Capabilities", LANG_EN: "Capabilities",
        LANG_RO: "Capabilități", LANG_PT: "Capacidades",
        LANG_FR: "Capacités",
    },
    "section.decisions": {
        LANG_DE: "Entscheidungen & Annahmen", LANG_EN: "Decisions & assumptions",
        LANG_RO: "Decizii & ipoteze", LANG_PT: "Decisões & pressupostos",
        LANG_FR: "Décisions & hypothèses",
    },
    "section.epics": {
        LANG_DE: "Roadmap-Epics (aktualisierte Roadmaps)",
        LANG_EN: "Roadmap epics (updated roadmaps)",
        LANG_RO: "Epice de roadmap (roadmap-uri actualizate)",
        LANG_PT: "Épicos de roadmap (roadmaps atualizados)",
        LANG_FR: "Epics de roadmap (roadmaps mises à jour)",
    },
    # -- Konferenzmappe ------------------------------------------------------
    # ACHTUNG: Die deutschen Einträge dieses Blocks sind Roberts eigene Prosa
    # aus 0.31.0 und stehen hier ZEICHENGENAU. Sie werden nicht geglättet,
    # nicht neu übersetzt und nicht "verbessert" — die anderen vier Sprachen
    # sind daraus übertragen.
    "vsc.title": {
        LANG_DE: "Value-Stream-Konferenz — Vorbereitungsmappe",
        LANG_EN: "Value-Stream Conference — Pre-Read",
        LANG_RO: "Value-Stream Conference — dosar de pregătire",
        LANG_PT: "Value-Stream Conference — dossier de preparação",
        LANG_FR: "Value-Stream Conference — dossier de préparation",
    },
    "vsc.meta": {
        LANG_DE: "{name} · {slot} · Stand {today} — Inputs in "
                 "Sitzungsreihenfolge; der vollständige interaktive Report "
                 "bleibt die Detailquelle.",
        LANG_EN: "{name} · {slot} · as of {today} — inputs in meeting order; "
                 "the full interactive report stays the detail source.",
        LANG_RO: "{name} · {slot} · la {today} — inputurile în ordinea "
                 "ședinței; raportul interactiv complet rămâne sursa de detaliu.",
        LANG_PT: "{name} · {slot} · em {today} — inputs na ordem da reunião; "
                 "o relatório interativo completo continua a ser a fonte de "
                 "detalhe.",
        LANG_FR: "{name} · {slot} · au {today} — inputs dans l'ordre de la "
                 "séance ; le rapport interactif complet reste la source de "
                 "détail.",
    },
    "vsc.no_date": {
        LANG_DE: "Konferenztermin nicht gesetzt",
        LANG_EN: "no conference date set",
        LANG_RO: "data conferinței nu este stabilită",
        LANG_PT: "data da conferência não definida",
        LANG_FR: "date de la conférence non définie",
    },
    "vsc.date": {
        LANG_DE: "Konferenz {date} ({lead})",
        LANG_EN: "conference {date} ({lead})",
        LANG_RO: "conferință {date} ({lead})",
        LANG_PT: "conferência {date} ({lead})",
        LANG_FR: "conférence {date} ({lead})",
    },
    "vsc.lead.days": {
        LANG_DE: "noch {days} Tage", LANG_EN: "{days} days to go",
        LANG_RO: "mai sunt {days} zile", LANG_PT: "faltam {days} dias",
        LANG_FR: "encore {days} jours",
    },
    "vsc.lead.tomorrow": {
        LANG_DE: "morgen", LANG_EN: "tomorrow", LANG_RO: "mâine",
        LANG_PT: "amanhã", LANG_FR: "demain",
    },
    "vsc.lead.today": {
        LANG_DE: "heute", LANG_EN: "today", LANG_RO: "azi", LANG_PT: "hoje",
        LANG_FR: "aujourd'hui",
    },
    "vsc.lead.yesterday": {
        LANG_DE: "gestern", LANG_EN: "yesterday", LANG_RO: "ieri",
        LANG_PT: "ontem", LANG_FR: "hier",
    },
    "vsc.lead.past": {
        LANG_DE: "vor {days} Tagen", LANG_EN: "{days} days ago",
        LANG_RO: "acum {days} zile", LANG_PT: "há {days} dias",
        LANG_FR: "il y a {days} jours",
    },
    "vsc.input1": {
        LANG_DE: "Input 1 · Aktuelle Daten", LANG_EN: "Input 1 · Current data",
        LANG_RO: "Input 1 · Date actuale", LANG_PT: "Input 1 · Dados atuais",
        LANG_FR: "Input 1 · Données actuelles",
    },
    "vsc.input2": {
        LANG_DE: "Input 2 · Impediment-Backlog & Governance",
        LANG_EN: "Input 2 · Impediment backlog & governance",
        LANG_RO: "Input 2 · Backlog de impedimente & guvernanță",
        LANG_PT: "Input 2 · Backlog de impedimentos & governação",
        LANG_FR: "Input 2 · Backlog d'obstacles & gouvernance",
    },
    "vsc.input3": {
        LANG_DE: "Input 3 · Business Objectives (Capability-Map & SLOs)",
        LANG_EN: "Input 3 · Business objectives (capability map & SLOs)",
        LANG_RO: "Input 3 · Obiective de business (harta capabilităților & SLO)",
        LANG_PT: "Input 3 · Objetivos de negócio (mapa de capacidades & SLOs)",
        LANG_FR: "Input 3 · Objectifs métier (carte des capacités & SLO)",
    },
    "vsc.input4": {
        LANG_DE: "Input 4 · Integrierte Roadmap & Strategic Themes",
        LANG_EN: "Input 4 · Integrated roadmap & strategic themes",
        LANG_RO: "Input 4 · Roadmap integrat & strategic themes",
        LANG_PT: "Input 4 · Roadmap integrado & strategic themes",
        LANG_FR: "Input 4 · Roadmap intégrée & strategic themes",
    },
    "art.detail.quality": {
        LANG_DE: "ART-Detail — Datenqualität je ART",
        LANG_EN: "ART Detail — Data Quality per ART",
        LANG_RO: "Detaliu ART — calitatea datelor per ART",
        LANG_PT: "Detalhe ART — qualidade dos dados por ART",
        LANG_FR: "Détail ART — qualité des données par ART",
    },
    "art.detail": {
        LANG_DE: "ART-Detail — Management Summary je ART",
        LANG_EN: "ART Detail — Management Summary per ART",
        LANG_RO: "Detaliu ART — sumar de management per ART",
        LANG_PT: "Detalhe ART — sumário executivo por ART",
        LANG_FR: "Détail ART — synthèse de direction par ART",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: object) -> str:
    """
    Den Text zu ``key`` in ``lang`` liefern, Platzhalter eingesetzt.

    Ein unbekannter Schlüssel ist ein Programmierfehler und fliegt als
    KeyError — eine stille Ersatzausgabe würde in einem Report landen und dort
    niemandem auffallen. Eine unbekannte *Sprache* dagegen fällt still auf die
    Vorgabe zurück: Sie kommt aus einer Einstellung, nicht aus dem Code.

    Args:
        key:    Schlüssel aus dem Katalog.
        lang:   Sprachkürzel; unbekannt oder None → DEFAULT_LANG.
        kwargs: Werte für die Platzhalter der Vorlage.

    Returns:
        Der fertige Text.
    """
    eintrag = _TEXTS[key]
    text = eintrag[normalise(lang)]
    return text.format(**kwargs) if kwargs else text


def keys() -> tuple[str, ...]:
    """Alle Katalogschlüssel (für Vollständigkeitsprüfungen in den Tests)."""
    return tuple(_TEXTS)
