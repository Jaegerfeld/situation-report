# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Textkatalog des Testdaten-Generators in den fünf Sprachen der Suite
#   (Entscheidung Robert 30.10.2026: „konsequent mehrsprachig"). Hier
#   stehen alle Texte, die in den Datenraum und auf die Konsole gehen —
#   Geschichte (Vorlagen, Ereignisse, Zusammenfassungen, Hinweise), README,
#   Fortschritt und Protokoll, Übungsdateien der KI-Entwürfe, Kommandozeile.
#   Die Oberflächentexte der zwei Oberflächen liegen in `web/texts.py`.
#
#   Zugriff über ``t(key, lang, **kw)``: unbekannter Schlüssel ist ein
#   Programmierfehler (KeyError); unbekannte Sprache fällt auf Englisch
#   zurück. Ein Test prüft, dass jeder Schlüssel alle fünf Sprachen trägt und
#   die Platzhalter übereinstimmen.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

from build_reports.chart_texts import (
    DEFAULT_LANG,
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    LANGUAGES,
)

__all__ = ["DEFAULT_LANG", "LANGUAGES", "keys", "load_lang_pref", "normalise", "step_label",
           "t", "template_title"]

_T: dict[str, dict[str, str]] = {
    # --- story: template titles -------------------------------------------------
    "tpl.calm": {LANG_DE: "Ruhig", LANG_EN: "Calm", LANG_RO: "Calm", LANG_PT: "Calmo", LANG_FR: "Calme"},
    "tpl.standard": {LANG_DE: "Standard-Lage", LANG_EN: "Standard situation", LANG_RO: "Situație standard",
                     LANG_PT: "Situação padrão", LANG_FR: "Situation standard"},
    "tpl.escalation": {LANG_DE: "Eskalation", LANG_EN: "Escalation", LANG_RO: "Escaladare",
                       LANG_PT: "Escalada", LANG_FR: "Escalade"},
    "tpl.recovery": {LANG_DE: "Erholung", LANG_EN: "Recovery", LANG_RO: "Recuperare",
                     LANG_PT: "Recuperação", LANG_FR: "Reprise"},
    # --- story: events ------------------------------------------------------------
    "ev.E1.title": {
        LANG_DE: "{art} ist der Ausreißer (Cycle Time etwa 3×).",
        LANG_EN: "{art} is the outlier (cycle time about 3×).",
        LANG_RO: "{art} este ART-ul atipic (cycle time de circa 3×).",
        LANG_PT: "{art} é o ART atípico (cycle time cerca de 3×).",
        LANG_FR: "{art} est l'ART atypique (cycle time environ 3×).",
    },
    "ev.E1.effect": {
        LANG_DE: "Comparison-Report: Median/P95 rot markiert; Wecker DP-{ht}1 (P85 über 30 Tagen) ausgelöst; "
                 "Delivery-Bild selten und langsam; Capability {ht}C-2 at risk.",
        LANG_EN: "Comparison report: median/P95 marked red; alarm DP-{ht}1 (P85 above 30 days) triggered; "
                 "delivery picture rare and slow; capability {ht}C-2 at risk.",
        LANG_RO: "Raport comparativ: mediana/P95 marcate cu roșu; alarma DP-{ht}1 (P85 peste 30 de zile) declanșată; "
                 "imaginea de livrare rară și lentă; capabilitatea {ht}C-2 în risc.",
        LANG_PT: "Relatório comparativo: mediana/P95 a vermelho; alarme DP-{ht}1 (P85 acima de 30 dias) disparado; "
                 "imagem de entrega rara e lenta; capacidade {ht}C-2 em risco.",
        LANG_FR: "Rapport comparatif : médiane/P95 en rouge ; alarme DP-{ht}1 (P85 au-dessus de 30 jours) déclenchée ; "
                 "image de livraison rare et lente ; capacité {ht}C-2 à risque.",
    },
    "ev.E2.title": {
        LANG_DE: "{art} liefert schwache Daten (kein CFD, kaum First Dates, Datenstand 60 Tage alt).",
        LANG_EN: "{art} delivers weak data (no CFD, few first dates, data 60 days old).",
        LANG_RO: "{art} livrează date slabe (fără CFD, puține first dates, date vechi de 60 de zile).",
        LANG_PT: "{art} entrega dados fracos (sem CFD, poucas first dates, dados com 60 dias).",
        LANG_FR: "{art} livre des données faibles (pas de CFD, peu de first dates, données vieilles de 60 jours).",
    },
    "ev.E2.effect": {
        LANG_DE: "Konfidenz medium; Risiko {st}R-1 altert (50 Tage); Capability {st}C-1 kritisch; Flussproblem FP-{st}1 "
                 "überlebt vier Konferenzen; Annahme AS-{st}1 überschreitet ihr Prüfdatum; DORA/Qualität low.",
        LANG_EN: "Confidence medium; risk {st}R-1 ages (50 days); capability {st}C-1 critical; flow problem FP-{st}1 "
                 "survives four conferences; assumption AS-{st}1 passes its review date; DORA/quality low.",
        LANG_RO: "Încredere medie; riscul {st}R-1 îmbătrânește (50 de zile); capabilitatea {st}C-1 critică; problema de flux "
                 "FP-{st}1 supraviețuiește la patru conferințe; ipoteza AS-{st}1 depășește data de revizuire; DORA/calitate scăzute.",
        LANG_PT: "Confiança média; risco {st}R-1 envelhece (50 dias); capacidade {st}C-1 crítica; problema de fluxo FP-{st}1 "
                 "sobrevive a quatro conferências; pressuposto AS-{st}1 ultrapassa a data de revisão; DORA/qualidade baixos.",
        LANG_FR: "Confiance moyenne ; risque {st}R-1 vieillit (50 jours) ; capacité {st}C-1 critique ; problème de flux FP-{st}1 "
                 "survit à quatre conférences ; hypothèse AS-{st}1 dépasse sa date de revue ; DORA/qualité faibles.",
    },
    "ev.E3.title": {
        LANG_DE: "{a} → {b} ist blockiert und überfällig.",
        LANG_EN: "{a} → {b} is blocked and overdue.",
        LANG_RO: "{a} → {b} este blocată și restantă.",
        LANG_PT: "{a} → {b} está bloqueada e atrasada.",
        LANG_FR: "{a} → {b} est bloquée et en retard.",
    },
    "ev.E3.effect": {
        LANG_DE: "Abhängigkeit {ht}D-1: at_risk → blocked; Heatmap rot; Wecker DP-{ht}3 (zwei blockierte) unterschwellig.",
        LANG_EN: "Dependency {ht}D-1: at_risk → blocked; heatmap red; alarm DP-{ht}3 (two blocked) below threshold.",
        LANG_RO: "Dependența {ht}D-1: at_risk → blocked; heatmap roșu; alarma DP-{ht}3 (două blocate) sub prag.",
        LANG_PT: "Dependência {ht}D-1: at_risk → blocked; heatmap a vermelho; alarme DP-{ht}3 (duas bloqueadas) abaixo do limiar.",
        LANG_FR: "Dépendance {ht}D-1 : at_risk → blocked ; heatmap rouge ; alarme DP-{ht}3 (deux bloquées) sous le seuil.",
    },
    "ev.E4.title": {
        LANG_DE: "{a} → {b} ist eine Cross-Solution-Naht; der Druck zwischen den Value Streams steigt.",
        LANG_EN: "{a} → {b} is a cross-solution seam; the pressure between the value streams rises.",
        LANG_RO: "{a} → {b} este o cusătură între soluții; presiunea dintre fluxurile de valoare crește.",
        LANG_PT: "{a} → {b} é uma costura entre soluções; a pressão entre os fluxos de valor aumenta.",
        LANG_FR: "{a} → {b} est une couture inter-solutions ; la pression entre les flux de valeur monte.",
    },
    "ev.E4.effect": {
        LANG_DE: "{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — nur im Portfolio-Report sichtbar; "
                 "Grundlage des Entscheidungspunkt-Indikators (P4).",
        LANG_EN: "{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — visible only in the portfolio "
                 "report; the basis of the decision-point indicator (P4).",
        LANG_RO: "{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — vizibile doar în raportul de "
                 "portofoliu; baza indicatorului punctului de decizie (P4).",
        LANG_PT: "{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — visível só no relatório de "
                 "portfólio; base do indicador de ponto de decisão (P4).",
        LANG_FR: "{st}D-1 at_risk, {st}D-3 at_risk → blocked, {ht}D-4 on_track → at_risk — visible seulement dans le rapport "
                 "de portefeuille ; base de l'indicateur de point de décision (P4).",
    },
    "ev.E5.title": {
        LANG_DE: "Die Naht {a} × {b} öffnet zum dritten Mal eine Solution Area zum selben Thema (test environment).",
        LANG_EN: "The seam {a} × {b} opens a solution area on the same topic for the third time (test environment).",
        LANG_RO: "Cusătura {a} × {b} deschide a treia oară o solution area pe aceeași temă (test environment).",
        LANG_PT: "A costura {a} × {b} abre pela terceira vez uma solution area sobre o mesmo tema (test environment).",
        LANG_FR: "La couture {a} × {b} ouvre pour la troisième fois une solution area sur le même sujet (test environment).",
    },
    "ev.E5.effect": {
        LANG_DE: "SA-{ht}1, SA-{ht}2 geschlossen, SA-{ht}3 neu — das EA-Signal (P5): Schnitt oder Architektur prüfen, nicht die Teams.",
        LANG_EN: "SA-{ht}1, SA-{ht}2 closed, SA-{ht}3 new — the EA signal (P5): check the cut or the architecture, not the teams.",
        LANG_RO: "SA-{ht}1, SA-{ht}2 închise, SA-{ht}3 nouă — semnalul EA (P5): verificați tăietura sau arhitectura, nu echipele.",
        LANG_PT: "SA-{ht}1, SA-{ht}2 fechadas, SA-{ht}3 nova — o sinal EA (P5): rever o corte ou a arquitetura, não as equipas.",
        LANG_FR: "SA-{ht}1, SA-{ht}2 fermées, SA-{ht}3 nouvelle — le signal EA (P5) : revoir le découpage ou l'architecture, pas les équipes.",
    },
    "ev.E6.title": {
        LANG_DE: "„Order Sync API“ in Solution {sol} reißt sein SLO.",
        LANG_EN: "\"Order Sync API\" in solution {sol} breaches its SLO.",
        LANG_RO: "„Order Sync API” din soluția {sol} își încalcă SLO-ul.",
        LANG_PT: "«Order Sync API» na solução {sol} viola o seu SLO.",
        LANG_FR: "« Order Sync API » dans la solution {sol} rompt son SLO.",
    },
    "ev.E6.effect": {
        LANG_DE: "SLO-Register: breached; NFR {st}N-1 (API response time) verletzt; Runway-Lücke {st}RW-1 überfällig.",
        LANG_EN: "SLO register: breached; NFR {st}N-1 (API response time) violated; runway gap {st}RW-1 overdue.",
        LANG_RO: "Registrul SLO: breached; NFR {st}N-1 (API response time) încălcat; lacuna de runway {st}RW-1 restantă.",
        LANG_PT: "Registo SLO: breached; NFR {st}N-1 (API response time) violado; lacuna de runway {st}RW-1 atrasada.",
        LANG_FR: "Registre SLO : breached ; NFR {st}N-1 (API response time) violé ; lacune de runway {st}RW-1 en retard.",
    },
    "ev.E7.title": {
        LANG_DE: "Solution {host} wirkt gesund — mit den stillen Mustern.",
        LANG_EN: "Solution {host} looks healthy — with the silent patterns.",
        LANG_RO: "Soluția {host} pare sănătoasă — cu tiparele tăcute.",
        LANG_PT: "A solução {host} parece saudável — com os padrões silenciosos.",
        LANG_FR: "La solution {host} paraît saine — avec les motifs silencieux.",
    },
    "ev.E7.effect": {
        LANG_DE: "Risiko {ht}R-1 seit 45 Tagen owned (Aging); Theme T-{ht}2 ohne Epic („declared & forgotten“); Flussproblem "
                 "FP-{ht}1 überlebt drei Konferenzen; Capability {ht}C-3 ohne ART (uncovered); SLO „Checkout“ at risk.",
        LANG_EN: "Risk {ht}R-1 owned for 45 days (aging); theme T-{ht}2 without an epic (\"declared & forgotten\"); flow problem "
                 "FP-{ht}1 survives three conferences; capability {ht}C-3 without an ART (uncovered); SLO \"Checkout\" at risk.",
        LANG_RO: "Riscul {ht}R-1 owned de 45 de zile (aging); tema T-{ht}2 fără epic („declared & forgotten”); problema de flux "
                 "FP-{ht}1 supraviețuiește la trei conferințe; capabilitatea {ht}C-3 fără ART (uncovered); SLO „Checkout” în risc.",
        LANG_PT: "Risco {ht}R-1 owned há 45 dias (aging); tema T-{ht}2 sem épico («declared & forgotten»); problema de fluxo "
                 "FP-{ht}1 sobrevive a três conferências; capacidade {ht}C-3 sem ART (uncovered); SLO «Checkout» em risco.",
        LANG_FR: "Risque {ht}R-1 owned depuis 45 jours (aging) ; thème T-{ht}2 sans epic (« declared & forgotten ») ; problème de "
                 "flux FP-{ht}1 survit à trois conférences ; capacité {ht}C-3 sans ART (uncovered) ; SLO « Checkout » à risque.",
    },
    "ev.E8.title": {
        LANG_DE: "Die Datenqualität von {art} verfällt weiter.",
        LANG_EN: "The data quality of {art} decays further.",
        LANG_RO: "Calitatea datelor de la {art} se degradează în continuare.",
        LANG_PT: "A qualidade dos dados de {art} continua a degradar-se.",
        LANG_FR: "La qualité des données de {art} continue de se dégrader.",
    },
    "ev.E8.effect": {
        LANG_DE: "Anteil der Vorgänge ohne First Date steigt auf 80 % — Konfidenz medium → low, Abdeckung im Titel sichtbar.",
        LANG_EN: "Share of items without a first date rises to 80 % — confidence medium → low, coverage visible in the title.",
        LANG_RO: "Ponderea elementelor fără first date urcă la 80 % — încredere medie → scăzută, acoperirea vizibilă în titlu.",
        LANG_PT: "A parte de itens sem first date sobe para 80 % — confiança média → baixa, cobertura visível no título.",
        LANG_FR: "La part d'éléments sans first date monte à 80 % — confiance moyenne → faible, couverture visible dans le titre.",
    },
    "ev.E9.title": {
        LANG_DE: "Neues Risiko in Solution {second}: Security-Review nicht terminiert.",
        LANG_EN: "New risk in solution {second}: security review not scheduled.",
        LANG_RO: "Risc nou în soluția {second}: security review neprogramat.",
        LANG_PT: "Novo risco na solução {second}: security review não agendado.",
        LANG_FR: "Nouveau risque dans la solution {second} : security review non planifié.",
    },
    "ev.E9.effect": {
        LANG_DE: "Risiko {st}R-2 (mitigated, hoch) erscheint — im Delta-Briefing als neu.",
        LANG_EN: "Risk {st}R-2 (mitigated, high) appears — new in the delta briefing.",
        LANG_RO: "Riscul {st}R-2 (mitigated, ridicat) apare — nou în Delta-Briefing.",
        LANG_PT: "O risco {st}R-2 (mitigated, alto) aparece — novo no Delta-Briefing.",
        LANG_FR: "Le risque {st}R-2 (mitigated, élevé) apparaît — nouveau dans le Delta-Briefing.",
    },
    "ev.E10.title": {LANG_DE: "Roadmaps aktualisiert.", LANG_EN: "Roadmaps updated.", LANG_RO: "Roadmap-uri actualizate.",
                     LANG_PT: "Roadmaps atualizados.", LANG_FR: "Roadmaps mises à jour."},
    "ev.E10.effect": {
        LANG_DE: "Epic EP-{ht}9 verliert sein Theme (Zombie-Initiative){second_part}",
        LANG_EN: "Epic EP-{ht}9 loses its theme (zombie initiative){second_part}",
        LANG_RO: "Epicul EP-{ht}9 își pierde tema (inițiativă zombie){second_part}",
        LANG_PT: "O épico EP-{ht}9 perde o seu tema (iniciativa zombie){second_part}",
        LANG_FR: "L'epic EP-{ht}9 perd son thème (initiative zombie){second_part}",
    },
    "ev.E10.second": {
        LANG_DE: "; Epic EP-{st}2 wird von P2 nach P1 gezogen.",
        LANG_EN: "; epic EP-{st}2 is pulled from P2 to P1.",
        LANG_RO: "; epicul EP-{st}2 este tras din P2 în P1.",
        LANG_PT: "; o épico EP-{st}2 é puxado de P2 para P1.",
        LANG_FR: " ; l'epic EP-{st}2 est tiré de P2 vers P1.",
    },
    # --- story: summaries ---------------------------------------------------------------
    "sum.calm.1": {
        LANG_DE: "Ein Portfolio ohne Wendungen: alle ARTs liefern gleichmäßig, die Register tragen Grundmenge und gesunde Anker.",
        LANG_EN: "A portfolio without turning points: every ART delivers evenly, the registers hold base population and healthy anchors.",
        LANG_RO: "Un portofoliu fără răsturnări: toate ART-urile livrează uniform, registrele conțin populația de bază și ancore sănătoase.",
        LANG_PT: "Um portfólio sem viragens: todos os ARTs entregam de forma uniforme, os registos têm a população base e âncoras saudáveis.",
        LANG_FR: "Un portefeuille sans retournements : chaque ART livre régulièrement, les registres portent la population de base et des ancres saines.",
    },
    "sum.calm.2": {
        LANG_DE: "Die Reihe zeigt Durchsatz und kleine Bewegungen — die Übung ist, ein Lagebild zu lesen, das nichts Dramatisches sagt.",
        LANG_EN: "The series shows throughput and small movements — the exercise is reading a picture that says nothing dramatic.",
        LANG_RO: "Seria arată debit și mișcări mici — exercițiul este să citești o imagine care nu spune nimic dramatic.",
        LANG_PT: "A série mostra débito e pequenos movimentos — o exercício é ler uma imagem que não diz nada de dramático.",
        LANG_FR: "La série montre du débit et de petits mouvements — l'exercice est de lire une image qui ne dit rien de dramatique.",
    },
    "sum.calm.3": {
        LANG_DE: "Wer hier Alarm schlägt, hat das Bild überlesen.",
        LANG_EN: "Whoever raises an alarm here has misread the picture.",
        LANG_RO: "Cine dă alarma aici a citit greșit imaginea.",
        LANG_PT: "Quem der o alarme aqui leu mal a imagem.",
        LANG_FR: "Qui donne l'alarme ici a mal lu l'image.",
    },
    "sum.standard.1": {
        LANG_DE: "Ein Portfolio, das auf den ersten Blick ruhig wirkt.",
        LANG_EN: "A portfolio that looks calm at first glance.",
        LANG_RO: "Un portofoliu care pare calm la prima vedere.",
        LANG_PT: "Um portfólio que parece calmo à primeira vista.",
        LANG_FR: "Un portefeuille qui paraît calme au premier regard.",
    },
    "sum.standard.2": {
        LANG_DE: "Darunter {outlier}{weak}und Nähte zwischen den Value Streams, die mit dem letzten Stand sichtbar unter Druck geraten.",
        LANG_EN: "Underneath {outlier}{weak}and seams between the value streams that visibly come under pressure with the last stand.",
        LANG_RO: "Dedesubt {outlier}{weak}și cusături între fluxurile de valoare care intră vizibil sub presiune odată cu ultima stare.",
        LANG_PT: "Por baixo {outlier}{weak}e costuras entre os fluxos de valor que ficam visivelmente sob pressão com o último estado.",
        LANG_FR: "Dessous {outlier}{weak}et des coutures entre les flux de valeur qui passent visiblement sous pression au dernier état.",
    },
    "sum.part.outlier": {LANG_DE: "ein Ausreißer-ART ({outlier}), ", LANG_EN: "an outlier ART ({outlier}), ",
                         LANG_RO: "un ART atipic ({outlier}), ", LANG_PT: "um ART atípico ({outlier}), ",
                         LANG_FR: "un ART atypique ({outlier}), "},
    "sum.part.weak": {LANG_DE: "eine schwache Datenquelle ({weak}) ", LANG_EN: "a weak data source ({weak}) ",
                      LANG_RO: "o sursă de date slabă ({weak}) ", LANG_PT: "uma fonte de dados fraca ({weak}) ",
                      LANG_FR: "une source de données faible ({weak}) "},
    "sum.standard.3": {
        LANG_DE: "Die Register erzählen dieselbe Lage aus jeder Richtung — Risiken, Abhängigkeiten, Annahmen, SLOs und Wecker zeigen auf dieselben Stellen.",
        LANG_EN: "The registers tell the same situation from every direction — risks, dependencies, assumptions, SLOs and alarms point at the same places.",
        LANG_RO: "Registrele spun aceeași situație din fiecare direcție — riscuri, dependențe, ipoteze, SLO-uri și alarme arată spre aceleași locuri.",
        LANG_PT: "Os registos contam a mesma situação de todas as direções — riscos, dependências, pressupostos, SLOs e alarmes apontam para os mesmos sítios.",
        LANG_FR: "Les registres racontent la même situation de toutes les directions — risques, dépendances, hypothèses, SLO et alarmes pointent les mêmes endroits.",
    },
    "sum.escalation.1": {
        LANG_DE: "Eine Lage, die sich Stand für Stand verschärft.",
        LANG_EN: "A situation that sharpens stand by stand.",
        LANG_RO: "O situație care se agravează stare cu stare.",
        LANG_PT: "Uma situação que se agrava estado a estado.",
        LANG_FR: "Une situation qui se durcit état après état.",
    },
    "sum.escalation.2": {
        LANG_DE: "Zuerst reißt ein SLO, dann {blocks}, dann {decay}",
        LANG_EN: "First an SLO breaks, then {blocks}, then {decay}",
        LANG_RO: "Mai întâi se rupe un SLO, apoi {blocks}, apoi {decay}",
        LANG_PT: "Primeiro rompe um SLO, depois {blocks}, depois {decay}",
        LANG_FR: "D'abord un SLO se rompt, puis {blocks}, puis {decay}",
    },
    "sum.part.blocks_outlier": {LANG_DE: "blockiert der Ausreißer ({outlier}) seine Naht",
                                LANG_EN: "the outlier ({outlier}) blocks its seam",
                                LANG_RO: "ART-ul atipic ({outlier}) își blochează cusătura",
                                LANG_PT: "o ART atípico ({outlier}) bloqueia a sua costura",
                                LANG_FR: "l'ART atypique ({outlier}) bloque sa couture"},
    "sum.part.blocks_plain": {LANG_DE: "blockiert eine Naht", LANG_EN: "a seam blocks", LANG_RO: "se blochează o cusătură",
                              LANG_PT: "bloqueia uma costura", LANG_FR: "une couture se bloque"},
    "sum.part.decay_weak": {LANG_DE: "verfällt die Datenqualität von {weak} und die Cross-Solution-Nähte kippen.",
                            LANG_EN: "the data quality of {weak} decays and the cross-solution seams tip over.",
                            LANG_RO: "calitatea datelor de la {weak} se degradează și cusăturile între soluții se răstoarnă.",
                            LANG_PT: "a qualidade dos dados de {weak} degrada-se e as costuras entre soluções viram.",
                            LANG_FR: "la qualité des données de {weak} se dégrade et les coutures inter-solutions basculent."},
    "sum.part.decay_plain": {LANG_DE: "kippen die Nähte zwischen den Value Streams.",
                             LANG_EN: "the seams between the value streams tip over.",
                             LANG_RO: "cusăturile dintre fluxurile de valoare se răstoarnă.",
                             LANG_PT: "as costuras entre os fluxos de valor viram.",
                             LANG_FR: "les coutures entre les flux de valeur basculent."},
    "sum.escalation.3": {
        LANG_DE: "Am Ende kommen ein neues Sicherheitsrisiko und geänderte Roadmaps dazu — der Wecker hätte früher klingeln müssen.",
        LANG_EN: "At the end a new security risk and changed roadmaps join in — the alarm should have rung earlier.",
        LANG_RO: "La final se adaugă un risc de securitate nou și roadmap-uri schimbate — alarma ar fi trebuit să sune mai devreme.",
        LANG_PT: "No fim juntam-se um novo risco de segurança e roadmaps alterados — o alarme devia ter tocado mais cedo.",
        LANG_FR: "À la fin s'ajoutent un nouveau risque de sécurité et des roadmaps modifiées — l'alarme aurait dû sonner plus tôt.",
    },
    "sum.recovery.1": {
        LANG_DE: "Eine Lage, die schlecht beginnt und sich erholt.",
        LANG_EN: "A situation that starts badly and recovers.",
        LANG_RO: "O situație care începe prost și își revine.",
        LANG_PT: "Uma situação que começa mal e recupera.",
        LANG_FR: "Une situation qui commence mal et se rétablit.",
    },
    "sum.recovery.2": {
        LANG_DE: "Stand 1 zeigt {outlier}blockierte und gefährdete Nähte, ein gerissenes SLO{weak}",
        LANG_EN: "Stand 1 shows {outlier}blocked and endangered seams, a breached SLO{weak}",
        LANG_RO: "Starea 1 arată {outlier}cusături blocate și periclitate, un SLO încălcat{weak}",
        LANG_PT: "O estado 1 mostra {outlier}costuras bloqueadas e em perigo, um SLO violado{weak}",
        LANG_FR: "L'état 1 montre {outlier}des coutures bloquées et menacées, un SLO rompu{weak}",
    },
    "sum.part.rec_outlier": {LANG_DE: "den Ausreißer ({outlier}), ", LANG_EN: "the outlier ({outlier}), ",
                             LANG_RO: "ART-ul atipic ({outlier}), ", LANG_PT: "o ART atípico ({outlier}), ",
                             LANG_FR: "l'ART atypique ({outlier}), "},
    "sum.part.rec_weak": {LANG_DE: " und die schwache Quelle {weak}.", LANG_EN: " and the weak source {weak}.",
                          LANG_RO: " și sursa slabă {weak}.", LANG_PT: " e a fonte fraca {weak}.",
                          LANG_FR: " et la source faible {weak}."},
    "sum.recovery.3": {
        LANG_DE: "Dann werden Nähte gelöst, das SLO hält wieder, der Ausreißer findet seinen Takt, zuletzt heilt die Datenquelle — nur die stillen Muster der ersten Solution bleiben.",
        LANG_EN: "Then seams get resolved, the SLO holds again, the outlier finds its pace, the data source heals last — only the silent patterns of the first solution remain.",
        LANG_RO: "Apoi cusăturile se rezolvă, SLO-ul ține din nou, ART-ul atipic își găsește ritmul, la urmă se vindecă sursa de date — rămân doar tiparele tăcute ale primei soluții.",
        LANG_PT: "Depois as costuras resolvem-se, o SLO volta a cumprir, o ART atípico encontra o ritmo, por fim a fonte de dados sara — ficam só os padrões silenciosos da primeira solução.",
        LANG_FR: "Puis les coutures se résolvent, le SLO tient de nouveau, l'ART atypique retrouve son rythme, la source de données guérit en dernier — seuls restent les motifs silencieux de la première solution.",
    },
    # --- story: notices -----------------------------------------------------------------------
    "notice.no_solution": {LANG_DE: "Portfolio ohne Solution — keine Geschichte.", LANG_EN: "Portfolio without a solution — no story.",
                           LANG_RO: "Portofoliu fără soluție — fără poveste.", LANG_PT: "Portfólio sem solução — sem história.",
                           LANG_FR: "Portefeuille sans solution — pas d'histoire."},
    "notice.one_art_host": {
        LANG_DE: "{solution} hat nur einen ART — kein Ausreißer, keine blockierte Abhängigkeit, keine wiederkehrende Naht.",
        LANG_EN: "{solution} has only one ART — no outlier, no blocked dependency, no recurring seam.",
        LANG_RO: "{solution} are un singur ART — fără ART atipic, fără dependență blocată, fără cusătură recurentă.",
        LANG_PT: "{solution} tem só um ART — sem ART atípico, sem dependência bloqueada, sem costura recorrente.",
        LANG_FR: "{solution} n'a qu'un ART — pas d'ART atypique, pas de dépendance bloquée, pas de couture récurrente.",
    },
    "notice.one_art_second": {
        LANG_DE: "{solution} hat nur einen ART — er ist zugleich die schwache Quelle und der Partner der Cross-Solution-Naht.",
        LANG_EN: "{solution} has only one ART — it is both the weak source and the partner of the cross-solution seam.",
        LANG_RO: "{solution} are un singur ART — este deopotrivă sursa slabă și partenerul cusăturii între soluții.",
        LANG_PT: "{solution} tem só um ART — é ao mesmo tempo a fonte fraca e o parceiro da costura entre soluções.",
        LANG_FR: "{solution} n'a qu'un ART — il est à la fois la source faible et le partenaire de la couture inter-solutions.",
    },
    "notice.one_solution": {
        LANG_DE: "Nur eine Solution — keine schwache Quelle, kein SLO-Bruch in einer zweiten Solution, keine Cross-Solution-Abhängigkeit.",
        LANG_EN: "Only one solution — no weak source, no SLO breach in a second solution, no cross-solution dependency.",
        LANG_RO: "O singură soluție — fără sursă slabă, fără încălcare de SLO într-o a doua soluție, fără dependență între soluții.",
        LANG_PT: "Só uma solução — sem fonte fraca, sem violação de SLO numa segunda solução, sem dependência entre soluções.",
        LANG_FR: "Une seule solution — pas de source faible, pas de rupture de SLO dans une seconde solution, pas de dépendance inter-solutions.",
    },
    "notice.anchor_free": {
        LANG_DE: "Ohne Story-Anker (nur seed-erzeugte Grundmenge): {others}.",
        LANG_EN: "Without story anchors (seed-generated base population only): {others}.",
        LANG_RO: "Fără ancore de poveste (doar populația de bază generată din seed): {others}.",
        LANG_PT: "Sem âncoras de história (só população base gerada pelo seed): {others}.",
        LANG_FR: "Sans ancres d'histoire (population de base issue du seed seulement) : {others}.",
    },
    "notice.requires": {
        LANG_DE: "{eid} braucht {needs} — bleibt aus, weil {needs} nicht aktiv ist.",
        LANG_EN: "{eid} needs {needs} — stays off because {needs} is not active.",
        LANG_RO: "{eid} are nevoie de {needs} — rămâne oprit pentru că {needs} nu este activ.",
        LANG_PT: "{eid} precisa de {needs} — fica desligado porque {needs} não está ativo.",
        LANG_FR: "{eid} a besoin de {needs} — reste désactivé car {needs} n'est pas actif.",
    },
    "notice.unknown_switch": {
        LANG_DE: "Schalter ohne Ereignis in dieser Struktur (ignoriert): {ids}.",
        LANG_EN: "Switches without an event in this structure (ignored): {ids}.",
        LANG_RO: "Comutatoare fără eveniment în această structură (ignorate): {ids}.",
        LANG_PT: "Interruptores sem evento nesta estrutura (ignorados): {ids}.",
        LANG_FR: "Interrupteurs sans événement dans cette structure (ignorés) : {ids}.",
    },
    # --- README of a data room ---------------------------------------------------------------
    "rm.title": {LANG_DE: "# {name} (generierter Demo-Datenraum)", LANG_EN: "# {name} (generated demo data room)",
                 LANG_RO: "# {name} (spațiu de date demo generat)", LANG_PT: "# {name} (sala de dados demo gerada)",
                 LANG_FR: "# {name} (espace de données démo généré)"},
    "rm.made": {
        LANG_DE: "Erzeugt mit `python -m testdata_generator --scenario portfolio` (Seed {seed}, Referenzdatum {reference}, Skala {scale}, Geschichte „{title}“).",
        LANG_EN: "Generated with `python -m testdata_generator --scenario portfolio` (seed {seed}, reference date {reference}, scale {scale}, story \"{title}\").",
        LANG_RO: "Generat cu `python -m testdata_generator --scenario portfolio` (seed {seed}, dată de referință {reference}, scară {scale}, poveste „{title}”).",
        LANG_PT: "Gerado com `python -m testdata_generator --scenario portfolio` (seed {seed}, data de referência {reference}, escala {scale}, história «{title}»).",
        LANG_FR: "Généré avec `python -m testdata_generator --scenario portfolio` (seed {seed}, date de référence {reference}, échelle {scale}, histoire « {title} »).",
    },
    "rm.usable": {
        LANG_DE: "Direkt verwendbar: `python -m portfolio portfolio.json` bzw. die Solution-Configs einzeln. **Der Ordner ist ein Portfolio-Datenraum**: alle Pfade in den Configs sind relativ zur jeweiligen Config-Datei — der Ordner kann als Ganzes verschoben, kopiert oder gezippt werden.",
        LANG_EN: "Directly usable: `python -m portfolio portfolio.json` or the solution configs individually. **The folder is a portfolio data room**: every path in the configs is relative to its config file — the folder can be moved, copied or zipped as a whole.",
        LANG_RO: "Direct utilizabil: `python -m portfolio portfolio.json` sau configurațiile de soluție individual. **Folderul este un spațiu de date de portofoliu**: toate căile din configurații sunt relative la fișierul de configurare — folderul poate fi mutat, copiat sau arhivat ca întreg.",
        LANG_PT: "Diretamente utilizável: `python -m portfolio portfolio.json` ou as configurações de solução individualmente. **A pasta é uma sala de dados de portfólio**: todos os caminhos nas configurações são relativos ao respetivo ficheiro — a pasta pode ser movida, copiada ou comprimida como um todo.",
        LANG_FR: "Directement utilisable : `python -m portfolio portfolio.json` ou les configurations de solution une à une. **Le dossier est un espace de données de portefeuille** : tous les chemins des configurations sont relatifs à leur fichier — le dossier peut être déplacé, copié ou zippé en entier.",
    },
    "rm.tree.structure": {LANG_DE: "Struktur und Geschichte als Daten", LANG_EN: "structure and story as data",
                          LANG_RO: "structura și povestea ca date", LANG_PT: "estrutura e história como dados",
                          LANG_FR: "structure et histoire sous forme de données"},
    "rm.tree.portfolio": {LANG_DE: "Einstieg (Portfolio)", LANG_EN: "entry point (portfolio)", LANG_RO: "punct de intrare (portofoliu)",
                          LANG_PT: "ponto de entrada (portfólio)", LANG_FR: "point d'entrée (portefeuille)"},
    "rm.tree.solution": {LANG_DE: "je Solution: solution.json, arts/ (IssueTimes/Transitions/CFD), registers/",
                         LANG_EN: "per solution: solution.json, arts/ (IssueTimes/Transitions/CFD), registers/",
                         LANG_RO: "per soluție: solution.json, arts/ (IssueTimes/Transitions/CFD), registers/",
                         LANG_PT: "por solução: solution.json, arts/ (IssueTimes/Transitions/CFD), registers/",
                         LANG_FR: "par solution : solution.json, arts/ (IssueTimes/Transitions/CFD), registers/"},
    "rm.tree.snapshots": {LANG_DE: "snapshot_<nn>_<datum>.json je Stand, stands.json, snapshot_prev/now.json = die letzten beiden",
                          LANG_EN: "snapshot_<nn>_<date>.json per stand, stands.json, snapshot_prev/now.json = the last two",
                          LANG_RO: "snapshot_<nn>_<data>.json per stare, stands.json, snapshot_prev/now.json = ultimele două",
                          LANG_PT: "snapshot_<nn>_<data>.json por estado, stands.json, snapshot_prev/now.json = os dois últimos",
                          LANG_FR: "snapshot_<nn>_<date>.json par état, stands.json, snapshot_prev/now.json = les deux derniers"},
    "rm.tree.deltas": {LANG_DE: "delta_<nn>-<nn+1>.md/.html je Folgepaar", LANG_EN: "delta_<nn>-<nn+1>.md/.html per consecutive pair",
                       LANG_RO: "delta_<nn>-<nn+1>.md/.html per pereche consecutivă", LANG_PT: "delta_<nn>-<nn+1>.md/.html por par consecutivo",
                       LANG_FR: "delta_<nn>-<nn+1>.md/.html par paire consécutive"},
    "rm.tree.sources": {LANG_DE: "Provider-Rohdaten (Replay-Dateien im Systemformat) + sources-Configs je Solution",
                        LANG_EN: "provider raw data (replay files in the systems' formats) + sources configs per solution",
                        LANG_RO: "date brute ale providerilor (fișiere replay în formatul sistemelor) + configurații sources per soluție",
                        LANG_PT: "dados brutos dos providers (ficheiros replay no formato dos sistemas) + configurações sources por solução",
                        LANG_FR: "données brutes des providers (fichiers replay au format des systèmes) + configurations sources par solution"},
    "rm.h_structure": {LANG_DE: "## Struktur", LANG_EN: "## Structure", LANG_RO: "## Structură", LANG_PT: "## Estrutura", LANG_FR: "## Structure"},
    "rm.workflow.classic": {LANG_DE: "klassischer Workflow (Default-Pfad)", LANG_EN: "classic workflow (default path)",
                            LANG_RO: "flux de lucru clasic (calea implicită)", LANG_PT: "fluxo de trabalho clássico (caminho padrão)",
                            LANG_FR: "flux de travail classique (chemin par défaut)"},
    "rm.workflow.stage_map": {LANG_DE: "eigene stage_map (Schema 2)", LANG_EN: "own stage_map (schema 2)",
                              LANG_RO: "stage_map proprie (schema 2)", LANG_PT: "stage_map própria (esquema 2)",
                              LANG_FR: "stage_map propre (schéma 2)"},
    "rm.registers": {
        LANG_DE: "Die Register bestehen aus festen **Story-Ankern** (unten) plus einer seed-generierten Grundmenge; `--scale s|m|l` steuert deren Umfang je Solution (s = nur Anker, m = Standard, l = Stresstest). Die Anker und ihre Geschichten sind auf jeder Skala identisch. Die Statuswege der ARTs sind unordentlich wie in echten ARTs (Realismus 60: Sprünge, Abbrüche, Schleifen, Wiedereröffnung). Je ART lassen sich die Generator-Regler übersteuern (GUI-Dialog „ART-Profile…“ bzw. `--art-profiles datei.json`); Overrides gelten in allen Ständen, alles andere behält seinen Story-Wert.",
        LANG_EN: "The registers consist of fixed **story anchors** (below) plus a seed-generated base population; `--scale s|m|l` controls its size per solution (s = anchors only, m = default, l = stress test). Anchors and their stories are identical at every scale. The ARTs' stage paths are untidy like real ones (realism 60: skips, cancellations, loops, reopening). Per ART the generator knobs can be overridden (GUI dialog \"ART profiles…\" or `--art-profiles file.json`); overrides apply in every stand, everything else keeps its story value.",
        LANG_RO: "Registrele constau din **ancore de poveste** fixe (mai jos) plus o populație de bază generată din seed; `--scale s|m|l` îi controlează mărimea per soluție (s = doar ancore, m = implicit, l = test de stres). Ancorele și poveștile lor sunt identice la orice scară. Traseele de stare ale ART-urilor sunt dezordonate ca în realitate (realism 60: salturi, anulări, bucle, redeschideri). Per ART, parametrii generatorului pot fi suprascriși (dialogul „Profiluri ART…” sau `--art-profiles fișier.json`); suprascrierile se aplică în toate stările, restul își păstrează valoarea din poveste.",
        LANG_PT: "Os registos consistem em **âncoras de história** fixas (abaixo) mais uma população base gerada pelo seed; `--scale s|m|l` controla o seu tamanho por solução (s = só âncoras, m = padrão, l = teste de carga). As âncoras e as suas histórias são idênticas em todas as escalas. Os percursos de estado dos ARTs são desarrumados como os reais (realismo 60: saltos, cancelamentos, ciclos, reaberturas). Por ART, os parâmetros do gerador podem ser sobrepostos (diálogo «Perfis de ART…» ou `--art-profiles ficheiro.json`); as sobreposições valem em todos os estados, o resto mantém o valor da história.",
        LANG_FR: "Les registres se composent d'**ancres d'histoire** fixes (ci-dessous) plus d'une population de base issue du seed ; `--scale s|m|l` en règle la taille par solution (s = ancres seulement, m = défaut, l = test de charge). Les ancres et leurs histoires sont identiques à toute échelle. Les parcours d'états des ARTs sont désordonnés comme les vrais (réalisme 60 : sauts, abandons, boucles, réouvertures). Par ART, les réglages du générateur peuvent être surchargés (dialogue « Profils ART… » ou `--art-profiles fichier.json`) ; les surcharges valent dans tous les états, le reste garde sa valeur d'histoire.",
    },
    "rm.h_story": {LANG_DE: "## Geschichte „{title}“ (story.json)", LANG_EN: "## Story \"{title}\" (story.json)",
                   LANG_RO: "## Povestea „{title}” (story.json)", LANG_PT: "## História «{title}» (story.json)",
                   LANG_FR: "## Histoire « {title} » (story.json)"},
    "rm.when.all": {LANG_DE: "in allen Ständen", LANG_EN: "in all stands", LANG_RO: "în toate stările", LANG_PT: "em todos os estados", LANG_FR: "dans tous les états"},
    "rm.when.from": {LANG_DE: "ab Stand {a:02d}", LANG_EN: "from stand {a:02d}", LANG_RO: "de la starea {a:02d}", LANG_PT: "a partir do estado {a:02d}", LANG_FR: "à partir de l'état {a:02d}"},
    "rm.when.last": {LANG_DE: "nur im letzten Stand", LANG_EN: "only in the last stand", LANG_RO: "doar în ultima stare", LANG_PT: "só no último estado", LANG_FR: "seulement au dernier état"},
    "rm.when.one": {LANG_DE: "Stand {a:02d}", LANG_EN: "stand {a:02d}", LANG_RO: "starea {a:02d}", LANG_PT: "estado {a:02d}", LANG_FR: "état {a:02d}"},
    "rm.when.range": {LANG_DE: "Stand {a:02d} bis {b:02d}", LANG_EN: "stands {a:02d} to {b:02d}", LANG_RO: "stările {a:02d} până la {b:02d}", LANG_PT: "estados {a:02d} a {b:02d}", LANG_FR: "états {a:02d} à {b:02d}"},
    "rm.when.off": {LANG_DE: "aus", LANG_EN: "off", LANG_RO: "oprit", LANG_PT: "desligado", LANG_FR: "désactivé"},
    "rm.notices": {LANG_DE: "Hinweise der Rollenbindung:", LANG_EN: "Notes of the role binding:", LANG_RO: "Note ale legării rolurilor:",
                   LANG_PT: "Notas da ligação de papéis:", LANG_FR: "Notes de la liaison des rôles :"},
    "rm.h_stands": {LANG_DE: "## Stände", LANG_EN: "## Stands", LANG_RO: "## Stări", LANG_PT: "## Estados", LANG_FR: "## États"},
    "rm.stands_intro": {
        LANG_DE: "{n} Stände im Abstand von {days} Tagen — jeder Stand ein Snapshot, jedes Folgepaar ein fertiges Delta-Briefing. Die Ereignisse gelten in ihrem Stand-Fenster (siehe Geschichte); davor und danach zeigt die Reihe die Lage ohne sie.",
        LANG_EN: "{n} stands {days} days apart — every stand a snapshot, every consecutive pair a rendered delta briefing. Events apply within their stand window (see story); before and after, the series shows the situation without them.",
        LANG_RO: "{n} stări la {days} zile distanță — fiecare stare un snapshot, fiecare pereche consecutivă un Delta-Briefing gata redat. Evenimentele se aplică în fereastra lor de stări (vezi povestea); înainte și după, seria arată situația fără ele.",
        LANG_PT: "{n} estados com {days} dias de intervalo — cada estado um snapshot, cada par consecutivo um Delta-Briefing pronto. Os eventos valem na sua janela de estados (ver história); antes e depois, a série mostra a situação sem eles.",
        LANG_FR: "{n} états espacés de {days} jours — chaque état un snapshot, chaque paire consécutive un Delta-Briefing rendu. Les événements valent dans leur fenêtre d'états (voir l'histoire) ; avant et après, la série montre la situation sans eux.",
    },
    "rm.stand_line": {LANG_DE: "Stand {k:02d}: {date}", LANG_EN: "Stand {k:02d}: {date}", LANG_RO: "Starea {k:02d}: {date}",
                      LANG_PT: "Estado {k:02d}: {date}", LANG_FR: "État {k:02d} : {date}"},
    "rm.deltas_label": {LANG_DE: "Delta-Briefings: ", LANG_EN: "Delta briefings: ", LANG_RO: "Delta-Briefing-uri: ",
                        LANG_PT: "Delta-Briefings: ", LANG_FR: "Delta-Briefings : "},
    "rm.h_sources": {LANG_DE: "## Quellen (Provider-Rohdaten, Weg 2)", LANG_EN: "## Sources (provider raw data, path 2)",
                     LANG_RO: "## Surse (date brute ale providerilor, calea 2)", LANG_PT: "## Fontes (dados brutos dos providers, caminho 2)",
                     LANG_FR: "## Sources (données brutes des providers, voie 2)"},
    "rm.sources_intro": {
        LANG_DE: "Je Solution liegen unter `sources/<name>/` die Rohdaten, wie die Systeme sie liefern würden — Prometheus-Instant-Queries, GitHub-Deployments/PRs/Issues oder GitLab-DORA-Tageswerte, SonarQube-Measures, eine SLO-CSV — als Replay-Dateien, dazu die passenden `sources`-Configs. `python -m sources fetch` läuft darauf ohne Netz (`\"replay\"` in der Config) und liefert, was auch in `registers/` steht; GitHub-DORA kommt näherungsweise (Zählungen), GitLab exakt. Pfade in den Configs gelten relativ zur Config-Datei.",
        LANG_EN: "Per solution, `sources/<name>/` holds the raw data as the systems would deliver it — Prometheus instant queries, GitHub deployments/PRs/issues or GitLab DORA daily values, SonarQube measures, an SLO CSV — as replay files, plus the matching `sources` configs. `python -m sources fetch` runs on them without network (`\"replay\"` in the config) and yields what `registers/` holds; GitHub DORA comes approximately (counts), GitLab exactly. Paths in the configs are relative to the config file.",
        LANG_RO: "Per soluție, `sources/<name>/` conține datele brute așa cum le-ar livra sistemele — Prometheus instant queries, GitHub deployments/PR-uri/issues sau valori zilnice DORA din GitLab, măsuri SonarQube, un CSV SLO — ca fișiere replay, plus configurațiile `sources` potrivite. `python -m sources fetch` rulează pe ele fără rețea (`\"replay\"` în configurație) și returnează ce stă în `registers/`; DORA din GitHub vine aproximativ (numărări), GitLab exact. Căile din configurații sunt relative la fișierul de configurare.",
        LANG_PT: "Por solução, `sources/<name>/` contém os dados brutos como os sistemas os entregariam — Prometheus instant queries, GitHub deployments/PRs/issues ou valores diários DORA do GitLab, medidas SonarQube, um CSV de SLO — como ficheiros replay, mais as configurações `sources` correspondentes. `python -m sources fetch` corre sobre eles sem rede (`\"replay\"` na configuração) e devolve o que está em `registers/`; o DORA do GitHub vem aproximado (contagens), o GitLab exato. Os caminhos nas configurações são relativos ao ficheiro de configuração.",
        LANG_FR: "Par solution, `sources/<name>/` contient les données brutes telles que les systèmes les livreraient — Prometheus instant queries, GitHub deployments/PR/issues ou valeurs journalières DORA de GitLab, mesures SonarQube, un CSV SLO — en fichiers replay, plus les configurations `sources` correspondantes. `python -m sources fetch` tourne dessus sans réseau (`\"replay\"` dans la configuration) et restitue ce que contient `registers/` ; le DORA GitHub est approximatif (comptages), GitLab exact. Les chemins des configurations sont relatifs au fichier de configuration.",
    },
    "rm.sources_none": {LANG_DE: "`{key}`: keine Register mit Einträgen — keine Rohdaten.", LANG_EN: "`{key}`: no registers with entries — no raw data.",
                        LANG_RO: "`{key}`: niciun registru cu intrări — fără date brute.", LANG_PT: "`{key}`: nenhum registo com entradas — sem dados brutos.",
                        LANG_FR: "`{key}` : aucun registre avec des entrées — pas de données brutes."},
    "rm.sources_dora": {LANG_DE: " (DORA über {provider})", LANG_EN: " (DORA via {provider})", LANG_RO: " (DORA prin {provider})",
                        LANG_PT: " (DORA via {provider})", LANG_FR: " (DORA via {provider})"},
    "rm.h_more": {LANG_DE: "## Weitere Wege", LANG_EN: "## Further paths", LANG_RO: "## Alte căi", LANG_PT: "## Outros caminhos", LANG_FR: "## Autres voies"},
    "rm.more.delta": {
        LANG_DE: "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (Stand vor {days} Tagen) und `snapshots/snapshot_now.json` liegen bei — `python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json`; jedes andere Paar genauso.",
        LANG_EN: "- **Delta briefing (D2)**: `snapshots/snapshot_prev.json` (the stand {days} days earlier) and `snapshots/snapshot_now.json` are included — `python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json`; any other pair the same way.",
        LANG_RO: "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (starea de acum {days} zile) și `snapshots/snapshot_now.json` sunt incluse — `python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json`; orice altă pereche la fel.",
        LANG_PT: "- **Delta-Briefing (D2)**: `snapshots/snapshot_prev.json` (o estado de há {days} dias) e `snapshots/snapshot_now.json` estão incluídos — `python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json`; qualquer outro par da mesma forma.",
        LANG_FR: "- **Delta-Briefing (D2)** : `snapshots/snapshot_prev.json` (l'état d'il y a {days} jours) et `snapshots/snapshot_now.json` sont inclus — `python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json` ; toute autre paire de même.",
    },
    "rm.more.narrate": {
        LANG_DE: "- **KI-Narration (D2 Teil 2)**: `--narrate mock` ergänzt das Briefing um den gekennzeichneten Abschnitt „Narration (Entwurf)“ — ohne Modell oder Installation (Attrappe); der Nachweis landet in `llm_audit.jsonl`.",
        LANG_EN: "- **AI narration (D2 part 2)**: `--narrate mock` adds the labelled section \"Narration (draft)\" to the briefing — without a model or installation (mock); the evidence lands in `llm_audit.jsonl`.",
        LANG_RO: "- **Narațiune AI (D2 partea 2)**: `--narrate mock` adaugă briefingului secțiunea marcată „Narațiune (schiță)” — fără model sau instalare (mock); dovada ajunge în `llm_audit.jsonl`.",
        LANG_PT: "- **Narração por IA (D2 parte 2)**: `--narrate mock` acrescenta ao briefing a secção marcada «Narração (rascunho)» — sem modelo nem instalação (mock); a evidência fica em `llm_audit.jsonl`.",
        LANG_FR: "- **Narration IA (D2 partie 2)** : `--narrate mock` ajoute au briefing la section marquée « Narration (brouillon) » — sans modèle ni installation (mock) ; la preuve atterrit dans `llm_audit.jsonl`.",
    },
    "rm.more.conference": {LANG_DE: "- **Konferenzmappe**: `python -m portfolio portfolio.json --conference mappe.html`.",
                           LANG_EN: "- **Conference pre-read**: `python -m portfolio portfolio.json --conference preread.html`.",
                           LANG_RO: "- **Dosarul conferinței**: `python -m portfolio portfolio.json --conference dosar.html`.",
                           LANG_PT: "- **Dossiê da conferência**: `python -m portfolio portfolio.json --conference dossie.html`.",
                           LANG_FR: "- **Dossier de conférence** : `python -m portfolio portfolio.json --conference dossier.html`."},
    "rm.more.getdata": {
        LANG_DE: "- **Export-Prüfung (Weg 2)**: `python -m get_data check raw/{art}_jira.json`; die Roh-JSONs unter `raw/` sind zugleich Demo-Futter für get_data.",
        LANG_EN: "- **Export check (path 2)**: `python -m get_data check raw/{art}_jira.json`; the raw JSONs under `raw/` double as demo input for get_data.",
        LANG_RO: "- **Verificarea exportului (calea 2)**: `python -m get_data check raw/{art}_jira.json`; JSON-urile brute din `raw/` servesc și ca intrare demo pentru get_data.",
        LANG_PT: "- **Verificação de exportação (caminho 2)**: `python -m get_data check raw/{art}_jira.json`; os JSON brutos em `raw/` servem também de entrada demo para o get_data.",
        LANG_FR: "- **Vérification d'export (voie 2)** : `python -m get_data check raw/{art}_jira.json` ; les JSON bruts sous `raw/` servent aussi d'entrée démo à get_data.",
    },
    "rm.more.delivery": {
        LANG_DE: "- **Delivery-Register**: erzeugt/austauschbar über `python -m sources fetch` (Provider: file, prometheus, github, gitlab, sonarqube — kombinierbar).",
        LANG_EN: "- **Delivery register**: produced/exchangeable via `python -m sources fetch` (providers: file, prometheus, github, gitlab, sonarqube — combinable).",
        LANG_RO: "- **Registrul de livrare**: produs/înlocuibil prin `python -m sources fetch` (provideri: file, prometheus, github, gitlab, sonarqube — combinabili).",
        LANG_PT: "- **Registo de entrega**: produzido/substituível via `python -m sources fetch` (providers: file, prometheus, github, gitlab, sonarqube — combináveis).",
        LANG_FR: "- **Registre de livraison** : produit/remplaçable via `python -m sources fetch` (providers : file, prometheus, github, gitlab, sonarqube — combinables).",
    },
    "rm.root.title": {LANG_DE: "# Demo-Datenraum mit mehreren Portfolios", LANG_EN: "# Demo data room with several portfolios",
                      LANG_RO: "# Spațiu de date demo cu mai multe portofolii", LANG_PT: "# Sala de dados demo com vários portfólios",
                      LANG_FR: "# Espace de données démo à plusieurs portefeuilles"},
    "rm.root.made": {
        LANG_DE: "Erzeugt mit `python -m testdata_generator --scenario portfolio` (Seed {seed}, Referenzdatum {reference}, {describe}).",
        LANG_EN: "Generated with `python -m testdata_generator --scenario portfolio` (seed {seed}, reference date {reference}, {describe}).",
        LANG_RO: "Generat cu `python -m testdata_generator --scenario portfolio` (seed {seed}, dată de referință {reference}, {describe}).",
        LANG_PT: "Gerado com `python -m testdata_generator --scenario portfolio` (seed {seed}, data de referência {reference}, {describe}).",
        LANG_FR: "Généré avec `python -m testdata_generator --scenario portfolio` (seed {seed}, date de référence {reference}, {describe}).",
    },
    "rm.root.intro": {
        LANG_DE: "Jeder Unterordner ist ein vollständiger Portfolio-Datenraum mit eigener `portfolio.json`, eigenen Ständen und eigener README:",
        LANG_EN: "Every sub-folder is a complete portfolio data room with its own `portfolio.json`, its own stands and its own README:",
        LANG_RO: "Fiecare subfolder este un spațiu de date de portofoliu complet, cu propriul `portfolio.json`, propriile stări și propriul README:",
        LANG_PT: "Cada subpasta é uma sala de dados de portfólio completa, com o seu `portfolio.json`, os seus estados e o seu README:",
        LANG_FR: "Chaque sous-dossier est un espace de données de portefeuille complet, avec son `portfolio.json`, ses états et son README :",
    },
    "rm.root.note": {
        LANG_DE: "Ein Lagebild über mehrere Portfolios hinweg ist heute kein Feature; die Daten dafür liegen hier bereits nebeneinander.",
        LANG_EN: "A picture across several portfolios is not a feature today; the data for it already lies side by side here.",
        LANG_RO: "O imagine peste mai multe portofolii nu este încă o funcție; datele pentru ea stau deja aici una lângă alta.",
        LANG_PT: "Uma imagem transversal a vários portfólios ainda não é uma funcionalidade; os dados para isso já estão aqui lado a lado.",
        LANG_FR: "Une image transversale à plusieurs portefeuilles n'est pas encore une fonction ; les données pour cela sont déjà ici côte à côte.",
    },
    "rm.cont.appended": {
        LANG_DE: "_Fortgeschrieben am {today}: Referenzdatum {old} → {new}, {added} neue Vorgänge; snapshot_prev = Stand {old}, snapshot_now = Stand {new}. Register unverändert._",
        LANG_EN: "_Continued on {today}: reference date {old} → {new}, {added} new items; snapshot_prev = stand {old}, snapshot_now = stand {new}. Registers unchanged._",
        LANG_RO: "_Continuat la {today}: dată de referință {old} → {new}, {added} elemente noi; snapshot_prev = starea {old}, snapshot_now = starea {new}. Registre neschimbate._",
        LANG_PT: "_Continuado em {today}: data de referência {old} → {new}, {added} novos itens; snapshot_prev = estado {old}, snapshot_now = estado {new}. Registos inalterados._",
        LANG_FR: "_Prolongé le {today} : date de référence {old} → {new}, {added} nouveaux éléments ; snapshot_prev = état {old}, snapshot_now = état {new}. Registres inchangés._",
    },
    # --- progress steps and details ---------------------------------------------------------------
    "step.story": {LANG_DE: "Struktur und Geschichte", LANG_EN: "Structure and story", LANG_RO: "Structură și poveste", LANG_PT: "Estrutura e história", LANG_FR: "Structure et histoire"},
    "step.arts": {LANG_DE: "Jira-Exporte und Arbeitsmappen", LANG_EN: "Jira exports and workbooks", LANG_RO: "Exporturi Jira și registre de lucru", LANG_PT: "Exportações Jira e livros de trabalho", LANG_FR: "Exports Jira et classeurs"},
    "step.registers": {LANG_DE: "Register", LANG_EN: "Registers", LANG_RO: "Registre", LANG_PT: "Registos", LANG_FR: "Registres"},
    "step.configs": {LANG_DE: "Konfigurationen", LANG_EN: "Configurations", LANG_RO: "Configurații", LANG_PT: "Configurações", LANG_FR: "Configurations"},
    "step.sources": {LANG_DE: "Provider-Rohdaten", LANG_EN: "Provider raw data", LANG_RO: "Date brute ale providerilor", LANG_PT: "Dados brutos dos providers", LANG_FR: "Données brutes des providers"},
    "step.readme": {LANG_DE: "README", LANG_EN: "README", LANG_RO: "README", LANG_PT: "README", LANG_FR: "README"},
    "step.stands": {LANG_DE: "Stände-Reihe", LANG_EN: "Series of stands", LANG_RO: "Seria de stări", LANG_PT: "Série de estados", LANG_FR: "Série d'états"},
    "step.deltas": {LANG_DE: "Delta-Briefings", LANG_EN: "Delta briefings", LANG_RO: "Delta-Briefing-uri", LANG_PT: "Delta-Briefings", LANG_FR: "Delta-Briefings"},
    "step.ai_drafts": {LANG_DE: "KI-Entwürfe (Mock)", LANG_EN: "AI drafts (mock)", LANG_RO: "Schițe AI (mock)", LANG_PT: "Rascunhos de IA (mock)", LANG_FR: "Brouillons IA (mock)"},
    "det.story": {LANG_DE: "{name}: {title}, {solutions} Solutions, {arts} ARTs", LANG_EN: "{name}: {title}, {solutions} solutions, {arts} ARTs",
                  LANG_RO: "{name}: {title}, {solutions} soluții, {arts} ART-uri", LANG_PT: "{name}: {title}, {solutions} soluções, {arts} ARTs",
                  LANG_FR: "{name} : {title}, {solutions} solutions, {arts} ARTs"},
    "det.arts_running": {LANG_DE: "{n} ARTs", LANG_EN: "{n} ARTs", LANG_RO: "{n} ART-uri", LANG_PT: "{n} ARTs", LANG_FR: "{n} ARTs"},
    "det.arts_done": {LANG_DE: "{n} Jira-Exporte, Arbeitsmappen", LANG_EN: "{n} Jira exports, workbooks", LANG_RO: "{n} exporturi Jira, registre de lucru",
                      LANG_PT: "{n} exportações Jira, livros de trabalho", LANG_FR: "{n} exports Jira, classeurs"},
    "det.registers_running": {LANG_DE: "{n} Solutions", LANG_EN: "{n} solutions", LANG_RO: "{n} soluții", LANG_PT: "{n} soluções", LANG_FR: "{n} solutions"},
    "det.registers_done": {LANG_DE: "{n} Register", LANG_EN: "{n} registers", LANG_RO: "{n} registre", LANG_PT: "{n} registos", LANG_FR: "{n} registres"},
    "det.configs": {LANG_DE: "portfolio.json, solution.json je Solution, pi_config, structure, story",
                    LANG_EN: "portfolio.json, solution.json per solution, pi_config, structure, story",
                    LANG_RO: "portfolio.json, solution.json per soluție, pi_config, structure, story",
                    LANG_PT: "portfolio.json, solution.json por solução, pi_config, structure, story",
                    LANG_FR: "portfolio.json, solution.json par solution, pi_config, structure, story"},
    "det.sources": {LANG_DE: "{n} Solutions mit Rohdaten", LANG_EN: "{n} solutions with raw data", LANG_RO: "{n} soluții cu date brute",
                    LANG_PT: "{n} soluções com dados brutos", LANG_FR: "{n} solutions avec données brutes"},
    "det.stands_running": {LANG_DE: "{n} Stände", LANG_EN: "{n} stands", LANG_RO: "{n} stări", LANG_PT: "{n} estados", LANG_FR: "{n} états"},
    "det.stands_done": {LANG_DE: "{n} Stände, {first} bis {last}", LANG_EN: "{n} stands, {first} to {last}", LANG_RO: "{n} stări, {first} până la {last}",
                        LANG_PT: "{n} estados, {first} a {last}", LANG_FR: "{n} états, {first} à {last}"},
    "det.deltas_running": {LANG_DE: "{n} Folgepaare", LANG_EN: "{n} consecutive pairs", LANG_RO: "{n} perechi consecutive", LANG_PT: "{n} pares consecutivos", LANG_FR: "{n} paires consécutives"},
    "det.deltas_done": {LANG_DE: "{n} Delta-Briefings (md + html)", LANG_EN: "{n} delta briefings (md + html)", LANG_RO: "{n} Delta-Briefing-uri (md + html)",
                        LANG_PT: "{n} Delta-Briefings (md + html)", LANG_FR: "{n} Delta-Briefings (md + html)"},
    "det.drafts_off": {LANG_DE: "Schalter aus", LANG_EN: "switch off", LANG_RO: "comutator oprit", LANG_PT: "interruptor desligado", LANG_FR: "interrupteur désactivé"},
    "det.drafts_done": {LANG_DE: "{n} Ordner", LANG_EN: "{n} folder(s)", LANG_RO: "{n} folder(e)", LANG_PT: "{n} pasta(s)", LANG_FR: "{n} dossier(s)"},
    # --- log lines ------------------------------------------------------------------------------------
    "log.notice": {LANG_DE: "  Hinweis: {text}", LANG_EN: "  Note: {text}", LANG_RO: "  Notă: {text}", LANG_PT: "  Nota: {text}", LANG_FR: "  Remarque : {text}"},
    "log.stands_start": {LANG_DE: "  Stände-Reihe: {n} Stände im {days}-Tage-Rhythmus ...", LANG_EN: "  Series of stands: {n} stands every {days} days ...",
                         LANG_RO: "  Seria de stări: {n} stări la fiecare {days} zile ...", LANG_PT: "  Série de estados: {n} estados a cada {days} dias ...",
                         LANG_FR: "  Série d'états : {n} états tous les {days} jours ..."},
    "log.stand": {LANG_DE: "    Stand {k:02d}: {date}", LANG_EN: "    Stand {k:02d}: {date}", LANG_RO: "    Starea {k:02d}: {date}",
                  LANG_PT: "    Estado {k:02d}: {date}", LANG_FR: "    État {k:02d} : {date}"},
    "log.deltas": {LANG_DE: "  Delta-Briefings: {n} Folgepaare unter deltas/", LANG_EN: "  Delta briefings: {n} consecutive pairs under deltas/",
                   LANG_RO: "  Delta-Briefing-uri: {n} perechi consecutive sub deltas/", LANG_PT: "  Delta-Briefings: {n} pares consecutivos em deltas/",
                   LANG_FR: "  Delta-Briefings : {n} paires consécutives sous deltas/"},
    "log.sources": {LANG_DE: "  Quellen {key}: {kinds}{dora}", LANG_EN: "  Sources {key}: {kinds}{dora}", LANG_RO: "  Surse {key}: {kinds}{dora}",
                    LANG_PT: "  Fontes {key}: {kinds}{dora}", LANG_FR: "  Sources {key} : {kinds}{dora}"},
    "log.sources_none": {LANG_DE: "  Quellen {key}: keine Register mit Einträgen — keine Rohdaten", LANG_EN: "  Sources {key}: no registers with entries — no raw data",
                         LANG_RO: "  Surse {key}: niciun registru cu intrări — fără date brute", LANG_PT: "  Fontes {key}: nenhum registo com entradas — sem dados brutos",
                         LANG_FR: "  Sources {key} : aucun registre avec des entrées — pas de données brutes"},
    "log.portfolio": {LANG_DE: "Portfolio {name} -> {key}/", LANG_EN: "Portfolio {name} -> {key}/", LANG_RO: "Portofoliu {name} -> {key}/",
                      LANG_PT: "Portfólio {name} -> {key}/", LANG_FR: "Portefeuille {name} -> {key}/"},
    "log.complete": {LANG_DE: "Szenario komplett: {out}", LANG_EN: "Scenario complete: {out}", LANG_RO: "Scenariu complet: {out}",
                     LANG_PT: "Cenário completo: {out}", LANG_FR: "Scénario complet : {out}"},
    "log.complete_multi": {LANG_DE: "Szenario komplett: {out} ({describe})", LANG_EN: "Scenario complete: {out} ({describe})",
                           LANG_RO: "Scenariu complet: {out} ({describe})", LANG_PT: "Cenário completo: {out} ({describe})",
                           LANG_FR: "Scénario complet : {out} ({describe})"},
    "log.drafts": {LANG_DE: "  KI-Entwürfe (Mock): Lagevortrag, {n} Antworten, Prompt-Bündel, Übungsantwort -> ai_drafts/",
                   LANG_EN: "  AI drafts (mock): spoken briefing, {n} answers, prompt bundle, practice answer -> ai_drafts/",
                   LANG_RO: "  Schițe AI (mock): briefing vorbit, {n} răspunsuri, pachet de prompt, răspuns de exercițiu -> ai_drafts/",
                   LANG_PT: "  Rascunhos de IA (mock): briefing falado, {n} respostas, pacote de prompt, resposta de exercício -> ai_drafts/",
                   LANG_FR: "  Brouillons IA (mock) : briefing oral, {n} réponses, paquet de prompt, réponse d'exercice -> ai_drafts/"},
    "log.cont.start": {LANG_DE: "Szenario fortschreiben: {old} -> {new} ({days} Tage)", LANG_EN: "Continuing the scenario: {old} -> {new} ({days} days)",
                       LANG_RO: "Continuarea scenariului: {old} -> {new} ({days} zile)", LANG_PT: "Continuação do cenário: {old} -> {new} ({days} dias)",
                       LANG_FR: "Prolongation du scénario : {old} -> {new} ({days} jours)"},
    "log.cont.art": {LANG_DE: "  {name}: {before} -> {after} issues{stale}", LANG_EN: "  {name}: {before} -> {after} issues{stale}",
                     LANG_RO: "  {name}: {before} -> {after} issues{stale}", LANG_PT: "  {name}: {before} -> {after} issues{stale}",
                     LANG_FR: "  {name} : {before} -> {after} issues{stale}"},
    "log.cont.stale": {LANG_DE: " (Datenstand -{days}d bleibt)", LANG_EN: " (data stays -{days}d stale)", LANG_RO: " (datele rămân vechi de {days} zile)",
                       LANG_PT: " (dados continuam com {days} dias)", LANG_FR: " (les données restent datées de {days} j)"},
    "log.cont.rotated": {LANG_DE: "  Snapshots rotiert: now ({old}) -> prev, neues now ({new})", LANG_EN: "  Snapshots rotated: now ({old}) -> prev, new now ({new})",
                         LANG_RO: "  Snapshot-uri rotite: now ({old}) -> prev, now nou ({new})", LANG_PT: "  Snapshots rodados: now ({old}) -> prev, novo now ({new})",
                         LANG_FR: "  Snapshots tournés : now ({old}) -> prev, nouveau now ({new})"},
    "log.cont.appended": {LANG_DE: "  Stand {k:02d} ({date}) an die Reihe angehängt, Delta {a:02d}-{b:02d} gerendert",
                          LANG_EN: "  Stand {k:02d} ({date}) appended to the series, delta {a:02d}-{b:02d} rendered",
                          LANG_RO: "  Starea {k:02d} ({date}) adăugată seriei, delta {a:02d}-{b:02d} redat",
                          LANG_PT: "  Estado {k:02d} ({date}) acrescentado à série, delta {a:02d}-{b:02d} gerado",
                          LANG_FR: "  État {k:02d} ({date}) ajouté à la série, delta {a:02d}-{b:02d} rendu"},
    "log.cont.done": {LANG_DE: "Fortschreibung komplett: {out} (+{added} Vorgänge)", LANG_EN: "Continuation complete: {out} (+{added} items)",
                      LANG_RO: "Continuare completă: {out} (+{added} elemente)", LANG_PT: "Continuação completa: {out} (+{added} itens)",
                      LANG_FR: "Prolongation complète : {out} (+{added} éléments)"},
    # --- estimate warning -------------------------------------------------------------------------
    "warn.arts": {LANG_DE: "{n} ARTs (ab {limit} dauert die Erzeugung spürbar)",
                  LANG_EN: "{n} ARTs (from {limit} generation takes noticeably longer)",
                  LANG_RO: "{n} ART-uri (de la {limit} generarea durează sensibil mai mult)",
                  LANG_PT: "{n} ARTs (a partir de {limit} a geração demora sensivelmente mais)",
                  LANG_FR: "{n} ARTs (à partir de {limit} la génération est nettement plus longue)"},
    "warn.portfolios": {LANG_DE: "{n} Portfolios bei Umfang L", LANG_EN: "{n} portfolios at scale L",
                        LANG_RO: "{n} portofolii la scara L", LANG_PT: "{n} portfólios na escala L",
                        LANG_FR: "{n} portefeuilles à l'échelle L"},
    # --- command line -----------------------------------------------------------------------------------
    "cli.structure": {
        LANG_DE: "Struktur: {describe} — {exports} Jira-Exporte, {workbooks} Arbeitsmappen, {registers} Register, {stands} Stände, {deltas} Delta-Briefings; Geschichte: {template}{switches}",
        LANG_EN: "Structure: {describe} — {exports} Jira exports, {workbooks} workbooks, {registers} registers, {stands} stands, {deltas} delta briefings; story: {template}{switches}",
        LANG_RO: "Structură: {describe} — {exports} exporturi Jira, {workbooks} registre de lucru, {registers} registre, {stands} stări, {deltas} Delta-Briefing-uri; poveste: {template}{switches}",
        LANG_PT: "Estrutura: {describe} — {exports} exportações Jira, {workbooks} livros de trabalho, {registers} registos, {stands} estados, {deltas} Delta-Briefings; história: {template}{switches}",
        LANG_FR: "Structure : {describe} — {exports} exports Jira, {workbooks} classeurs, {registers} registres, {stands} états, {deltas} Delta-Briefings ; histoire : {template}{switches}",
    },
    "cli.switches": {LANG_DE: ", Schalter {switches}", LANG_EN: ", switches {switches}", LANG_RO: ", comutatoare {switches}",
                     LANG_PT: ", interruptores {switches}", LANG_FR: ", interrupteurs {switches}"},
    "cli.warn": {LANG_DE: "WARNUNG: grosse Struktur ({reason}) — Erzeugung dauert entsprechend.",
                 LANG_EN: "WARNING: large structure ({reason}) — generation takes accordingly.",
                 LANG_RO: "AVERTISMENT: structură mare ({reason}) — generarea durează corespunzător.",
                 LANG_PT: "AVISO: estrutura grande ({reason}) — a geração demora em conformidade.",
                 LANG_FR: "AVERTISSEMENT : structure volumineuse ({reason}) — la génération prend du temps en conséquence."},
    "cli.result": {
        LANG_DE: "Datenraum: {issues} Vorgänge, {registers} Register, {stands} Stände, {deltas} Delta-Briefings, {providers} Quellen-Arten{drafts} — {s} s",
        LANG_EN: "Data room: {issues} items, {registers} registers, {stands} stands, {deltas} delta briefings, {providers} source kinds{drafts} — {s} s",
        LANG_RO: "Spațiu de date: {issues} elemente, {registers} registre, {stands} stări, {deltas} Delta-Briefing-uri, {providers} tipuri de surse{drafts} — {s} s",
        LANG_PT: "Sala de dados: {issues} itens, {registers} registos, {stands} estados, {deltas} Delta-Briefings, {providers} tipos de fontes{drafts} — {s} s",
        LANG_FR: "Espace de données : {issues} éléments, {registers} registres, {stands} états, {deltas} Delta-Briefings, {providers} types de sources{drafts} — {s} s",
    },
    "cli.drafts": {LANG_DE: ", KI-Entwürfe in {n} Ordner(n)", LANG_EN: ", AI drafts in {n} folder(s)", LANG_RO: ", schițe AI în {n} folder(e)",
                   LANG_PT: ", rascunhos de IA em {n} pasta(s)", LANG_FR: ", brouillons IA dans {n} dossier(s)"},
    # --- AI drafts: questions and practice files ---------------------------------------------------------------
    "drafts.q1": {LANG_DE: "Welche Solution braucht in dieser Woche die Aufmerksamkeit des Portfolios?",
                  LANG_EN: "Which solution needs the portfolio's attention this week?",
                  LANG_RO: "Care soluție are nevoie de atenția portofoliului în această săptămână?",
                  LANG_PT: "Que solução precisa da atenção do portfólio esta semana?",
                  LANG_FR: "Quelle solution a besoin de l'attention du portefeuille cette semaine ?"},
    "drafts.q2": {LANG_DE: "Was hat sich seit dem letzten Stand bei den Abhängigkeiten geändert?",
                  LANG_EN: "What changed in the dependencies since the last stand?",
                  LANG_RO: "Ce s-a schimbat la dependențe de la ultima stare?",
                  LANG_PT: "O que mudou nas dependências desde o último estado?",
                  LANG_FR: "Qu'est-ce qui a changé dans les dépendances depuis le dernier état ?"},
    "drafts.q3": {LANG_DE: "Welche Annahme sollten wir vor der nächsten Konferenz prüfen?",
                  LANG_EN: "Which assumption should we check before the next conference?",
                  LANG_RO: "Ce ipoteză ar trebui să verificăm înainte de următoarea conferință?",
                  LANG_PT: "Que pressuposto devemos verificar antes da próxima conferência?",
                  LANG_FR: "Quelle hypothèse devrions-nous vérifier avant la prochaine conférence ?"},
    "drafts.practice_text": {
        LANG_DE: "Der Durchsatz des Portfolios liegt bei 4711 Vorgängen [S1/total.items] und ist damit um 0815 Prozent gestiegen. Solution Alpha ist die beste im Konzern.\n",
        LANG_EN: "The portfolio's throughput stands at 4711 items [S1/total.items], up by 0815 percent. Solution Alpha is the best in the group.\n",
        LANG_RO: "Debitul portofoliului este de 4711 elemente [S1/total.items], în creștere cu 0815 la sută. Soluția Alpha este cea mai bună din grup.\n",
        LANG_PT: "O débito do portfólio está em 4711 itens [S1/total.items], uma subida de 0815 por cento. A Solution Alpha é a melhor do grupo.\n",
        LANG_FR: "Le débit du portefeuille s'établit à 4711 éléments [S1/total.items], en hausse de 0815 pour cent. La Solution Alpha est la meilleure du groupe.\n",
    },
    "drafts.practice_readme": {
        LANG_DE: "# Übung: Rückweg mit `llm check`\n\n`{bundle}` ist ein exportiertes Prompt-Bündel (Export-Weg: Prompt in ein externes Modell kopieren, Antwort zurückholen). `{answer}` ist eine Antwort, wie sie aus einem Modell kommen könnte — mit zwei Zahlen, die nicht im Contract stehen (4711, 0815), und einer Behauptung ohne Zitat.\n\nPrüfen:\n\n    python -m llm check {answer} --bundle {bundle}\n\nErwartung: der Zahlen-Wächter weist beide Zahlen zurück, der Zitat-Wächter die unbelegte Behauptung; nichts wird als Entwurf abgelegt. Dann dieselbe Prüfung mit einer eigenen, belegten Antwort versuchen.\n\nDie anderen Dateien in diesem Ordner sind Mock-Entwürfe (kein Modell): Lagevortrag (`{briefing}`) und drei Antworten (`frage_*.ask.md`), alle mit KI-Marker, nicht freigegeben. Freigabe üben: `python -m llm approve <datei>`.\n",
        LANG_EN: "# Practice: the return path with `llm check`\n\n`{bundle}` is an exported prompt bundle (export path: copy the prompt into an external model, bring the answer back). `{answer}` is an answer as a model might give it — with two numbers that are not in the contract (4711, 0815) and a claim without a citation.\n\nCheck it:\n\n    python -m llm check {answer} --bundle {bundle}\n\nExpected: the numbers guard rejects both numbers, the citation guard the unbacked claim; nothing is stored as a draft. Then try the same check with your own, cited answer.\n\nThe other files in this folder are mock drafts (no model): the spoken briefing (`{briefing}`) and three answers (`frage_*.ask.md`), all carrying the AI marker, none approved. Practise approval: `python -m llm approve <file>`.\n",
        LANG_RO: "# Exercițiu: calea de întoarcere cu `llm check`\n\n`{bundle}` este un pachet de prompt exportat (calea de export: copiați promptul într-un model extern, aduceți răspunsul înapoi). `{answer}` este un răspuns așa cum l-ar putea da un model — cu două numere care nu sunt în contract (4711, 0815) și o afirmație fără citare.\n\nVerificați:\n\n    python -m llm check {answer} --bundle {bundle}\n\nAșteptare: gardianul numerelor respinge ambele numere, gardianul citărilor afirmația nesusținută; nimic nu este stocat ca schiță. Apoi încercați aceeași verificare cu un răspuns propriu, cu citări.\n\nCelelalte fișiere din acest folder sunt schițe mock (fără model): briefingul vorbit (`{briefing}`) și trei răspunsuri (`frage_*.ask.md`), toate cu marcaj AI, niciunul aprobat. Exersați aprobarea: `python -m llm approve <fișier>`.\n",
        LANG_PT: "# Exercício: o caminho de volta com `llm check`\n\n`{bundle}` é um pacote de prompt exportado (caminho de exportação: copiar o prompt para um modelo externo, trazer a resposta de volta). `{answer}` é uma resposta como um modelo a poderia dar — com dois números que não estão no contrato (4711, 0815) e uma afirmação sem citação.\n\nVerificar:\n\n    python -m llm check {answer} --bundle {bundle}\n\nEsperado: o guarda de números rejeita ambos os números, o guarda de citações a afirmação sem base; nada é guardado como rascunho. Depois tente a mesma verificação com uma resposta própria e citada.\n\nOs outros ficheiros nesta pasta são rascunhos mock (sem modelo): o briefing falado (`{briefing}`) e três respostas (`frage_*.ask.md`), todos com marcador de IA, nenhum aprovado. Praticar a aprovação: `python -m llm approve <ficheiro>`.\n",
        LANG_FR: "# Exercice : le chemin de retour avec `llm check`\n\n`{bundle}` est un paquet de prompt exporté (voie d'export : copier le prompt dans un modèle externe, ramener la réponse). `{answer}` est une réponse telle qu'un modèle pourrait la donner — avec deux nombres absents du contrat (4711, 0815) et une affirmation sans citation.\n\nVérifier :\n\n    python -m llm check {answer} --bundle {bundle}\n\nAttendu : le gardien des nombres rejette les deux nombres, le gardien des citations l'affirmation non étayée ; rien n'est enregistré comme brouillon. Puis essayez la même vérification avec votre propre réponse, citée.\n\nLes autres fichiers de ce dossier sont des brouillons mock (sans modèle) : le briefing oral (`{briefing}`) et trois réponses (`frage_*.ask.md`), tous porteurs du marqueur IA, aucun approuvé. S'exercer à l'approbation : `python -m llm approve <fichier>`.\n",
    },
}


def normalise(lang: str | None) -> str:
    return lang if lang in LANGUAGES else DEFAULT_LANG


def t(_key: str, _lang: str | None = DEFAULT_LANG, **kwargs: object) -> str:
    """
    The text for ``_key`` in ``_lang`` with placeholders filled in (the two
    positional names are underscored so that ``key=``/``lang=`` stay free
    as placeholders).

    An unknown key is a programming error (KeyError); an unknown language
    falls back to English, a missing translation of a known key as well.
    """
    entry = _T[_key]
    template = entry.get(normalise(_lang)) or entry[LANG_EN]
    return template.format(**kwargs) if kwargs else template


def keys() -> tuple[str, ...]:
    return tuple(_T)


_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"


def prefs_path() -> Path:
    """``~/.situation_report/prefs.json`` (tests point ``_PREFS_PATH`` elsewhere)."""
    return _PREFS_PATH


def load_lang_pref(default: str = DEFAULT_LANG) -> str:
    """
    The suite-wide language from ``~/.situation_report/prefs.json`` (the
    launcher writes it), or ``default`` when there is none.
    """
    try:
        with open(prefs_path(), encoding="utf-8") as f:
            value = json.load(f).get("lang", default)
    except (OSError, ValueError):
        return normalise(default)
    return value if value in LANGUAGES else normalise(default)


def template_title(template: str, lang: str | None = DEFAULT_LANG) -> str:
    """The display title of a story template (``tpl.<id>``)."""
    return t(f"tpl.{template}", lang)


def step_label(step: str, lang: str | None = DEFAULT_LANG) -> str:
    """The label of a generator step (``step.<id>``); an unknown step is its id."""
    return t(f"step.{step}", lang) if f"step.{step}" in _T else step
