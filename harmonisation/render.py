# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Entscheider-Matrix als HTML, in fünf Sprachen. Oben die Matrix fürs
#   Board — Zeilen Prozesse, Spalten die drei Dimensionen, je Zelle Score,
#   Bewertungen, Konfidenz und Spannweite — daneben die Spalten, die das
#   Board ausfüllt (Entscheidung, Tiefe). Darunter dieselben Zahlen in der
#   zweiten Lesart: je Prozess jede Bewertung mit jeder Antwort und ihrem
#   Beleggrad. Farbschlüssel und Legende stehen VOR der ersten Tabelle
#   (dasselbe Muster wie die Konferenzmappe, 0.31.0). Der Score ist blau
#   abgestuft, nicht Ampel: Er ist ein Befund, kein Urteil. Ampelfarben
#   trägt nur die Konfidenz. Seit Schritt 2 (12.10.2026) außerdem: die
#   Matrix als eingebetteter Block für die Konferenzmappe (CSS auf .harmo
#   begrenzt) und die Seite „Veränderung zweier Stände" nach dem D2-Muster.
# =============================================================================

from __future__ import annotations

from datetime import date
from html import escape

from .delta import HarmonisationDelta
from .model import (
    DECISION_BRAND_SPECIFIC,
    DECISION_OPEN,
    DECISION_STANDARDISE,
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
    EVIDENCE_HEARSAY,
    LANGS,
    Assessment,
    Decision,
    Workspace,
)
from .score import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CellSummary,
    matrix,
    score_dimension,
)

DEFAULT_LANG = "de"

_T: dict[str, dict[str, str]] = {
    "de": {
        "title": "Harmonisierungs-Score — Entscheider-Matrix",
        "generated": "Stand",
        "catalogue": "Katalog",
        "no_judgement": "Die Zahlen sind Befund, kein Urteil: Das Werkzeug empfiehlt weder, was harmonisiert wird, noch in welcher Tiefe. Das trägt das Board in den rechten Spalten ein.",
        "legend_title": "Farbschlüssel",
        "legend_score": "Score 0–100: Mittel der beantworteten Fragen, hohe Werte sprechen für eine Harmonisierung — je dunkler, desto höher.",
        "legend_confidence": "Konfidenz: Anteil belegter Antworten an allen Fragen",
        "legend_spread": "Spanne: Abstand zwischen höchster und niedrigster Bewertung desselben Prozesses — ein Befund, kein Rauschen.",
        "conf_high": "hoch", "conf_medium": "mittel", "conf_low": "niedrig",
        "col_process": "End-to-End-Prozess", "col_owner": "Owner",
        "col_decision": "Entscheidung des Boards", "col_depth": "Tiefe (Wortlaut Board)",
        "cell_assessment": "Bewertung", "cell_assessments": "Bewertungen", "cell_answered": "beantwortet",
        "cell_spread": "Spanne", "cell_none": "keine Bewertung",
        "dec_standardise": "standardisieren", "dec_brand_specific": "markenspezifisch",
        "dec_open": "offen", "dec_date": "am",
        "details_title": "Zweite Lesart: die Antworten",
        "assessment_by": "Bewertung von", "assessment_on": "am",
        "col_question": "Frage", "col_value": "Wert", "col_evidence": "Beleg",
        "ev_documented": "belegt", "ev_estimated": "geschätzt", "ev_hearsay": "Hörensagen",
        "unknown": "unbekannt", "note": "Anmerkung",
        "footer": "SituationReport · Harmonisierungs-Score · Rechnung deterministisch, nur Standardbibliothek; KI-Text steht nur in als Entwurf gekennzeichneten Abschnitten",
        "delta_title": "Harmonisierungs-Score — Veränderung zweier Stände",
        "delta_meta": "Früherer Stand {prev} · späterer Stand {now}",
        "delta_claim": "Ein gesunkener Score ist keine Verschlechterung, sondern ein anderer Befund. Die Tabelle ordnet nach Prozess, nicht nach gut und schlecht.",
        "delta_quiet": "Keine Änderungen zwischen den beiden Ständen.",
        "delta_catalogue": "Achtung: Der Fragenkatalog unterscheidet sich zwischen den Ständen; die Scores sind nicht vergleichbar.",
        "delta_cells": "Veränderte Zellen",
        "col_dimension": "Dimension",
        "col_score": "Score",
        "col_confidence": "Konfidenz",
        "col_spread": "Spanne",
        "col_assessments": "Bewertungen",
        "delta_new_assessments": "Neue Bewertungen",
        "delta_assessment_dated": "Bewertung vom {day}",
        "delta_decisions": "Entscheidungen des Boards",
        "delta_added": "Hinzugekommene Prozesse",
        "delta_removed": "Entfallene Prozesse",
        "delta_undated": "{n} Entscheidung(en) ohne Datum gelten in beiden Ständen als vorhanden.",
        "block_hint": "Auszug aus dem Harmonisierungs-Score; die zweite Lesart mit allen Antworten steht in der Matrix selbst.",
    },
    "en": {
        "title": "Harmonisation score — decision matrix",
        "generated": "As of",
        "catalogue": "Catalogue",
        "no_judgement": "The numbers are a finding, not a judgement: the tool recommends neither what to harmonise nor how deep. The board enters that in the columns on the right.",
        "legend_title": "Colour key",
        "legend_score": "Score 0–100: mean of the answered questions, high values speak for harmonisation — the darker, the higher.",
        "legend_confidence": "Confidence: share of documented answers over all questions",
        "legend_spread": "Spread: distance between the highest and lowest assessment of the same process — a finding, not noise.",
        "conf_high": "high", "conf_medium": "medium", "conf_low": "low",
        "col_process": "End-to-end process", "col_owner": "Owner",
        "col_decision": "Board decision", "col_depth": "Depth (board's wording)",
        "cell_assessment": "assessment", "cell_assessments": "assessments", "cell_answered": "answered",
        "cell_spread": "spread", "cell_none": "no assessment",
        "dec_standardise": "standardise", "dec_brand_specific": "brand-specific",
        "dec_open": "open", "dec_date": "on",
        "details_title": "Second reading: the answers",
        "assessment_by": "Assessment by", "assessment_on": "on",
        "col_question": "Question", "col_value": "Value", "col_evidence": "Evidence",
        "ev_documented": "documented", "ev_estimated": "estimated", "ev_hearsay": "hearsay",
        "unknown": "unknown", "note": "Note",
        "footer": "SituationReport · harmonisation score · computation deterministic, standard library only; AI text appears only in sections labeled as drafts",
        "delta_title": "Harmonisation score — change between two states",
        "delta_meta": "Earlier state {prev} · later state {now}",
        "delta_claim": "A lower score is not a worsening but a different finding. The table is ordered by process, not by good and bad.",
        "delta_quiet": "No changes between the two states.",
        "delta_catalogue": "Warning: the question catalogue differs between the states; the scores are not comparable.",
        "delta_cells": "Changed cells",
        "col_dimension": "Dimension",
        "col_score": "Score",
        "col_confidence": "Confidence",
        "col_spread": "Spread",
        "col_assessments": "Assessments",
        "delta_new_assessments": "New assessments",
        "delta_assessment_dated": "assessment dated {day}",
        "delta_decisions": "Board decisions",
        "delta_added": "Processes added",
        "delta_removed": "Processes removed",
        "delta_undated": "{n} board decision(s) without a date count as present in both states.",
        "block_hint": "Excerpt from the harmonisation score; the second reading with every answer is in the matrix itself.",
    },
    "ro": {
        "title": "Scor de armonizare — matricea decidenților",
        "generated": "Stare la",
        "catalogue": "Catalog",
        "no_judgement": "Cifrele sunt o constatare, nu o judecată: instrumentul nu recomandă nici ce se armonizează, nici cât de adânc. Board-ul completează acestea în coloanele din dreapta.",
        "legend_title": "Legenda culorilor",
        "legend_score": "Scor 0–100: media întrebărilor cu răspuns, valorile mari pledează pentru armonizare — cu cât mai închis, cu atât mai mare.",
        "legend_confidence": "Încredere: ponderea răspunsurilor documentate din toate întrebările",
        "legend_spread": "Interval: distanța dintre cea mai mare și cea mai mică evaluare a aceluiași proces — o constatare, nu zgomot.",
        "conf_high": "ridicată", "conf_medium": "medie", "conf_low": "scăzută",
        "col_process": "Proces end-to-end", "col_owner": "Responsabil",
        "col_decision": "Decizia board-ului", "col_depth": "Profunzime (formularea board-ului)",
        "cell_assessment": "evaluare", "cell_assessments": "evaluări", "cell_answered": "cu răspuns",
        "cell_spread": "interval", "cell_none": "nicio evaluare",
        "dec_standardise": "standardizare", "dec_brand_specific": "specific mărcii",
        "dec_open": "deschis", "dec_date": "la",
        "details_title": "A doua lectură: răspunsurile",
        "assessment_by": "Evaluare de", "assessment_on": "la",
        "col_question": "Întrebare", "col_value": "Valoare", "col_evidence": "Dovadă",
        "ev_documented": "documentat", "ev_estimated": "estimat", "ev_hearsay": "din auzite",
        "unknown": "necunoscut", "note": "Notă",
        "footer": "SituationReport · scor de armonizare · calcul determinist, doar biblioteca standard; text AI apare doar în secțiuni marcate ca schiță",
        "delta_title": "Scor de armonizare — schimbarea între două stări",
        "delta_meta": "Stare anterioară {prev} · stare ulterioară {now}",
        "delta_claim": "Un scor mai mic nu este o înrăutățire, ci o altă constatare. Tabelul este ordonat după proces, nu după bine și rău.",
        "delta_quiet": "Nicio schimbare între cele două stări.",
        "delta_catalogue": "Atenție: catalogul de întrebări diferă între stări; scorurile nu sunt comparabile.",
        "delta_cells": "Celule modificate",
        "col_dimension": "Dimensiune",
        "col_score": "Scor",
        "col_confidence": "Încredere",
        "col_spread": "Interval",
        "col_assessments": "Evaluări",
        "delta_new_assessments": "Evaluări noi",
        "delta_assessment_dated": "evaluare din {day}",
        "delta_decisions": "Deciziile board-ului",
        "delta_added": "Procese adăugate",
        "delta_removed": "Procese eliminate",
        "delta_undated": "{n} decizie(i) fără dată se consideră prezente în ambele stări.",
        "block_hint": "Extras din scorul de armonizare; a doua lectură cu toate răspunsurile se află în matricea însăși.",
    },
    "pt": {
        "title": "Score de harmonização — matriz de decisão",
        "generated": "Estado em",
        "catalogue": "Catálogo",
        "no_judgement": "Os números são um resultado, não um juízo: a ferramenta não recomenda o que harmonizar nem em que profundidade. Isso é o board que regista nas colunas à direita.",
        "legend_title": "Chave de cores",
        "legend_score": "Score 0–100: média das perguntas respondidas, valores altos apontam para harmonização — quanto mais escuro, mais alto.",
        "legend_confidence": "Confiança: proporção de respostas documentadas em todas as perguntas",
        "legend_spread": "Amplitude: distância entre a avaliação mais alta e a mais baixa do mesmo processo — um resultado, não ruído.",
        "conf_high": "alta", "conf_medium": "média", "conf_low": "baixa",
        "col_process": "Processo end-to-end", "col_owner": "Responsável",
        "col_decision": "Decisão do board", "col_depth": "Profundidade (palavras do board)",
        "cell_assessment": "avaliação", "cell_assessments": "avaliações", "cell_answered": "respondidas",
        "cell_spread": "amplitude", "cell_none": "sem avaliação",
        "dec_standardise": "padronizar", "dec_brand_specific": "específico da marca",
        "dec_open": "em aberto", "dec_date": "em",
        "details_title": "Segunda leitura: as respostas",
        "assessment_by": "Avaliação de", "assessment_on": "em",
        "col_question": "Pergunta", "col_value": "Valor", "col_evidence": "Evidência",
        "ev_documented": "documentado", "ev_estimated": "estimado", "ev_hearsay": "por ouvir dizer",
        "unknown": "desconhecido", "note": "Nota",
        "footer": "SituationReport · score de harmonização · cálculo determinístico, só biblioteca padrão; texto de IA só em secções marcadas como rascunho",
        "delta_title": "Score de harmonização — alteração entre dois estados",
        "delta_meta": "Estado anterior {prev} · estado posterior {now}",
        "delta_claim": "Um score mais baixo não é uma piora, mas um resultado diferente. A tabela está ordenada por processo, não por bom e mau.",
        "delta_quiet": "Sem alterações entre os dois estados.",
        "delta_catalogue": "Atenção: o catálogo de perguntas difere entre os estados; os scores não são comparáveis.",
        "delta_cells": "Células alteradas",
        "col_dimension": "Dimensão",
        "col_score": "Score",
        "col_confidence": "Confiança",
        "col_spread": "Amplitude",
        "col_assessments": "Avaliações",
        "delta_new_assessments": "Novas avaliações",
        "delta_assessment_dated": "avaliação de {day}",
        "delta_decisions": "Decisões do board",
        "delta_added": "Processos adicionados",
        "delta_removed": "Processos removidos",
        "delta_undated": "{n} decisão(ões) sem data contam como presentes em ambos os estados.",
        "block_hint": "Excerto do score de harmonização; a segunda leitura com todas as respostas está na própria matriz.",
    },
    "fr": {
        "title": "Score d'harmonisation — matrice de décision",
        "generated": "État au",
        "catalogue": "Catalogue",
        "no_judgement": "Les chiffres sont un constat, pas un jugement : l'outil ne recommande ni quoi harmoniser ni à quelle profondeur. C'est le board qui l'inscrit dans les colonnes de droite.",
        "legend_title": "Code couleur",
        "legend_score": "Score 0–100 : moyenne des questions répondues, les valeurs élevées plaident pour une harmonisation — plus c'est foncé, plus c'est élevé.",
        "legend_confidence": "Confiance : part des réponses documentées sur l'ensemble des questions",
        "legend_spread": "Écart : distance entre l'évaluation la plus haute et la plus basse du même processus — un constat, pas du bruit.",
        "conf_high": "élevée", "conf_medium": "moyenne", "conf_low": "faible",
        "col_process": "Processus de bout en bout", "col_owner": "Responsable",
        "col_decision": "Décision du board", "col_depth": "Profondeur (termes du board)",
        "cell_assessment": "évaluation", "cell_assessments": "évaluations", "cell_answered": "répondues",
        "cell_spread": "écart", "cell_none": "aucune évaluation",
        "dec_standardise": "standardiser", "dec_brand_specific": "propre à la marque",
        "dec_open": "ouvert", "dec_date": "le",
        "details_title": "Deuxième lecture : les réponses",
        "assessment_by": "Évaluation par", "assessment_on": "le",
        "col_question": "Question", "col_value": "Valeur", "col_evidence": "Preuve",
        "ev_documented": "documenté", "ev_estimated": "estimé", "ev_hearsay": "par ouï-dire",
        "unknown": "inconnu", "note": "Remarque",
        "footer": "SituationReport · score d'harmonisation · calcul déterministe, bibliothèque standard uniquement ; du texte IA n'apparaît que dans des sections marquées comme brouillon",
        "delta_title": "Score d'harmonisation — évolution entre deux états",
        "delta_meta": "État antérieur {prev} · état postérieur {now}",
        "delta_claim": "Un score plus bas n'est pas une dégradation mais un autre constat. Le tableau est ordonné par processus, non par bon et mauvais.",
        "delta_quiet": "Aucun changement entre les deux états.",
        "delta_catalogue": "Attention : le catalogue de questions diffère entre les états ; les scores ne sont pas comparables.",
        "delta_cells": "Cellules modifiées",
        "col_dimension": "Dimension",
        "col_score": "Score",
        "col_confidence": "Confiance",
        "col_spread": "Écart",
        "col_assessments": "Évaluations",
        "delta_new_assessments": "Nouvelles évaluations",
        "delta_assessment_dated": "évaluation du {day}",
        "delta_decisions": "Décisions du board",
        "delta_added": "Processus ajoutés",
        "delta_removed": "Processus retirés",
        "delta_undated": "{n} décision(s) sans date comptent comme présentes dans les deux états.",
        "block_hint": "Extrait du score d'harmonisation ; la deuxième lecture avec toutes les réponses se trouve dans la matrice elle-même.",
    },
}

_DATE_FORMATS = {"de": "%d.%m.%Y", "ro": "%d.%m.%Y", "pt": "%d/%m/%Y", "fr": "%d/%m/%Y",
                 "en": "%Y-%m-%d"}

#: Score-Abstufung: fünf Blautöne, hell nach dunkel — ein Befund, keine Ampel.
_SCORE_SHADES = ("#f4f7fb", "#dbe6f3", "#b7cde6", "#8fb0d6", "#5f8cc0")
_CONF_COLOURS = {CONFIDENCE_HIGH: "#d9efd9", CONFIDENCE_MEDIUM: "#fff1c9",
                 CONFIDENCE_LOW: "#f6d5d5"}

_PAGE_CSS = """
body{font-family:"Segoe UI",Calibri,Arial,sans-serif;font-size:14px;color:#23303e;margin:28px auto;max-width:1180px;line-height:1.45}
h1{color:#16304d;font-size:24px;margin:0 0 4px}h2{color:#16304d;font-size:18px;margin:28px 0 8px}
.meta{color:#5b6b7c;font-size:13px;margin:0 0 14px}
.quiet{background:#e6f4e6;border-left:4px solid #1e8449;padding:8px 12px;margin:0 0 16px}
footer{color:#5b6b7c;font-size:12px;margin-top:30px;border-top:1px solid #d9dfe6;padding-top:8px}
"""

#: Rules every rendering shares — the page uses them as they are, the embedded
#: block (Konferenzmappe) gets them scoped to .harmo so the host page's tables
#: keep their own look.
_CORE_CSS = """
.claim{background:#eef3f8;border-left:4px solid #9a3412;padding:8px 12px;margin:0 0 16px;color:#16304d}
.legend{border:1px solid #d9dfe6;border-radius:6px;padding:8px 12px;margin:0 0 16px;font-size:13px}
.legend .k{font-weight:700;color:#9a3412;margin-right:6px}
.swatch{display:inline-block;width:18px;height:12px;border:1px solid #c9d2dc;vertical-align:middle;margin:0 1px}
.badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:12px;border:1px solid #c9d2dc}
table{border-collapse:collapse;width:100%;margin:0 0 10px}
th{background:#16304d;color:#fff;text-align:left;padding:6px 8px;font-size:13px}
td{border:1px solid #d9dfe6;padding:6px 8px;vertical-align:top}
td.cell{text-align:center;min-width:120px}td.cell .s{font-size:20px;font-weight:700;color:#16304d}
td.cell .m{font-size:12px;color:#5b6b7c}td.none{color:#5b6b7c;font-style:italic;text-align:center}
td.dec{min-width:130px}.dec b{color:#16304d}
.detail th{background:#5b6b7c}.detail td.v{text-align:center;width:60px}
.note{color:#5b6b7c;font-size:13px}
td.chg{white-space:nowrap}td.chg b{color:#16304d}
"""

_CSS = _PAGE_CSS + _CORE_CSS


def _scoped(css: str, scope: str = ".harmo") -> str:
    """Prefix every selector of ``css`` with ``scope`` (rules are brace-delimited)."""
    out: list[str] = []
    for chunk in css.split("}"):
        chunk = chunk.strip()
        if not chunk:
            continue
        selectors, body = chunk.split("{", 1)
        scoped = ",".join(f"{scope} {s.strip()}" for s in selectors.split(","))
        out.append(f"{scoped}{{{body}}}")
    return "".join(out)


_BLOCK_CSS = (".harmo{font-size:14px;color:#23303e;line-height:1.45}"
              ".harmo h3{color:#16304d;font-size:16px;margin:14px 0 6px}" + _scoped(_CORE_CSS))


def _tr(lang: str, key: str) -> str:
    return _T.get(lang, _T["en"]).get(key) or _T["en"][key]


def _fmt_date(d: date | None, lang: str) -> str:
    return d.strftime(_DATE_FORMATS.get(lang, "%Y-%m-%d")) if d else ""


def _shade(score: float) -> str:
    idx = min(int(score // 20), len(_SCORE_SHADES) - 1)
    return _SCORE_SHADES[idx]


def _score_cell(cell: CellSummary, lang: str) -> str:
    if cell.score is None:
        return f'<td class="none">{escape(_tr(lang, "cell_none"))}</td>'
    conf = _tr(lang, "conf_" + cell.confidence)
    spread = ""
    if cell.spread is not None:
        spread = f' · {escape(_tr(lang, "cell_spread"))} {cell.spread:g}'
    # Auf den beiden dunklen Blautönen trägt nur weiße Schrift genug Kontrast.
    ink = ' style="color:#fff"' if cell.score >= 60 else ""
    count_key = "cell_assessment" if cell.assessments == 1 else "cell_assessments"
    return (f'<td class="cell" style="background:{_shade(cell.score)}">'
            f'<div class="s"{ink}>{cell.score:g}</div>'
            f'<div class="m"{ink}>{cell.assessments} {escape(_tr(lang, count_key))} · '
            f'{cell.answered}/{cell.total} {escape(_tr(lang, "cell_answered"))}{spread}</div>'
            f'<div class="m"><span class="badge" style="background:{_CONF_COLOURS[cell.confidence]}">'
            f'{escape(conf)}</span></div></td>')


def _decision_cells(ws: Workspace, pid: str, lang: str) -> str:
    d = ws.decisions.get(pid)
    if d is None or d.decision == DECISION_OPEN and not d.depth:
        label = _tr(lang, "dec_open")
        return f'<td class="dec">{escape(label)}</td><td class="dec"></td>'
    key = {DECISION_STANDARDISE: "dec_standardise", DECISION_BRAND_SPECIFIC: "dec_brand_specific",
           DECISION_OPEN: "dec_open"}[d.decision]
    when = f' <span class="note">{escape(_tr(lang, "dec_date"))} {escape(_fmt_date(d.day, lang))}' \
           f'{" · " + escape(d.body) if d.body else ""}</span>' if (d.day or d.body) else ""
    return (f'<td class="dec"><b>{escape(_tr(lang, key))}</b>{when}</td>'
            f'<td class="dec">{escape(d.depth)}</td>')


def _legend(ws: Workspace, lang: str) -> str:
    swatches = "".join(f'<span class="swatch" style="background:{c}"></span>' for c in _SCORE_SHADES)
    confs = " ".join(
        f'<span class="badge" style="background:{_CONF_COLOURS[c]}">{escape(_tr(lang, "conf_" + c))}</span>'
        for c in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW))
    return (f'<div class="legend"><div><span class="k">{escape(_tr(lang, "legend_title"))}</span></div>'
            f'<div>{swatches} {escape(_tr(lang, "legend_score"))}</div>'
            f'<div>{confs} {escape(_tr(lang, "legend_confidence"))}</div>'
            f'<div>{escape(_tr(lang, "legend_spread"))}</div></div>')


def _assessment_table(ws: Workspace, a: Assessment, lang: str) -> str:
    ev_label = {EVIDENCE_DOCUMENTED: "ev_documented", EVIDENCE_ESTIMATED: "ev_estimated",
                EVIDENCE_HEARSAY: "ev_hearsay"}
    rows: list[str] = []
    for dim in ws.catalogue.dimensions:
        ds = score_dimension(a, dim)
        score = f"{ds.score:g}" if ds.score is not None else "–"
        rows.append(f'<tr><th colspan="3">{escape(dim.label(lang))} · {score} · '
                    f'{ds.answered}/{ds.total} {escape(_tr(lang, "cell_answered"))} · '
                    f'{escape(_tr(lang, "conf_" + ds.confidence))}</th></tr>')
        for q in dim.questions:
            ans = a.answers.get(q.id)
            if ans is None or ans.value is None:
                value, evidence = _tr(lang, "unknown"), ""
            else:
                value, evidence = str(ans.value), _tr(lang, ev_label[ans.evidence])
            rows.append(f'<tr><td>{escape(q.label(lang))}</td><td class="v">{escape(value)}</td>'
                        f'<td>{escape(evidence)}</td></tr>')
    note = f'<p class="note">{escape(_tr(lang, "note"))}: {escape(a.note)}</p>' if a.note else ""
    return (f'<h3>{escape(_tr(lang, "assessment_by"))} {escape(a.assessor or "–")} '
            f'{escape(_tr(lang, "assessment_on"))} {escape(_fmt_date(a.day, lang))}</h3>'
            f'<table class="detail"><tr><th>{escape(_tr(lang, "col_question"))}</th>'
            f'<th>{escape(_tr(lang, "col_value"))}</th><th>{escape(_tr(lang, "col_evidence"))}</th></tr>'
            f'{"".join(rows)}</table>{note}')


def _matrix_table(ws: Workspace, lang: str) -> str:
    """The decision matrix itself: processes × dimensions plus the board's columns."""
    cells = matrix(ws)
    dims = ws.catalogue.dimensions
    head = "".join(f"<th>{escape(d.label(lang))}</th>" for d in dims)
    body: list[str] = []
    for p in ws.processes:
        owner = f'<div class="note">{escape(p.owner)}</div>' if p.owner else ""
        brands = f'<div class="note">{escape(", ".join(p.brands))}</div>' if p.brands else ""
        body.append(f"<tr><td><b>{escape(p.name)}</b>{owner}{brands}</td>"
                    + "".join(_score_cell(cells[p.id][d.id], lang) for d in dims)
                    + _decision_cells(ws, p.id, lang) + "</tr>")
    return (f"<table><tr><th>{escape(_tr(lang, 'col_process'))}</th>{head}"
            f"<th>{escape(_tr(lang, 'col_decision'))}</th><th>{escape(_tr(lang, 'col_depth'))}</th></tr>"
            f"{''.join(body)}</table>")


def render_matrix_block(ws: Workspace, lang: str = DEFAULT_LANG,
                        heading: str | None = None) -> str:
    """
    The matrix as an embeddable block (Konferenzmappe): claim, legend and
    table with their CSS scoped to ``.harmo``, so the host page keeps its
    own table styling. ``heading`` names the source solution when a
    portfolio brings several workspaces.
    """
    lang = lang if lang in LANGS else "en"
    cat = ws.catalogue
    title = f"<h3>{escape(heading)}</h3>" if heading else ""
    cat_note = f" · {escape(cat.note)}" if cat.note else ""
    return (f'<div class="harmo"><style>{_BLOCK_CSS}</style>{title}'
            f'<p class="note">{escape(_tr(lang, "catalogue"))}: {escape(cat.name)}{cat_note} · '
            f'{escape(_tr(lang, "block_hint"))}</p>'
            f'<div class="claim">{escape(_tr(lang, "no_judgement"))}</div>'
            f"{_legend(ws, lang)}{_matrix_table(ws, lang)}</div>")


def render_html(ws: Workspace, lang: str = DEFAULT_LANG, today: date | None = None) -> str:
    """The complete report as one self-contained HTML document."""
    lang = lang if lang in LANGS else "en"
    today = today or date.today()

    details: list[str] = []
    for p in ws.processes:
        mine = [a for a in ws.assessments if a.process == p.id]
        if not mine:
            continue
        details.append(f"<h2>{escape(p.name)}</h2>")
        details.extend(_assessment_table(ws, a, lang) for a in sorted(mine, key=lambda a: a.day))

    cat = ws.catalogue
    cat_note = f' <span class="note">{escape(cat.note)}</span>' if cat.note else ""
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        f"<title>{escape(_tr(lang, 'title'))}</title><style>{_CSS}</style></head><body>"
        f"<h1>{escape(_tr(lang, 'title'))}</h1>"
        f'<p class="meta">{escape(_tr(lang, "generated"))} {escape(_fmt_date(today, lang))} · '
        f"{escape(_tr(lang, 'catalogue'))}: {escape(cat.name)}{cat_note}</p>"
        f'<div class="claim">{escape(_tr(lang, "no_judgement"))}</div>'
        f"{_legend(ws, lang)}"
        f"{_matrix_table(ws, lang)}"
        f"<h2>{escape(_tr(lang, 'details_title'))}</h2>{''.join(details)}"
        f"<footer>{escape(_tr(lang, 'footer'))}</footer></body></html>"
    )


# ---------------------------------------------------------------------------
# Veränderung zweier Stände (P3 Schritt 2)
# ---------------------------------------------------------------------------

def _num(value: float | None) -> str:
    return "–" if value is None else f"{value:g}"


def _conf(value: str, lang: str) -> str:
    return _tr(lang, "conf_" + value) if value else "–"


def _pair(old: str, new: str) -> str:
    return f"{escape(old)} → <b>{escape(new)}</b>"


def _decision_label(d: Decision | None, lang: str) -> str:
    if d is None or (d.decision == DECISION_OPEN and not d.depth):
        return _tr(lang, "dec_open")
    key = {DECISION_STANDARDISE: "dec_standardise", DECISION_BRAND_SPECIFIC: "dec_brand_specific",
           DECISION_OPEN: "dec_open"}[d.decision]
    text = _tr(lang, key)
    if d.depth:
        text += f" („{d.depth}“)" if lang == "de" else f' ("{d.depth}")'
    if d.day:
        text += f" {_tr(lang, 'dec_date')} {_fmt_date(d.day, lang)}"
    return text


def render_delta_html(delta: HarmonisationDelta, now: Workspace, lang: str = DEFAULT_LANG,
                      today: date | None = None) -> str:
    """
    The change between two states as one self-contained HTML page. Cells
    in process order; 'no changes' is said explicitly, so a quiet page is
    never mistaken for one that was not computed.
    """
    lang = lang if lang in LANGS else "en"
    today = today or date.today()
    dim_label = {d.id: d.label(lang) for d in now.catalogue.dimensions}
    parts: list[str] = []
    if delta.quiet:
        parts.append(f'<p class="quiet">{escape(_tr(lang, "delta_quiet"))}</p>')
    if delta.catalogue_changed:
        parts.append(f'<div class="claim">{escape(_tr(lang, "delta_catalogue"))}</div>')
    if delta.cells:
        rows = "".join(
            f"<tr><td><b>{escape(now.process(c.process).name)}</b></td>"
            f"<td>{escape(dim_label.get(c.dimension, c.dimension))}</td>"
            f'<td class="chg">{_pair(_num(c.score[0]), _num(c.score[1]))}</td>'
            f'<td class="chg">{_pair(_conf(c.confidence[0], lang), _conf(c.confidence[1], lang))}</td>'
            f'<td class="chg">{_pair(_num(c.spread[0]), _num(c.spread[1]))}</td>'
            f'<td class="chg">{_pair(str(c.assessments[0]), str(c.assessments[1]))}</td></tr>'
            for c in delta.cells)
        parts.append(
            f"<h2>{escape(_tr(lang, 'delta_cells'))}</h2><table><tr>"
            f"<th>{escape(_tr(lang, 'col_process'))}</th><th>{escape(_tr(lang, 'col_dimension'))}</th>"
            f"<th>{escape(_tr(lang, 'col_score'))}</th><th>{escape(_tr(lang, 'col_confidence'))}</th>"
            f"<th>{escape(_tr(lang, 'col_spread'))}</th><th>{escape(_tr(lang, 'col_assessments'))}</th>"
            f"</tr>{rows}</table>")
    if delta.new_assessments:
        items = "".join(
            f"<li><b>{escape(now.process(n.process).name)}</b>: "
            f"{escape(_tr(lang, 'delta_assessment_dated').format(day=_fmt_date(n.day, lang)))}</li>"
            for n in delta.new_assessments)
        parts.append(f"<h2>{escape(_tr(lang, 'delta_new_assessments'))}</h2><ul>{items}</ul>")
    if delta.decisions:
        items = "".join(
            f"<li><b>{escape(now.process(d.process).name)}</b>: "
            f"{_pair(_decision_label(d.old, lang), _decision_label(d.new, lang))}</li>"
            for d in delta.decisions)
        parts.append(f"<h2>{escape(_tr(lang, 'delta_decisions'))}</h2><ul>{items}</ul>")
    for key, names in (("delta_added", delta.added_processes),
                       ("delta_removed", delta.removed_processes)):
        if names:
            items = "".join(f"<li>{escape(n)}</li>" for n in names)
            parts.append(f"<h2>{escape(_tr(lang, key))}</h2><ul>{items}</ul>")
    if delta.undated_decisions:
        parts.append(f'<p class="note">'
                     f'{escape(_tr(lang, "delta_undated").format(n=delta.undated_decisions))}</p>')

    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        f"<title>{escape(_tr(lang, 'delta_title'))}</title><style>{_CSS}</style></head><body>"
        f"<h1>{escape(_tr(lang, 'delta_title'))}</h1>"
        f'<p class="meta">{escape(_tr(lang, "generated"))} {escape(_fmt_date(today, lang))} · '
        f"{escape(_tr(lang, 'delta_meta').format(prev=delta.label_prev, now=delta.label_now))} · "
        f"{escape(_tr(lang, 'catalogue'))}: {escape(now.catalogue.name)}</p>"
        f'<div class="claim">{escape(_tr(lang, "delta_claim"))}</div>'
        f"{''.join(parts)}"
        f"<footer>{escape(_tr(lang, 'footer'))}</footer></body></html>"
    )
