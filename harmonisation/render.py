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
#   trägt nur die Konfidenz.
# =============================================================================

from __future__ import annotations

from datetime import date
from html import escape

from .model import (
    DECISION_BRAND_SPECIFIC,
    DECISION_OPEN,
    DECISION_STANDARDISE,
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
    EVIDENCE_HEARSAY,
    LANGS,
    Assessment,
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
        "footer": "SituationReport · Harmonisierungs-Score · nur Standardbibliothek, deterministisch, ohne KI-Anteil",
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
        "footer": "SituationReport · harmonisation score · standard library only, deterministic, no AI involved",
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
        "footer": "SituationReport · scor de armonizare · doar biblioteca standard, determinist, fără AI",
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
        "footer": "SituationReport · score de harmonização · só biblioteca padrão, determinístico, sem IA",
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
        "footer": "SituationReport · score d'harmonisation · bibliothèque standard uniquement, déterministe, sans IA",
    },
}

_DATE_FORMATS = {"de": "%d.%m.%Y", "ro": "%d.%m.%Y", "pt": "%d/%m/%Y", "fr": "%d/%m/%Y",
                 "en": "%Y-%m-%d"}

#: Score-Abstufung: fünf Blautöne, hell nach dunkel — ein Befund, keine Ampel.
_SCORE_SHADES = ("#f4f7fb", "#dbe6f3", "#b7cde6", "#8fb0d6", "#5f8cc0")
_CONF_COLOURS = {CONFIDENCE_HIGH: "#d9efd9", CONFIDENCE_MEDIUM: "#fff1c9",
                 CONFIDENCE_LOW: "#f6d5d5"}

_CSS = """
body{font-family:"Segoe UI",Calibri,Arial,sans-serif;font-size:14px;color:#23303e;margin:28px auto;max-width:1180px;line-height:1.45}
h1{color:#16304d;font-size:24px;margin:0 0 4px}h2{color:#16304d;font-size:18px;margin:28px 0 8px}
.meta{color:#5b6b7c;font-size:13px;margin:0 0 14px}
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
.note{color:#5b6b7c;font-size:13px}footer{color:#5b6b7c;font-size:12px;margin-top:30px;border-top:1px solid #d9dfe6;padding-top:8px}
"""


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


def render_html(ws: Workspace, lang: str = DEFAULT_LANG, today: date | None = None) -> str:
    """The complete report as one self-contained HTML document."""
    lang = lang if lang in LANGS else "en"
    today = today or date.today()
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
        f"<table><tr><th>{escape(_tr(lang, 'col_process'))}</th>{head}"
        f"<th>{escape(_tr(lang, 'col_decision'))}</th><th>{escape(_tr(lang, 'col_depth'))}</th></tr>"
        f"{''.join(body)}</table>"
        f"<h2>{escape(_tr(lang, 'details_title'))}</h2>{''.join(details)}"
        f"<footer>{escape(_tr(lang, 'footer'))}</footer></body></html>"
    )
