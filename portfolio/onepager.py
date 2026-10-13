# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Lagevortrag-Einseiter (Roadmap P6, aus einem Praxis-Workshop: „eine
#   fokussierte Folie, die jeder sofort lesen kann"). Vier Dimensionen
#   (Flow · Qualität · Wert · Abhängigkeiten) × drei Fragen (Wo stehen wir?
#   Was hat sich geändert? Was folgt daraus?), BLUF oben, Konfidenz je Zelle,
#   eine Seite. Alles deterministisch aus den Registern und Kennzahlen, die
#   Report, Konferenzmappe und Delta-Briefing schon kennen — keine neue
#   Rechnung, kein Urteil: Spalte 3 nennt nur, WO entschieden werden muss
#   (Wecker über Schwelle, Flussprobleme ab der dritten Konferenz, frisch
#   Überfälliges, verletzte SLO/NFR, abgelaufene Annahmen), und lässt dem
#   Vortragenden ein Feld. Der Kata-Modus rendert dieselbe Seite leer als
#   Übungsblatt des Curriculums („eine Lageanalyse in 30 Minuten").
#   Entscheidungen Robert 13.10.2026: Vierklang vom Post-it, Spalte 3 =
#   Entscheidungsbedarf + Freitext, Kata jetzt, BLUF als Vorlagensatz.
# =============================================================================

from __future__ import annotations

import html as _html
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .capability_config import HEALTH_CRITICAL
from .decision_config import ASSUMPTION_OPEN, KIND_ASSUMPTION
from .dependency_config import DEP_AT_RISK, DEP_BLOCKED, DEP_DONE
from .dora_config import unit_tier
from .nfr_config import RUNWAY_GAP, STATUS_VIOLATED
from .report_texts import DEFAULT_LANG
from .slo_config import SLO_AT_RISK, SLO_BREACHED, slo_status
from .solution_config import SolutionConfig
from .summary import CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM

CONF_NONE = "none"
DIMENSIONS = ("flow", "quality", "value", "dependencies")
QUESTIONS = ("q1", "q2", "q3")
#: Register dates younger than this count as fresh (same rule as A1).
_FRESH_DAYS = 30
_MAX_NAMES = 3

_T: dict[str, dict[str, str]] = {
    "de": {
        "title": "Lagevortrag — Einseiter", "kata_title": "Lagevortrag — Übungsblatt (Kata)",
        "bluf": "BLUF", "meta": "{name} · Stand {today} · Fenster {frm} – {to}",
        "meta_prev": "Vergleichsstand {prev}", "meta_noprev": "kein Vergleichsstand",
        "meta_conf": "Konferenz am {date}",
        "q1": "Wo stehen wir?", "q2": "Was hat sich geändert?", "q3": "Was folgt daraus?",
        "flow": "Flow", "quality": "Qualität", "value": "Wert", "dependencies": "Abhängigkeiten",
        "conf_high": "hoch", "conf_medium": "mittel", "conf_low": "niedrig", "conf_none": "fehlt",
        "no_data": "kein Register verbunden", "no_prev": "kein Vergleichsstand — Spalte leer",
        "no_decision": "kein Entscheidungspunkt erreicht", "decide": "Entscheidungsbedarf:",
        "speaker": "Vortragende(r):", "speaker_hint": "Urteil, Optionen, Empfehlung — hier eintragen",
        "kata_hint": "Übungsblatt: 30 Minuten, dann mit dem gefüllten Einseiter vergleichen. "
                     "Je Zelle höchstens drei Zeilen, BLUF zuerst.",
        "legend": "Konfidenz je Zelle: hoch = Quelle frisch und vollständig · mittel = vorhanden, "
                  "ohne Datum oder älter als 30 Tage · niedrig = lückenhaft · fehlt = kein Register. "
                  "Zahlen stammen aus dem Datenpfad; Spalte 3 nennt nur, wo entschieden werden muss.",
        "sources": "Quellen", "units": "{n} Einheiten",
        "footer": "SituationReport · Lagevortrag-Einseiter (P6) · deterministisch, ohne KI-Anteil",
        # Flow
        "f_items": "{items} Vorgänge · {completed} fertig · {open} offen (WIP)",
        "f_ct": "Median-CT {median} d · P85 {p85} d · {pct} % innerhalb {target} d",
        "f_flow": "{n} Flussprobleme offen · {survived} seit ≥ 3 Konferenzen · {cross} Cross-VS",
        "f_delta_tp": "Durchsatz {delta:+d} fertig in {days} Tagen",
        "f_delta_ct": "Median-CT {old} → {new} d",
        "f_delta_fp": "Flussprobleme: {added} neu · {changed} Statuswechsel",
        "f_decide": "Flussprobleme ab der dritten Konferenz: {names}",
        # Quality
        "qu_dora": "DORA {n} Einheiten: {tiers}", "qu_slo": "SLO {n} Dienste · {breached} verletzt · {risk} gefährdet",
        "qu_nfr": "NFR {n} · {violated} verletzt · Runway-Lücken {gaps}",
        "qu_delta_slo": "SLO-Übergänge: {changed} ({worse} Verschlechterungen)",
        "qu_delta_nfr": "NFR/Runway: {changed} Statuswechsel · {overdue} frisch überfällig",
        "qu_decide_slo": "SLO verletzt: {names}", "qu_decide_nfr": "NFR verletzt: {names}",
        "qu_decide_runway": "Runway-Lücke überfällig: {names}",
        # Value
        "v_caps": "Capabilities {n}: {counts}", "v_themes": "Themes {n} · {forgotten} ohne Epic",
        "v_epics": "Epics {n} ({counts}) · {zombies} ohne Theme",
        "v_delta_caps": "Capabilities: {changed} Health-Wechsel ({worse} schlechter)",
        "v_delta_epics": "Roadmap: {added} neue Epics · {changed} geändert",
        "v_decide_caps": "Capability kritisch: {names}", "v_decide_themes": "Theme ohne Epic: {names}",
        "v_decide_zombies": "Epic ohne Theme: {names}",
        "v_decide_assumptions": "Annahme über Prüfdatum: {names}",
        # Dependencies
        "d_pressure": "Cross-VS-Druck {value} · Schwelle {threshold}", "d_pressure_none": "Cross-VS-Druck {value} · keine Schwelle vereinbart",
        "d_pressure_na": "Cross-VS-Druck nicht anwendbar (eine Solution)",
        "d_deps": "{n} Abhängigkeiten · {blocked} blockiert · {risk} gefährdet · {overdue} überfällig",
        "d_risks": "ROAM {n} · {owned} owned · {unmitigated} ohne Mitigation",
        "d_delta_deps": "Abhängigkeiten: {changed} Statuswechsel · {overdue} frisch überfällig",
        "d_delta_risks": "Risiken: {added} neu · {changed} ROAM-Wechsel",
        "d_decide_wecker": "Wecker: Druck {value} ≥ Schwelle {threshold} — Value-Stream-Konferenz einberufen?",
        "d_decide_overdue": "Abhängigkeit überfällig: {names}",
        # BLUF
        "b_wecker": "Cross-VS-Druck {value} über Schwelle {threshold}",
        "b_survived": "{n} Flussproblem(e) überleben die dritte Konferenz",
        "b_slo": "{n} SLO verletzt", "b_nfr": "{n} NFR verletzt", "b_caps": "{n} Capability kritisch",
        "b_overdue": "{n} Abhängigkeiten überfällig",
        "b_calm": "Lage im Rahmen der vereinbarten Schwellen",
        "b_tail": "{items} Vorgänge, Median-CT {median} d",
    },
    "en": {
        "title": "Situation briefing — one page", "kata_title": "Situation briefing — practice sheet (kata)",
        "bluf": "BLUF", "meta": "{name} · as of {today} · window {frm} – {to}",
        "meta_prev": "compared with {prev}", "meta_noprev": "no earlier state",
        "meta_conf": "conference on {date}",
        "q1": "Where do we stand?", "q2": "What has changed?", "q3": "What follows?",
        "flow": "Flow", "quality": "Quality", "value": "Value", "dependencies": "Dependencies",
        "conf_high": "high", "conf_medium": "medium", "conf_low": "low", "conf_none": "missing",
        "no_data": "no register connected", "no_prev": "no earlier state — column empty",
        "no_decision": "no decision point reached", "decide": "Decision needed:",
        "speaker": "Presenter:", "speaker_hint": "judgement, options, recommendation — enter here",
        "kata_hint": "Practice sheet: 30 minutes, then compare with the filled page. "
                     "At most three lines per cell, BLUF first.",
        "legend": "Confidence per cell: high = source fresh and complete · medium = present, undated or "
                  "older than 30 days · low = gappy · missing = no register. Numbers come from the data "
                  "path; column 3 only names where a decision is due.",
        "sources": "Sources", "units": "{n} units",
        "footer": "SituationReport · situation briefing one-pager (P6) · deterministic, no AI involved",
        "f_items": "{items} items · {completed} done · {open} open (WIP)",
        "f_ct": "median CT {median} d · P85 {p85} d · {pct} % within {target} d",
        "f_flow": "{n} flow problems open · {survived} for ≥ 3 conferences · {cross} cross-VS",
        "f_delta_tp": "throughput {delta:+d} done in {days} days",
        "f_delta_ct": "median CT {old} → {new} d",
        "f_delta_fp": "flow problems: {added} new · {changed} status changes",
        "f_decide": "flow problems past the third conference: {names}",
        "qu_dora": "DORA {n} units: {tiers}", "qu_slo": "SLO {n} services · {breached} breached · {risk} at risk",
        "qu_nfr": "NFR {n} · {violated} violated · runway gaps {gaps}",
        "qu_delta_slo": "SLO transitions: {changed} ({worse} worsenings)",
        "qu_delta_nfr": "NFR/runway: {changed} status changes · {overdue} newly overdue",
        "qu_decide_slo": "SLO breached: {names}", "qu_decide_nfr": "NFR violated: {names}",
        "qu_decide_runway": "runway gap overdue: {names}",
        "v_caps": "capabilities {n}: {counts}", "v_themes": "themes {n} · {forgotten} without epic",
        "v_epics": "epics {n} ({counts}) · {zombies} without theme",
        "v_delta_caps": "capabilities: {changed} health changes ({worse} worse)",
        "v_delta_epics": "roadmap: {added} new epics · {changed} changed",
        "v_decide_caps": "capability critical: {names}", "v_decide_themes": "theme without epic: {names}",
        "v_decide_zombies": "epic without theme: {names}",
        "v_decide_assumptions": "assumption past review date: {names}",
        "d_pressure": "cross-VS pressure {value} · threshold {threshold}", "d_pressure_none": "cross-VS pressure {value} · no threshold agreed",
        "d_pressure_na": "cross-VS pressure not applicable (single solution)",
        "d_deps": "{n} dependencies · {blocked} blocked · {risk} at risk · {overdue} overdue",
        "d_risks": "ROAM {n} · {owned} owned · {unmitigated} without mitigation",
        "d_delta_deps": "dependencies: {changed} status changes · {overdue} newly overdue",
        "d_delta_risks": "risks: {added} new · {changed} ROAM changes",
        "d_decide_wecker": "wake-up: pressure {value} ≥ threshold {threshold} — convene the value-stream conference?",
        "d_decide_overdue": "dependency overdue: {names}",
        "b_wecker": "cross-VS pressure {value} above threshold {threshold}",
        "b_survived": "{n} flow problem(s) survive the third conference",
        "b_slo": "{n} SLO breached", "b_nfr": "{n} NFR violated", "b_caps": "{n} capability critical",
        "b_overdue": "{n} dependencies overdue",
        "b_calm": "situation within the agreed thresholds",
        "b_tail": "{items} items, median CT {median} d",
    },
    "ro": {
        "title": "Raport de situație — o pagină", "kata_title": "Raport de situație — fișă de exercițiu (kata)",
        "bluf": "BLUF", "meta": "{name} · stare la {today} · fereastră {frm} – {to}",
        "meta_prev": "comparat cu {prev}", "meta_noprev": "fără stare anterioară",
        "meta_conf": "conferință la {date}",
        "q1": "Unde ne aflăm?", "q2": "Ce s-a schimbat?", "q3": "Ce urmează?",
        "flow": "Flux", "quality": "Calitate", "value": "Valoare", "dependencies": "Dependențe",
        "conf_high": "ridicată", "conf_medium": "medie", "conf_low": "scăzută", "conf_none": "lipsește",
        "no_data": "niciun registru conectat", "no_prev": "fără stare anterioară — coloană goală",
        "no_decision": "niciun punct de decizie atins", "decide": "Decizie necesară:",
        "speaker": "Prezentator:", "speaker_hint": "judecată, opțiuni, recomandare — aici",
        "kata_hint": "Fișă de exercițiu: 30 de minute, apoi comparați cu pagina completată. "
                     "Cel mult trei rânduri pe celulă, BLUF mai întâi.",
        "legend": "Încredere pe celulă: ridicată = sursă proaspătă și completă · medie = prezentă, fără dată sau "
                  "mai veche de 30 de zile · scăzută = cu lacune · lipsește = fără registru. Cifrele vin din "
                  "calea datelor; coloana 3 spune doar unde trebuie decis.",
        "sources": "Surse", "units": "{n} unități",
        "footer": "SituationReport · raport de situație pe o pagină (P6) · determinist, fără AI",
        "f_items": "{items} elemente · {completed} finalizate · {open} deschise (WIP)",
        "f_ct": "CT mediană {median} z · P85 {p85} z · {pct} % în {target} z",
        "f_flow": "{n} probleme de flux deschise · {survived} de ≥ 3 conferințe · {cross} cross-VS",
        "f_delta_tp": "debit {delta:+d} finalizate în {days} zile",
        "f_delta_ct": "CT mediană {old} → {new} z",
        "f_delta_fp": "probleme de flux: {added} noi · {changed} schimbări de stare",
        "f_decide": "probleme de flux după a treia conferință: {names}",
        "qu_dora": "DORA {n} unități: {tiers}", "qu_slo": "SLO {n} servicii · {breached} încălcate · {risk} în risc",
        "qu_nfr": "NFR {n} · {violated} încălcate · lacune runway {gaps}",
        "qu_delta_slo": "tranziții SLO: {changed} ({worse} înrăutățiri)",
        "qu_delta_nfr": "NFR/runway: {changed} schimbări · {overdue} nou întârziate",
        "qu_decide_slo": "SLO încălcat: {names}", "qu_decide_nfr": "NFR încălcat: {names}",
        "qu_decide_runway": "lacună runway întârziată: {names}",
        "v_caps": "capabilități {n}: {counts}", "v_themes": "teme {n} · {forgotten} fără epic",
        "v_epics": "epics {n} ({counts}) · {zombies} fără temă",
        "v_delta_caps": "capabilități: {changed} schimbări de sănătate ({worse} mai rău)",
        "v_delta_epics": "roadmap: {added} epics noi · {changed} modificate",
        "v_decide_caps": "capabilitate critică: {names}", "v_decide_themes": "temă fără epic: {names}",
        "v_decide_zombies": "epic fără temă: {names}",
        "v_decide_assumptions": "ipoteză peste data de revizuire: {names}",
        "d_pressure": "presiune cross-VS {value} · prag {threshold}", "d_pressure_none": "presiune cross-VS {value} · niciun prag convenit",
        "d_pressure_na": "presiune cross-VS neaplicabilă (o singură soluție)",
        "d_deps": "{n} dependențe · {blocked} blocate · {risk} în risc · {overdue} întârziate",
        "d_risks": "ROAM {n} · {owned} owned · {unmitigated} fără atenuare",
        "d_delta_deps": "dependențe: {changed} schimbări · {overdue} nou întârziate",
        "d_delta_risks": "riscuri: {added} noi · {changed} schimbări ROAM",
        "d_decide_wecker": "alarmă: presiune {value} ≥ prag {threshold} — convocăm conferința value stream?",
        "d_decide_overdue": "dependență întârziată: {names}",
        "b_wecker": "presiune cross-VS {value} peste pragul {threshold}",
        "b_survived": "{n} problemă/probleme de flux supraviețuiesc a treia conferință",
        "b_slo": "{n} SLO încălcate", "b_nfr": "{n} NFR încălcate", "b_caps": "{n} capabilitate critică",
        "b_overdue": "{n} dependențe întârziate",
        "b_calm": "situație în limitele pragurilor convenite",
        "b_tail": "{items} elemente, CT mediană {median} z",
    },
    "pt": {
        "title": "Briefing de situação — uma página", "kata_title": "Briefing de situação — folha de exercício (kata)",
        "bluf": "BLUF", "meta": "{name} · estado em {today} · janela {frm} – {to}",
        "meta_prev": "comparado com {prev}", "meta_noprev": "sem estado anterior",
        "meta_conf": "conferência a {date}",
        "q1": "Onde estamos?", "q2": "O que mudou?", "q3": "O que se segue?",
        "flow": "Fluxo", "quality": "Qualidade", "value": "Valor", "dependencies": "Dependências",
        "conf_high": "alta", "conf_medium": "média", "conf_low": "baixa", "conf_none": "em falta",
        "no_data": "nenhum registo ligado", "no_prev": "sem estado anterior — coluna vazia",
        "no_decision": "nenhum ponto de decisão atingido", "decide": "Decisão necessária:",
        "speaker": "Apresentador(a):", "speaker_hint": "juízo, opções, recomendação — aqui",
        "kata_hint": "Folha de exercício: 30 minutos, depois comparar com a página preenchida. "
                     "No máximo três linhas por célula, BLUF primeiro.",
        "legend": "Confiança por célula: alta = fonte fresca e completa · média = presente, sem data ou com "
                  "mais de 30 dias · baixa = com lacunas · em falta = sem registo. Os números vêm do caminho "
                  "de dados; a coluna 3 só diz onde é preciso decidir.",
        "sources": "Fontes", "units": "{n} unidades",
        "footer": "SituationReport · briefing de situação numa página (P6) · determinístico, sem IA",
        "f_items": "{items} itens · {completed} concluídos · {open} abertos (WIP)",
        "f_ct": "CT mediana {median} d · P85 {p85} d · {pct} % dentro de {target} d",
        "f_flow": "{n} problemas de fluxo abertos · {survived} há ≥ 3 conferências · {cross} cross-VS",
        "f_delta_tp": "débito {delta:+d} concluídos em {days} dias",
        "f_delta_ct": "CT mediana {old} → {new} d",
        "f_delta_fp": "problemas de fluxo: {added} novos · {changed} mudanças de estado",
        "f_decide": "problemas de fluxo após a terceira conferência: {names}",
        "qu_dora": "DORA {n} unidades: {tiers}", "qu_slo": "SLO {n} serviços · {breached} violados · {risk} em risco",
        "qu_nfr": "NFR {n} · {violated} violados · lacunas de runway {gaps}",
        "qu_delta_slo": "transições SLO: {changed} ({worse} pioras)",
        "qu_delta_nfr": "NFR/runway: {changed} mudanças · {overdue} recém-atrasados",
        "qu_decide_slo": "SLO violado: {names}", "qu_decide_nfr": "NFR violado: {names}",
        "qu_decide_runway": "lacuna de runway atrasada: {names}",
        "v_caps": "capacidades {n}: {counts}", "v_themes": "temas {n} · {forgotten} sem epic",
        "v_epics": "epics {n} ({counts}) · {zombies} sem tema",
        "v_delta_caps": "capacidades: {changed} mudanças de saúde ({worse} piores)",
        "v_delta_epics": "roadmap: {added} epics novos · {changed} alterados",
        "v_decide_caps": "capacidade crítica: {names}", "v_decide_themes": "tema sem epic: {names}",
        "v_decide_zombies": "epic sem tema: {names}",
        "v_decide_assumptions": "pressuposto além da data de revisão: {names}",
        "d_pressure": "pressão cross-VS {value} · limiar {threshold}", "d_pressure_none": "pressão cross-VS {value} · nenhum limiar acordado",
        "d_pressure_na": "pressão cross-VS não aplicável (uma só solution)",
        "d_deps": "{n} dependências · {blocked} bloqueadas · {risk} em risco · {overdue} atrasadas",
        "d_risks": "ROAM {n} · {owned} owned · {unmitigated} sem mitigação",
        "d_delta_deps": "dependências: {changed} mudanças · {overdue} recém-atrasadas",
        "d_delta_risks": "riscos: {added} novos · {changed} mudanças ROAM",
        "d_decide_wecker": "alerta: pressão {value} ≥ limiar {threshold} — convocar a conferência de value stream?",
        "d_decide_overdue": "dependência atrasada: {names}",
        "b_wecker": "pressão cross-VS {value} acima do limiar {threshold}",
        "b_survived": "{n} problema(s) de fluxo sobrevive(m) à terceira conferência",
        "b_slo": "{n} SLO violados", "b_nfr": "{n} NFR violados", "b_caps": "{n} capacidade crítica",
        "b_overdue": "{n} dependências atrasadas",
        "b_calm": "situação dentro dos limiares acordados",
        "b_tail": "{items} itens, CT mediana {median} d",
    },
    "fr": {
        "title": "Exposé de situation — une page", "kata_title": "Exposé de situation — fiche d'exercice (kata)",
        "bluf": "BLUF", "meta": "{name} · état au {today} · fenêtre {frm} – {to}",
        "meta_prev": "comparé à {prev}", "meta_noprev": "pas d'état antérieur",
        "meta_conf": "conférence le {date}",
        "q1": "Où en sommes-nous ?", "q2": "Qu'est-ce qui a changé ?", "q3": "Qu'en découle-t-il ?",
        "flow": "Flux", "quality": "Qualité", "value": "Valeur", "dependencies": "Dépendances",
        "conf_high": "élevée", "conf_medium": "moyenne", "conf_low": "faible", "conf_none": "absente",
        "no_data": "aucun registre connecté", "no_prev": "pas d'état antérieur — colonne vide",
        "no_decision": "aucun point de décision atteint", "decide": "Décision requise :",
        "speaker": "Présentateur :", "speaker_hint": "jugement, options, recommandation — ici",
        "kata_hint": "Fiche d'exercice : 30 minutes, puis comparer avec la page remplie. "
                     "Au plus trois lignes par cellule, BLUF d'abord.",
        "legend": "Confiance par cellule : élevée = source fraîche et complète · moyenne = présente, sans date ou "
                  "de plus de 30 jours · faible = lacunaire · absente = pas de registre. Les chiffres viennent du "
                  "chemin de données ; la colonne 3 dit seulement où décider.",
        "sources": "Sources", "units": "{n} unités",
        "footer": "SituationReport · exposé de situation sur une page (P6) · déterministe, sans IA",
        "f_items": "{items} éléments · {completed} terminés · {open} ouverts (WIP)",
        "f_ct": "CT médiane {median} j · P85 {p85} j · {pct} % sous {target} j",
        "f_flow": "{n} problèmes de flux ouverts · {survived} depuis ≥ 3 conférences · {cross} cross-VS",
        "f_delta_tp": "débit {delta:+d} terminés en {days} jours",
        "f_delta_ct": "CT médiane {old} → {new} j",
        "f_delta_fp": "problèmes de flux : {added} nouveaux · {changed} changements d'état",
        "f_decide": "problèmes de flux au-delà de la troisième conférence : {names}",
        "qu_dora": "DORA {n} unités : {tiers}", "qu_slo": "SLO {n} services · {breached} violés · {risk} à risque",
        "qu_nfr": "NFR {n} · {violated} violés · lacunes runway {gaps}",
        "qu_delta_slo": "transitions SLO : {changed} ({worse} dégradations)",
        "qu_delta_nfr": "NFR/runway : {changed} changements · {overdue} nouvellement en retard",
        "qu_decide_slo": "SLO violé : {names}", "qu_decide_nfr": "NFR violé : {names}",
        "qu_decide_runway": "lacune runway en retard : {names}",
        "v_caps": "capacités {n} : {counts}", "v_themes": "thèmes {n} · {forgotten} sans epic",
        "v_epics": "epics {n} ({counts}) · {zombies} sans thème",
        "v_delta_caps": "capacités : {changed} changements de santé ({worse} pires)",
        "v_delta_epics": "roadmap : {added} epics nouveaux · {changed} modifiés",
        "v_decide_caps": "capacité critique : {names}", "v_decide_themes": "thème sans epic : {names}",
        "v_decide_zombies": "epic sans thème : {names}",
        "v_decide_assumptions": "hypothèse au-delà de la date de revue : {names}",
        "d_pressure": "pression cross-VS {value} · seuil {threshold}", "d_pressure_none": "pression cross-VS {value} · aucun seuil convenu",
        "d_pressure_na": "pression cross-VS non applicable (une seule solution)",
        "d_deps": "{n} dépendances · {blocked} bloquées · {risk} à risque · {overdue} en retard",
        "d_risks": "ROAM {n} · {owned} owned · {unmitigated} sans atténuation",
        "d_delta_deps": "dépendances : {changed} changements · {overdue} nouvellement en retard",
        "d_delta_risks": "risques : {added} nouveaux · {changed} changements ROAM",
        "d_decide_wecker": "réveil : pression {value} ≥ seuil {threshold} — convoquer la conférence value stream ?",
        "d_decide_overdue": "dépendance en retard : {names}",
        "b_wecker": "pression cross-VS {value} au-dessus du seuil {threshold}",
        "b_survived": "{n} problème(s) de flux survivent à la troisième conférence",
        "b_slo": "{n} SLO violés", "b_nfr": "{n} NFR violés", "b_caps": "{n} capacité critique",
        "b_overdue": "{n} dépendances en retard",
        "b_calm": "situation dans les seuils convenus",
        "b_tail": "{items} éléments, CT médiane {median} j",
    },
}
_DATE_FMT = {"de": "%d.%m.%Y", "ro": "%d.%m.%Y", "pt": "%d/%m/%Y", "fr": "%d/%m/%Y", "en": "%Y-%m-%d"}
_CONF_COLOURS = {CONFIDENCE_HIGH: "#d9efd9", CONFIDENCE_MEDIUM: "#fff1c9",
                 CONFIDENCE_LOW: "#f6d5d5", CONF_NONE: "#e6e8eb"}


def _tr(lang: str, key: str, **kw: Any) -> str:
    text = _T.get(lang, _T["en"]).get(key) or _T["en"][key]
    return text.format(**kw) if kw else text


def _fmt_date(d: date | None, lang: str) -> str:
    return d.strftime(_DATE_FMT.get(lang, "%Y-%m-%d")) if d else "–"


def _num(value: float | None) -> str:
    return "–" if value is None else (f"{value:.1f}" if isinstance(value, float) else str(value))


def _names(items: list[str]) -> str:
    shown = items[:_MAX_NAMES]
    more = len(items) - len(shown)
    return ", ".join(shown) + (f" (+{more})" if more > 0 else "")


@dataclass
class Cell:
    lines: list[str] = field(default_factory=list)
    confidence: str = CONF_NONE
    decide: list[str] = field(default_factory=list)   # column 3 only


@dataclass
class OnePager:
    name: str
    kind: str
    today: date
    window_from: date | None
    window_to: date | None
    prev_as_of: date | None
    conference_date: date | None
    units: int
    bluf: str
    cells: dict[str, dict[str, Cell]]
    sources: list[str]


# ---------------------------------------------------------------------------
# Konfidenz
# ---------------------------------------------------------------------------

def _age_conf(dates: list[date | None], reference: date, present: bool) -> str:
    """Register confidence: fresh dated → high, undated/old → medium, absent → none."""
    if not present:
        return CONF_NONE
    known = [d for d in dates if d is not None]
    if not known:
        return CONFIDENCE_MEDIUM
    newest = max(known)
    return CONFIDENCE_HIGH if (reference - newest).days <= _FRESH_DAYS else CONFIDENCE_MEDIUM


def _parse_day(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _worst(confs: list[str]) -> str:
    order = (CONF_NONE, CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH)
    return min(confs, key=order.index) if confs else CONF_NONE


# ---------------------------------------------------------------------------
# Bau
# ---------------------------------------------------------------------------

@dataclass
class _Ctx:
    """What every dimension builder needs (keeps the builders flat)."""
    config: SolutionConfig
    lang: str
    today: date
    delta: Any
    quiet: Callable[[str], None]
    cells: dict[str, dict[str, Cell]]
    sources: list[str]
    bluf_parts: list[str]

    def section(self, name: str) -> Any:
        return self.delta.governance.get(name) if self.delta else None


def _collectors() -> Any:
    """The report's collectors, imported late (aggregator pulls plotly)."""
    from . import aggregator
    return aggregator


def _dim_flow(ctx: _Ctx, total: Any, qualities: list, units: int, target_ct: int) -> None:
    config, lang, delta = ctx.config, ctx.lang, ctx.delta
    quiet, cells, sources, bluf_parts = ctx.quiet, ctx.cells, ctx.sources, ctx.bluf_parts
    section = ctx.section
    agg = _collectors()
    # Flow ---------------------------------------------------------------
    flow = [p for _, p in agg._collect_flow_problems(config, log=quiet)]
    open_flow = [p for p in flow if p.status in ("open", "committed")]
    survived = [p for p in flow if p.survived]
    cross = [p for p in open_flow if p.cross_vs]
    c = cells["flow"]
    c["q1"].lines = [
        _tr(lang, "f_items", items=total.items, completed=total.completed, open=total.open_items),
        _tr(lang, "f_ct", median=_num(total.median_ct), p85=_num(total.p85_ct),
            pct=_num(total.target_ct_pct), target=target_ct),
    ]
    if flow:
        c["q1"].lines.append(_tr(lang, "f_flow", n=len(open_flow), survived=len(survived),
                                 cross=len(cross)))
    src_conf = _worst([q.confidence for q in qualities]) if qualities else CONF_NONE
    c["q1"].confidence = src_conf
    if delta:
        c["q2"].lines.append(_tr(lang, "f_delta_tp", delta=delta.completed_delta,
                                 days=delta.period_days))
        if delta.total and "median_ct" in delta.total.fields:
            old, new = delta.total.fields["median_ct"]
            c["q2"].lines.append(_tr(lang, "f_delta_ct", old=_num(old), new=_num(new)))
        fp = section("flow_problems")
        if fp and not fp.empty:
            c["q2"].lines.append(_tr(lang, "f_delta_fp", added=len(fp.added), changed=len(fp.changed)))
        c["q2"].confidence = src_conf
    if survived:
        c["q3"].decide.append(_tr(lang, "f_decide", names=_names([p.title for p in survived])))
        bluf_parts.append(_tr(lang, "b_survived", n=len(survived)))
    c["q3"].confidence = src_conf
    sources.append(f"{config.name}: {units} × IssueTimes" + (", flow_problems" if flow else ""))



def _dim_quality(ctx: _Ctx) -> None:
    config, lang, today, delta = ctx.config, ctx.lang, ctx.today, ctx.delta
    quiet, cells, sources, bluf_parts = ctx.quiet, ctx.cells, ctx.sources, ctx.bluf_parts
    section = ctx.section
    agg = _collectors()
    # Quality ------------------------------------------------------------
    dora, quality = agg._collect_delivery(config, log=quiet)
    slos = [s for _, s in agg._collect_slo(config, log=quiet)]
    nfrs, runway = agg._collect_nfr(config, log=quiet)
    c = cells["quality"]
    if dora:
        tiers = Counter(unit_tier(r) for _, r in dora)
        c["q1"].lines.append(_tr(lang, "qu_dora", n=len(dora),
                                 tiers=", ".join(f"{k} {v}" for k, v in sorted(tiers.items()))))
    if slos:
        statuses = [slo_status(s) for s in slos]
        c["q1"].lines.append(_tr(lang, "qu_slo", n=len(slos), breached=statuses.count(SLO_BREACHED),
                                 risk=statuses.count(SLO_AT_RISK)))
    if nfrs or runway:
        c["q1"].lines.append(_tr(lang, "qu_nfr", n=len(nfrs),
                                 violated=sum(1 for _, n in nfrs if n.status == STATUS_VIOLATED),
                                 gaps=sum(1 for _, r in runway if r.status == RUNWAY_GAP)))
    q_dates = [_parse_day(r.fetched_at) for _, r in dora] + [_parse_day(s.fetched_at) for s in slos]
    c["q1"].confidence = _age_conf(q_dates, today, bool(dora or slos or nfrs or runway))
    if delta:
        slo_d, nfr_d, run_d = section("slo"), section("nfr"), section("runway")
        if slo_d and not slo_d.empty:
            c["q2"].lines.append(_tr(lang, "qu_delta_slo", changed=len(slo_d.changed),
                                     worse=sum(1 for ch in slo_d.changed if ch.worsened)))
        changed = (len(nfr_d.changed) if nfr_d else 0) + (len(run_d.changed) if run_d else 0)
        overdue = len(run_d.newly_overdue) if run_d else 0
        if changed or overdue:
            c["q2"].lines.append(_tr(lang, "qu_delta_nfr", changed=changed, overdue=overdue))
        c["q2"].confidence = c["q1"].confidence
    breached = [s.service for s in slos if slo_status(s) == SLO_BREACHED]
    violated = [n.title for _, n in nfrs if n.status == STATUS_VIOLATED]
    gaps_overdue = [r.title for _, r in runway
                    if r.status == RUNWAY_GAP and r.needed_by and r.needed_by < today]
    if breached:
        c["q3"].decide.append(_tr(lang, "qu_decide_slo", names=_names(breached)))
        bluf_parts.append(_tr(lang, "b_slo", n=len(breached)))
    if violated:
        c["q3"].decide.append(_tr(lang, "qu_decide_nfr", names=_names(violated)))
        bluf_parts.append(_tr(lang, "b_nfr", n=len(violated)))
    if gaps_overdue:
        c["q3"].decide.append(_tr(lang, "qu_decide_runway", names=_names(gaps_overdue)))
    c["q3"].confidence = c["q1"].confidence
    sources.append("dora, slo, nfr: " + ", ".join(
        n for n, present in (("dora", bool(dora)), ("slo", bool(slos)), ("nfr", bool(nfrs or runway)))
        if present) or "dora, slo, nfr: –")



def _dim_value(ctx: _Ctx) -> None:
    config, lang, today, delta = ctx.config, ctx.lang, ctx.today, ctx.delta
    quiet, cells, sources, bluf_parts = ctx.quiet, ctx.cells, ctx.sources, ctx.bluf_parts
    section = ctx.section
    agg = _collectors()
    # Value --------------------------------------------------------------
    caps = [cp for _, cp in agg._collect_capabilities(config, log=quiet)]
    themes, epics = agg._collect_themes(config, log=quiet)
    theme_list = [th for _, th in themes]
    epic_list = [e for _, e in epics]
    decisions = [e for _, e in agg._collect_decisions(config, log=quiet)]
    c = cells["value"]
    if caps:
        counts = Counter(cp.health for cp in caps)
        c["q1"].lines.append(_tr(lang, "v_caps", n=len(caps),
                                 counts=", ".join(f"{k} {v}" for k, v in sorted(counts.items()))))
    used = {e.theme for e in epic_list if e.theme}
    forgotten = [th.title for th in theme_list if th.theme_id not in used]
    zombies = [e.title for e in epic_list if not e.theme]
    if theme_list:
        c["q1"].lines.append(_tr(lang, "v_themes", n=len(theme_list), forgotten=len(forgotten)))
    if epic_list:
        ec = Counter(e.status for e in epic_list)
        c["q1"].lines.append(_tr(lang, "v_epics", n=len(epic_list),
                                 counts=", ".join(f"{k} {v}" for k, v in sorted(ec.items())),
                                 zombies=len(zombies)))
    c["q1"].confidence = _age_conf([], today, bool(caps or theme_list or epic_list))
    if delta:
        cap_d, epic_d = section("capabilities"), section("epics")
        if cap_d and not cap_d.empty:
            c["q2"].lines.append(_tr(lang, "v_delta_caps", changed=len(cap_d.changed),
                                     worse=sum(1 for ch in cap_d.changed if ch.worsened)))
        if epic_d and not epic_d.empty:
            c["q2"].lines.append(_tr(lang, "v_delta_epics", added=len(epic_d.added),
                                     changed=len(epic_d.changed)))
        c["q2"].confidence = c["q1"].confidence
    critical = [cp.title for cp in caps if cp.health == HEALTH_CRITICAL]
    expired = [d.title for d in decisions if d.kind == KIND_ASSUMPTION and d.status == ASSUMPTION_OPEN
               and d.review_by and d.review_by < today]
    if critical:
        c["q3"].decide.append(_tr(lang, "v_decide_caps", names=_names(critical)))
        bluf_parts.append(_tr(lang, "b_caps", n=len(critical)))
    if forgotten:
        c["q3"].decide.append(_tr(lang, "v_decide_themes", names=_names(forgotten)))
    if zombies:
        c["q3"].decide.append(_tr(lang, "v_decide_zombies", names=_names(zombies)))
    if expired:
        c["q3"].decide.append(_tr(lang, "v_decide_assumptions", names=_names(expired)))
    c["q3"].confidence = c["q1"].confidence
    sources.append("capabilities, themes, decisions: " + (", ".join(
        n for n, present in (("capabilities", bool(caps)), ("themes", bool(theme_list or epic_list)),
                             ("decisions", bool(decisions))) if present) or "–"))



def _dim_dependencies(ctx: _Ctx) -> None:
    config, lang, today, delta = ctx.config, ctx.lang, ctx.today, ctx.delta
    quiet, cells, sources, bluf_parts = ctx.quiet, ctx.cells, ctx.sources, ctx.bluf_parts
    section = ctx.section
    agg = _collectors()
    # Dependencies -------------------------------------------------------
    deps = [d for _, d in agg._collect_dependencies(config, log=quiet)]
    risks = [r for _, r in agg._collect_risks(config, log=quiet)]
    pressure = agg._collect_dependency_pressure(config, log=quiet)
    c = cells["dependencies"]
    if not pressure.applicable:
        c["q1"].lines.append(_tr(lang, "d_pressure_na"))
    elif pressure.threshold is None:
        c["q1"].lines.append(_tr(lang, "d_pressure_none", value=pressure.value))
    else:
        c["q1"].lines.append(_tr(lang, "d_pressure", value=pressure.value, threshold=pressure.threshold))
    overdue_deps = [d for d in deps if d.status != DEP_DONE and d.due and d.due < today]
    if deps:
        c["q1"].lines.append(_tr(lang, "d_deps", n=len(deps),
                                 blocked=sum(1 for d in deps if d.status == DEP_BLOCKED),
                                 risk=sum(1 for d in deps if d.status == DEP_AT_RISK),
                                 overdue=len(overdue_deps)))
    if risks:
        c["q1"].lines.append(_tr(lang, "d_risks", n=len(risks),
                                 owned=sum(1 for r in risks if r.roam == "owned"),
                                 unmitigated=sum(1 for r in risks if r.roam in ("owned", "accepted"))))
    c["q1"].confidence = _age_conf([r.status_since for r in risks], today, bool(deps or risks))
    if delta:
        dep_d, risk_d = section("dependencies"), section("risks")
        if dep_d and not dep_d.empty:
            c["q2"].lines.append(_tr(lang, "d_delta_deps", changed=len(dep_d.changed),
                                     overdue=len(dep_d.newly_overdue)))
        if risk_d and not risk_d.empty:
            c["q2"].lines.append(_tr(lang, "d_delta_risks", added=len(risk_d.added),
                                     changed=len(risk_d.changed)))
        c["q2"].confidence = c["q1"].confidence
    if pressure.triggered:
        c["q3"].decide.append(_tr(lang, "d_decide_wecker", value=pressure.value,
                                  threshold=pressure.threshold))
        bluf_parts.insert(0, _tr(lang, "b_wecker", value=pressure.value, threshold=pressure.threshold))
    if overdue_deps:
        c["q3"].decide.append(_tr(lang, "d_decide_overdue",
                                  names=_names([d.title for d in overdue_deps])))
        bluf_parts.append(_tr(lang, "b_overdue", n=len(overdue_deps)))
    c["q3"].confidence = c["q1"].confidence
    sources.append("dependencies, risks: " + (", ".join(
        n for n, present in (("dependencies", bool(deps)), ("risks", bool(risks))) if present) or "–"))



def build_onepager(
    config: SolutionConfig,
    lang: str = DEFAULT_LANG,
    prev_snapshot: Any = None,
    reference: date | None = None,
    target_ct: int = 90,
    log: Callable[[str], None] = print,
) -> OnePager:
    """
    Gather the four dimensions from the registers the report already uses.

    ``prev_snapshot`` (a loaded Snapshot) fills column 2 via the delta
    briefing; without it the column says so. Nothing here judges: column 3
    lists decision points the agreed rules define, no recommendation.
    """
    from .delta import compute_delta
    from .snapshot import build_snapshot
    from .summary import SourceQuality, compute_summary

    lang = lang if lang in _T else "en"
    today = reference or date.today()
    quiet: Callable[[str], None] = lambda m: None  # noqa: E731
    qualities: list[SourceQuality] = []
    agg = _collectors()
    pooled = agg.build_pooled_report_data(config, log=quiet, quality_sink=qualities)
    units = agg.load_comparison_units(config, log=quiet)
    total = compute_summary(pooled, config.name, target_ct)
    delta = None
    if prev_snapshot is not None:
        now_snap = build_snapshot(config, as_of=today, target_ct=target_ct, log=quiet)
        delta = compute_delta(prev_snapshot, now_snap)

    ctx = _Ctx(config=config, lang=lang, today=today, delta=delta, quiet=quiet,
               cells={d: {q: Cell() for q in QUESTIONS} for d in DIMENSIONS},
               sources=[], bluf_parts=[])
    _dim_flow(ctx, total, qualities, len(units), target_ct)
    _dim_quality(ctx)
    _dim_value(ctx)
    _dim_dependencies(ctx)
    cells, sources, bluf_parts = ctx.cells, ctx.sources, ctx.bluf_parts

    # ---- BLUF ---------------------------------------------------------------
    if bluf_parts:
        bluf = "; ".join(bluf_parts[:2]) + "."
    else:
        bluf = (_tr(lang, "b_calm") + " — "
                + _tr(lang, "b_tail", items=total.items, median=_num(total.median_ct)) + ".")

    return OnePager(
        name=config.name, kind=config.kind, today=today,
        window_from=config.from_date, window_to=config.to_date,
        prev_as_of=(prev_snapshot.as_of if prev_snapshot is not None else None),
        conference_date=config.conference_date, units=len(units), bluf=bluf,
        cells=cells, sources=sources)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_CSS = """
@page{size:A4 landscape;margin:12mm}
body{font-family:"Segoe UI",Calibri,Arial,sans-serif;font-size:12.5px;color:#23303e;margin:18px auto;max-width:1120px;line-height:1.4}
h1{color:#16304d;font-size:20px;margin:0 0 2px}.meta{color:#5b6b7c;font-size:12px;margin:0 0 10px}
.bluf{background:#eef3f8;border-left:5px solid #9a3412;padding:8px 12px;margin:0 0 12px;font-size:15px;font-weight:600;color:#16304d}
.bluf .k{color:#9a3412;margin-right:8px}
table{border-collapse:collapse;width:100%;table-layout:fixed}
th{background:#16304d;color:#fff;text-align:left;padding:6px 8px;font-size:12.5px}
th.dim{width:13%}td{border:1px solid #d9dfe6;padding:6px 8px;vertical-align:top;height:108px}
td.dim{font-weight:700;color:#16304d;background:#f4f7fb}
ul{margin:0;padding-left:16px}li{margin:0 0 2px}
.badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:11px;border:1px solid #c9d2dc;margin-bottom:4px}
.decide{color:#9a3412;font-weight:600}.empty{color:#5b6b7c;font-style:italic}
.speaker{border-top:1px dashed #c9d2dc;margin-top:6px;padding-top:4px;color:#5b6b7c;font-size:11px;min-height:28px}
.kata td{height:150px}.kata .line{border-bottom:1px dotted #9aa5b1;height:18px}
.legend{color:#5b6b7c;font-size:11px;margin-top:10px}footer{color:#5b6b7c;font-size:11px;margin-top:8px;border-top:1px solid #d9dfe6;padding-top:6px}
"""


def _badge(conf: str, lang: str) -> str:
    return (f'<span class="badge" style="background:{_CONF_COLOURS.get(conf, "#e6e8eb")}">'
            f'{_html.escape(_tr(lang, "conf_" + conf))}</span>')


def _cell_html(cell: Cell, question: str, lang: str, has_prev: bool) -> str:
    esc = _html.escape
    parts = [_badge(cell.confidence, lang)]
    if question == "q3":
        if cell.decide:
            parts.append(f'<div class="decide">{esc(_tr(lang, "decide"))}</div><ul>'
                         + "".join(f"<li>{esc(line)}</li>" for line in cell.decide) + "</ul>")
        else:
            parts.append(f'<div class="empty">{esc(_tr(lang, "no_decision"))}</div>')
        parts.append(f'<div class="speaker">{esc(_tr(lang, "speaker"))} '
                     f'<span class="empty">{esc(_tr(lang, "speaker_hint"))}</span></div>')
        return "".join(parts)
    if question == "q2" and not has_prev:
        parts.append(f'<div class="empty">{esc(_tr(lang, "no_prev"))}</div>')
        return "".join(parts)
    if cell.lines:
        parts.append("<ul>" + "".join(f"<li>{esc(line)}</li>" for line in cell.lines) + "</ul>")
    else:
        parts.append(f'<div class="empty">{esc(_tr(lang, "no_data"))}</div>')
    return "".join(parts)


def _kata_cell(question: str, lang: str) -> str:
    lines = '<div class="line"></div>' * 4
    hint = _tr(lang, "speaker_hint") if question == "q3" else _tr(lang, question)
    return f'<div class="empty">{_html.escape(hint)}</div>{lines}'


def render_onepager_html(op: OnePager, lang: str = DEFAULT_LANG, kata: bool = False) -> str:
    """One self-contained page; ``kata`` renders the empty practice sheet."""
    lang = lang if lang in _T else "en"
    esc = _html.escape
    has_prev = op.prev_as_of is not None
    meta = _tr(lang, "meta", name=op.name, today=_fmt_date(op.today, lang),
               frm=_fmt_date(op.window_from, lang), to=_fmt_date(op.window_to, lang))
    meta += " · " + (_tr(lang, "meta_prev", prev=_fmt_date(op.prev_as_of, lang)) if has_prev
                     else _tr(lang, "meta_noprev"))
    if op.conference_date:
        meta += " · " + _tr(lang, "meta_conf", date=_fmt_date(op.conference_date, lang))
    meta += " · " + _tr(lang, "units", n=op.units)
    head = "".join(f"<th>{esc(_tr(lang, q))}</th>" for q in QUESTIONS)
    rows = []
    for dim in DIMENSIONS:
        tds = "".join(
            f"<td>{_kata_cell(q, lang) if kata else _cell_html(op.cells[dim][q], q, lang, has_prev)}</td>"
            for q in QUESTIONS)
        rows.append(f'<tr><td class="dim">{esc(_tr(lang, dim))}</td>{tds}</tr>')
    title = _tr(lang, "kata_title" if kata else "title")
    body_cls = ' class="kata"' if kata else ""
    bluf = (f'<div class="bluf"><span class="k">{esc(_tr(lang, "bluf"))}</span>'
            + (f'<span class="empty">{esc(_tr(lang, "kata_hint"))}</span>' if kata else esc(op.bluf))
            + "</div>")
    sources = "" if kata else (f'<div class="legend">{esc(_tr(lang, "sources"))}: '
                               + " · ".join(esc(s) for s in op.sources) + "</div>")
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{esc(title)}</title>'
        f"<style>{_CSS}</style></head><body{body_cls}>"
        f"<h1>{esc(title)}</h1><p class=\"meta\">{esc(meta)}</p>{bluf}"
        f'<table><tr><th class="dim"></th>{head}</tr>{"".join(rows)}</table>'
        f'<div class="legend">{esc(_tr(lang, "legend"))}</div>{sources}'
        f"<footer>{esc(_tr(lang, 'footer'))}</footer></body></html>"
    )
