# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Die Seite der Browser-Oberfläche (Beta, Schnitt 3b) — eine HTML-Datei
#   mit eingebettetem CSS und JavaScript ohne Bibliotheken, aus dem
#   Design-Prototyp (Artifact, Stand 7) übernommen: drei Schritte, ein
#   Hauptknopf, Fortschrittsliste, Ergebniskarte mit Delta-Vergleichswähler.
#
#   UX read (ux-preflight, 26.10.2026): Nutzer = Trainer, Vorführender,
#   Testnutzer; Ziel = in unter einer Minute ein Datenraum mit erzählbarer
#   Lage, und wissen, was danach zu öffnen ist. Primäre Aktion „Datenraum
#   erzeugen". Gesetze: Goal-Gradient (drei benannte Schritte, Stand oben),
#   Hick/Pareto (vier Vorlagen, eine empfohlen, Details zugeklappt), Tesler
#   (Komplexität in Vorlagen und Vorgaben), Doherty/Feedback (Fortschritt je
#   Teilschritt, Abbruch, Fehler neben dem Schritt), Peak-End (Ergebnis mit
#   den nächsten Aktionen), Fitts (Hauptknopf 48 px, Bedienelemente ≥ 36 px,
#   Zeilenhöhe ≥ 44 px), Jakob (Radio, Schieberegler, Schritte wie gewohnt).
#   Nicht ausgeliefert: Feldwand, gleichgewichtige Knöpfe, Erfolg ohne
#   nächsten Schritt. Zustände: leer, Vorschau, läuft, abgebrochen, Fehler,
#   fertig, Ordner nicht leer (Rückfrage).
#
#   UX read Sprachumschalter (30.10.2026): Jakob (Select oben rechts im Kopf,
#   Sprachnamen in Eigenschreibweise, Handbuch-Link folgt), Postel (?lang=
#   unbekannt → Sprache bleibt), Tesler (Start in der Suite-Sprache), Doherty
#   (Neuladen der Seite unter 400 ms, kein Zustand verloren außer Eingaben
#   der Sitzung — die Seite warnt nicht, weil sie vor dem ersten Schritt
#   gewechselt wird; Umschalten während eines laufenden Auftrags lässt den
#   Server weiterarbeiten, die Fortschrittsliste holt ihn nach dem Laden ab).
# =============================================================================

from __future__ import annotations

import json

from .texts import LANGUAGE_NAMES, MANUALS, texts_for

_CSS = """
:root{--bg:#f3f5f8;--card:#fff;--line:#d9dee6;--line2:#c9d2dd;--ink:#23303e;--mute:#5b6b7c;
--pri:#1f6fa8;--pri-dark:#174f78;--pri-soft:#e3eef7;--pri-soft2:#d8e8f5;--ok:#2e8b57;--warn:#b7791f;--bad:#b23a48}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:"Segoe UI",system-ui,sans-serif;color:var(--ink);font-size:15px;line-height:1.45}
a{color:var(--pri)}a:hover{color:var(--pri-dark)}
button,input,select{font:inherit;color:inherit}
header{display:flex;align-items:center;gap:16px;padding:14px 32px;background:var(--card);border-bottom:1px solid var(--line);flex-wrap:wrap}
.uilang{margin-left:auto}.uilang select{padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.brand{font-size:20px;font-weight:700}.beta{font-size:13px;color:var(--mute)}
nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
nav a{padding:8px 14px;border-radius:6px;color:var(--ink);text-decoration:none;min-height:44px;display:inline-flex;align-items:center}
nav a[aria-current=page]{background:var(--pri-soft);color:var(--pri-dark);font-weight:600}
.steps{display:flex;align-items:center;padding:18px 32px 0;flex-wrap:wrap;gap:0}
.step{display:flex;align-items:center;gap:10px;color:var(--mute);background:none;border:0;padding:4px 2px;cursor:pointer;min-height:44px}
.step[aria-current=step]{color:var(--ink);font-weight:700}
.dot{width:32px;height:32px;border-radius:50%;border:2px solid var(--line2);display:inline-flex;align-items:center;justify-content:center;font-weight:700}
.step[aria-current=step] .dot{background:var(--pri);border-color:var(--pri);color:#fff}
.step.done .dot{background:var(--pri-soft2);border-color:var(--pri-soft2);color:var(--pri-dark)}
.bar{width:72px;height:2px;background:var(--line2);margin:0 14px}.bar.done{background:var(--pri)}
.stepof{margin-left:auto;font-size:13px;color:var(--mute)}
main{display:flex;flex-wrap:wrap;gap:24px;padding:20px 32px 32px;align-items:flex-start}
section.col{flex:999 1 560px;min-width:0;display:flex;flex-direction:column;gap:16px}
aside.col{flex:1 1 330px;min-width:0;display:flex;flex-direction:column;gap:14px}
h1{margin:0;font-size:22px}h2{margin:0;font-size:16px}
.lead{margin:0;color:var(--mute)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.tpl{display:flex;gap:12px;padding:14px;border:1px solid var(--line2);border-radius:8px;background:var(--card);cursor:pointer;min-height:44px}
.tpl.sel{border:2px solid var(--pri);background:#f2f8fd}
.tpl input{margin-top:4px;width:18px;height:18px;flex:none}
.pill{font-size:12px;font-weight:700;color:var(--pri-dark);background:var(--pri-soft2);padding:2px 8px;border-radius:10px;margin-left:6px}
.sub{color:var(--mute);font-size:14px}.small{font-size:13px;color:var(--mute)}
table.ev{width:100%;border-collapse:collapse;font-size:14px}
table.ev th{text-align:left;color:var(--mute);font-weight:600;padding:4px 8px}
table.ev td{padding:6px 8px;border-top:1px solid var(--line);vertical-align:top}
table.ev tr.off td{color:var(--mute)}
table.ev input{width:20px;height:20px}
.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.btn{min-height:44px;padding:0 16px;border-radius:6px;border:1px solid var(--line2);background:var(--card);color:var(--ink);cursor:pointer}
.btn.primary{background:var(--pri);border-color:var(--pri);color:#fff;font-weight:600;padding:0 22px}
.btn.big{min-height:48px;padding:0 26px;font-weight:700;font-size:16px}
.btn.ghost{border-style:dashed;color:var(--pri-dark);font-size:13px;min-height:36px;padding:0 12px}
.btn.sm{min-height:36px;min-width:36px;padding:0 10px;font-size:14px}
.btn:disabled{opacity:.55;cursor:default}
input[type=text],input[type=number],input[type=date],select{min-height:44px;padding:0 10px;border:1px solid var(--line2);border-radius:6px;background:var(--card)}
.sm input[type=text],input.sm,select.sm{min-height:36px;font-size:14px}
input[type=range]{width:100%;height:44px}
.pf{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--bg);border-radius:6px}
.sol{padding-left:14px;border-left:2px solid var(--line2);display:flex;flex-direction:column;gap:8px}
.cnt{min-width:28px;text-align:center;font-weight:700}
.notice{padding:8px 10px;background:#fff7e6;border:1px solid #f0d9a8;border-radius:6px;font-size:13px}
.alert{padding:10px 12px;background:#fdecee;border:1px solid #efb6bd;border-radius:6px}
.okbox{border:2px solid var(--ok)}
.nums{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;font-size:14px}
.num{padding:10px 12px;background:var(--bg);border-radius:6px}.num b{display:block;font-size:22px}
ol.prog{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 24px;font-size:14px}
ol.prog li{display:flex;gap:10px;align-items:center;min-height:28px}
ol.prog li .t{margin-left:auto;color:var(--mute)}
.mark{width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex:none;border:2px solid var(--line2)}
.mark.done{background:var(--ok);border-color:var(--ok);color:#fff}
.mark.run{border:3px solid var(--pri);border-top-color:transparent;animation:spin 1s linear infinite}
.mark.skip{border-style:dashed}.mark.fail{background:var(--bad);border-color:var(--bad);color:#fff}
@keyframes spin{to{transform:rotate(360deg)}}
.pbar{height:8px;border-radius:4px;background:#e4e9ef;overflow:hidden}.pbar div{height:100%;background:var(--pri)}
pre.list{font-family:Consolas,"Courier New",monospace;font-size:13px;line-height:1.6;white-space:pre-wrap;margin:0}
footer{margin-top:auto;display:flex;align-items:center;gap:12px;padding:16px 32px;background:var(--card);border-top:1px solid var(--line);flex-wrap:wrap}
footer .spacer{margin-left:auto}
.wrap{min-height:100vh;display:flex;flex-direction:column}
.hidden{display:none!important}
dialog{border:1px solid var(--line);border-radius:8px;padding:20px;max-width:520px}
dialog::backdrop{background:rgba(35,48,62,.35)}
@media (max-width:720px){header,main,.steps,footer{padding-left:16px;padding-right:16px}.grid2,.nums{grid-template-columns:1fr}ol.prog{grid-template-columns:1fr}.bar{width:24px}}
"""

_JS = r"""
const T = window.__TEXTS__, TOKEN = window.__TOKEN__;
const api = p => `/${TOKEN}/api/${p}`;
const fmt = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => (v && v[k] !== undefined) ? v[k] : `{${k}}`);
const el = (tag, attrs, ...kids) => { const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') n.className = v; else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else if (v !== null && v !== undefined && v !== false) n.setAttribute(k, v === true ? '' : v); }
  for (const kid of kids.flat()) { if (kid === null || kid === undefined) continue; n.append(kid.nodeType ? kid : document.createTextNode(String(kid))); }
  return n; };

const S = { step: 1, options: null, template: 'standard', switches: {}, structureTemplate: 'standard', structure: null,
  stands: null, userStands: false, scale: 'm', seed: 42, reference: '', dataLang: 'en', realism: 60, aiDrafts: false,
  outputDir: '', preview: null, previewError: null, job: null, poll: null, error: null, busyOpen: '' };

async function get(p) { const r = await fetch(api(p)); return r.json(); }
async function post(p, body) { const r = await fetch(api(p), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }); const j = await r.json(); j.__status = r.status; return j; }

function previewBody() { return { structure: S.structure, template: S.template, switches: S.switches, stands: S.stands, scale: S.scale }; }
function requestBody(confirm) { return { ...previewBody(), seed: S.seed, reference: S.reference, lang: S.dataLang, realism: S.realism, ai_drafts: S.aiDrafts, output_dir: S.outputDir, confirm: !!confirm }; }

let previewTimer = null;
function schedulePreview() { clearTimeout(previewTimer); previewTimer = setTimeout(refreshPreview, 180); }
async function refreshPreview() {
  const j = await post('preview', previewBody());
  if (j.ok) { S.preview = j; S.previewError = null; } else { S.previewError = j.error; }
  render();
}

function clone(o) { return JSON.parse(JSON.stringify(o)); }
function pickStructureTemplate(id) {
  const t = S.options.structure_templates.find(x => x.id === id);
  S.structureTemplate = id; if (t) S.structure = clone(t.structure); schedulePreview(); render();
}
function markCustom() { S.structureTemplate = 'custom'; schedulePreview(); render(); }
function artNames(sol, n) { const base = sol.name.replace(/^Solution\s+/, ''); return Array.from({ length: n }, (_, i) => `${base}-${i + 1}`); }
function effectiveStands() { if (S.stands) return S.stands; const t = S.options.templates.find(x => x.id === S.template); return t ? t.suggested_stands : S.options.stands.default; }

// ---------- rendering ----------
function render() {
  renderSteps(); const m = document.getElementById('main'); m.replaceChildren();
  if (S.step === 1) renderStep1(m); else if (S.step === 2) renderStep2(m); else renderStep3(m);
  renderFooter();
}
function renderSteps() {
  const box = document.getElementById('steps'); box.replaceChildren();
  const labels = [T.step1, T.step2, T.step3];
  labels.forEach((label, i) => {
    const n = i + 1, done = n < S.step;
    const b = el('button', { class: 'step' + (done ? ' done' : ''), type: 'button', 'aria-current': n === S.step ? 'step' : null, onclick: () => { if (n <= S.step || n === S.step + 1) { S.step = n; render(); } } },
      el('span', { class: 'dot', 'aria-hidden': 'true' }, done ? '✓' : String(n)), el('span', {}, label));
    box.append(b); if (i < 2) box.append(el('span', { class: 'bar' + (done ? ' done' : ''), 'aria-hidden': 'true' }));
  });
  box.append(el('span', { class: 'stepof' }, fmt(T.step_of, { n: S.step })));
}

function whenText(e, last) {
  if (e.stand_from <= 1 && (e.stand_to === null || e.stand_to >= last)) return T.when_all;
  if (e.stand_to === null || e.stand_to >= last) return e.stand_from < last ? fmt(T.when_from, { a: e.stand_from }) : T.when_last;
  return e.stand_from === e.stand_to ? fmt(T.when_one, { a: e.stand_from }) : fmt(T.when_range, { a: e.stand_from, b: e.stand_to });
}

function renderStep1(m) {
  const sec = el('section', { class: 'col', 'aria-labelledby': 'h1' });
  sec.append(el('h1', { id: 'h1' }, T.h1_step1), el('p', { class: 'lead' }, T.p_step1));
  const grid = el('div', { class: 'grid2', role: 'radiogroup', 'aria-label': T.step1 });
  for (const t of S.options.templates) {
    const sel = t.id === S.template;
    const lab = el('label', { class: 'tpl' + (sel ? ' sel' : '') },
      el('input', { type: 'radio', name: 'tpl', checked: sel, onchange: () => { S.template = t.id; S.switches = {}; if (!S.userStands) S.stands = null; schedulePreview(); render(); } }),
      el('span', {}, el('strong', {}, T['tpl_' + t.id] || t.title), t.id === 'standard' ? el('span', { class: 'pill' }, T.recommended) : null, el('br'), el('span', { class: 'sub' }, T['tpl_' + t.id + '_desc'] || '')));
    grid.append(lab);
  }
  sec.append(grid);
  const card = el('div', { class: 'card' });
  const last = S.preview ? S.preview.stands : effectiveStands();
  card.append(el('div', { class: 'row' }, el('h2', {}, T.events_title), el('span', { class: 'small' }, fmt(T.events_hint, { n: last }))));
  if (S.previewError) card.append(el('div', { class: 'alert', role: 'alert' }, S.previewError));
  if (S.preview) {
    const tbl = el('table', { class: 'ev' }, el('thead', {}, el('tr', {}, el('th', {}, T.col_when), el('th', {}, T.col_what), el('th', {}, T.col_effect), el('th', {}, T.col_on))));
    const tb = el('tbody');
    for (const e of S.preview.story.events) {
      const on = S.switches[e.id] !== undefined ? S.switches[e.id] : e.enabled;
      tb.append(el('tr', { class: on ? '' : 'off' }, el('td', {}, on ? whenText(e, last) : '—'), el('td', {}, el('div', {}, e.title)),
        el('td', { class: 'small' }, e.effect), el('td', {}, el('input', { type: 'checkbox', checked: on, 'aria-label': e.id + ' ' + T.col_on, onchange: ev => { S.switches[e.id] = ev.target.checked; schedulePreview(); } }))));
    }
    tbl.append(tb); card.append(tbl);
    if (S.preview.story.notices.length) card.append(el('div', { class: 'notice' }, el('strong', {}, T.notices_title + ': '), S.preview.story.notices.join(' ')));
  }
  sec.append(card); m.append(sec);

  const aside = el('aside', { class: 'col', 'aria-labelledby': 'h-struct' });
  const sc = el('div', { class: 'card' });
  const sel = el('select', { class: 'sm', 'aria-label': T.structure_template, onchange: ev => pickStructureTemplate(ev.target.value) });
  for (const id of ['standard', 'small', 'large']) sel.append(el('option', { value: id, selected: S.structureTemplate === id }, T['st_' + id]));
  sel.append(el('option', { value: 'custom', selected: S.structureTemplate === 'custom', disabled: S.structureTemplate !== 'custom' }, T.st_custom));
  sc.append(el('div', { class: 'row' }, el('h2', { id: 'h-struct' }, T.structure_title), el('span', { style: 'margin-left:auto' }, sel)), el('p', { class: 'small', style: 'margin:0' }, T.structure_hint));
  const tree = el('div', { style: 'display:flex;flex-direction:column;gap:8px;font-size:14px' });
  S.structure.portfolios.forEach((p, pi) => {
    tree.append(el('div', { class: 'pf' }, el('strong', {}, T.portfolio),
      el('input', { type: 'text', class: 'sm', value: p.name, 'aria-label': T.portfolio, style: 'flex:1 1 140px;min-width:0', onchange: ev => { p.name = ev.target.value; markCustom(); } }),
      el('button', { type: 'button', class: 'btn sm', 'aria-label': T.portfolio + ' ' + T.remove, disabled: S.structure.portfolios.length < 2, onclick: () => { S.structure.portfolios.splice(pi, 1); markCustom(); } }, '–')));
    const sols = el('div', { class: 'sol' });
    p.solutions.forEach((s, si) => {
      const row = el('div', { class: 'row' }, el('strong', {}, T.solution),
        el('input', { type: 'text', class: 'sm', value: s.name, 'aria-label': T.solution, style: 'flex:1 1 90px;min-width:0', onchange: ev => { s.name = ev.target.value; s.arts = artNames(s, s.arts.length); markCustom(); } }),
        el('span', { class: 'small' }, T.arts),
        el('button', { type: 'button', class: 'btn sm', 'aria-label': T.arts + ' ' + T.fewer, disabled: s.arts.length < 2, onclick: () => { s.arts = artNames(s, s.arts.length - 1); markCustom(); } }, '–'),
        el('span', { class: 'cnt', 'aria-live': 'polite' }, String(s.arts.length)),
        el('button', { type: 'button', class: 'btn sm', 'aria-label': T.arts + ' ' + T.more, onclick: () => { s.arts = artNames(s, s.arts.length + 1); markCustom(); } }, '+'),
        (() => { const w = el('select', { class: 'sm', 'aria-label': 'Workflow', onchange: ev => { s.workflow = ev.target.value; markCustom(); } });
          w.append(el('option', { value: 'classic', selected: s.workflow !== 'stage_map' }, T.wf_classic), el('option', { value: 'stage_map', selected: s.workflow === 'stage_map' }, T.wf_stage_map)); return w; })(),
        el('button', { type: 'button', class: 'btn sm', 'aria-label': T.solution + ' ' + T.remove, disabled: p.solutions.length < 2, onclick: () => { p.solutions.splice(si, 1); markCustom(); } }, '×'));
      sols.append(row, el('div', { class: 'small', style: 'padding-left:12px' }, s.arts.map(a => 'ART ' + a).join(' · ')));
    });
    sols.append(el('button', { type: 'button', class: 'btn ghost', style: 'align-self:flex-start', onclick: () => { const greek = ['Alpha','Beta','Gamma','Delta','Epsilon','Zeta','Eta','Theta','Iota','Kappa','Lambda','My','Ny','Xi','Omikron','Pi','Rho','Sigma','Tau','Ypsilon','Phi','Chi','Psi','Omega'];
      const used = new Set(S.structure.portfolios.flatMap(x => x.solutions.map(y => y.name))); const name = greek.find(g => !used.has(g)) || ('S' + (used.size + 1));
      const s = { name, workflow: 'classic', arts: [] }; s.arts = artNames(s, 2); p.solutions.push(s); markCustom(); } }, T.add_solution));
    tree.append(sols);
  });
  tree.append(el('button', { type: 'button', class: 'btn ghost', style: 'align-self:flex-start', onclick: () => { const n = S.structure.portfolios.length + 1; const s = { name: 'Alpha', workflow: 'classic', arts: [] }; s.arts = artNames(s, 2);
    S.structure.portfolios.push({ name: T.portfolio + ' ' + n, solutions: [s] }); markCustom(); } }, T.add_portfolio));
  sc.append(tree);
  const np = S.structure.portfolios.length, ns = S.structure.portfolios.reduce((a, p) => a + p.solutions.length, 0), na = S.structure.portfolios.reduce((a, p) => a + p.solutions.reduce((b, s) => b + s.arts.length, 0), 0);
  sc.append(el('div', { class: 'small' }, fmt(T.sum, { p: np + ' ' + T.portfolio + (np !== 1 ? 's' : ''), s: ns + ' ' + T.solution + (ns !== 1 ? 's' : ''), a: na + ' ' + T.arts })));
  aside.append(sc);
  const y = el('div', { class: 'card', style: 'font-size:14px' }, el('h2', {}, T.yields_title, ' ', el('span', { class: 'small', style: 'font-weight:400' }, T.yields_follow)));
  if (S.preview) { const e = S.preview.estimate;
    y.append(el('div', {}, fmt(T.yields_line1, { exports: e.jira_exports, workbooks: e.workbooks, registers: e.registers })), el('div', {}, T.yields_line2), el('div', {}, fmt(T.yields_line3, { stands: e.stands, deltas: e.deltas })), el('div', { class: 'small' }, T.yields_note));
    if (e.warn) y.append(el('div', { class: 'notice' }, fmt(T.warn_large, { reason: e.warn_reason }))); }
  aside.append(y); m.append(aside);
}

function renderStep2(m) {
  const sec = el('section', { class: 'col' });
  sec.append(el('h1', {}, T.h1_step2), el('p', { class: 'lead' }, T.p_step2));
  const card = el('div', { class: 'card', style: 'display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 28px' });
  const st = effectiveStands(), o = S.options.stands;
  const stBox = el('div', { style: 'display:flex;flex-direction:column;gap:6px' },
    el('label', { for: 'stands', style: 'font-weight:600' }, T.stands, ' ', el('span', { class: 'small', style: 'font-weight:400' }, T.stands_sub)),
    el('input', { id: 'stands', type: 'range', min: o.min, max: o.max, value: st, oninput: ev => { S.stands = parseInt(ev.target.value, 10); S.userStands = true; document.getElementById('stands-line').textContent = fmt(T.stands_line, { n: S.stands, weeks: (S.stands - 1) * 2 }); schedulePreview(); } }),
    el('div', { style: 'display:flex;justify-content:space-between;font-size:13px;color:var(--mute)' }, el('span', {}, String(o.min)), el('span', { id: 'stands-line', style: 'color:var(--ink);font-weight:600' }, fmt(T.stands_line, { n: st, weeks: (st - 1) * 2 })), el('span', {}, String(o.max))),
    el('div', { class: 'small' }, T.stands_hint));
  const scale = el('select', { id: 'scale', onchange: ev => { S.scale = ev.target.value; schedulePreview(); } });
  for (const s of S.options.scales) scale.append(el('option', { value: s, selected: s === S.scale }, T['scale_' + s]));
  const realism = el('div', { style: 'display:flex;flex-direction:column;gap:6px' },
    el('label', { for: 'realism', style: 'font-weight:600' }, T.realism, ' ', el('span', { class: 'small', style: 'font-weight:400' }, T.realism_sub)),
    el('input', { id: 'realism', type: 'range', min: 0, max: 100, value: S.realism, oninput: ev => { S.realism = parseInt(ev.target.value, 10); document.getElementById('realism-v').textContent = String(S.realism); } }),
    el('div', { style: 'display:flex;justify-content:space-between;font-size:13px;color:var(--mute)' }, el('span', {}, T.realism_low), el('span', { id: 'realism-v', style: 'color:var(--ink);font-weight:600' }, String(S.realism)), el('span', {}, T.realism_high)));
  const langSel = el('select', { id: 'lang', onchange: ev => { S.dataLang = ev.target.value; } });
  const names = Object.fromEntries((S.options.ui_languages || []).map(x => [x.id, x.name]));
  for (const l of S.options.languages) langSel.append(el('option', { value: l, selected: l === S.dataLang }, names[l] || l));
  card.append(stBox,
    el('div', { style: 'display:flex;flex-direction:column;gap:6px' }, el('label', { for: 'scale', style: 'font-weight:600' }, T.scale), scale),
    realism,
    el('div', { style: 'display:flex;flex-direction:column;gap:6px' }, el('label', { for: 'seed', style: 'font-weight:600' }, T.seed, ' ', el('span', { class: 'small', style: 'font-weight:400' }, T.seed_sub)), el('input', { id: 'seed', type: 'number', value: S.seed, onchange: ev => { S.seed = parseInt(ev.target.value, 10) || 0; } })),
    el('div', { style: 'display:flex;flex-direction:column;gap:6px' }, el('label', { for: 'ref', style: 'font-weight:600' }, T.reference), el('input', { id: 'ref', type: 'date', value: S.reference, onchange: ev => { S.reference = ev.target.value; } })),
    el('div', { style: 'display:flex;flex-direction:column;gap:6px' }, el('label', { for: 'lang', style: 'font-weight:600' }, T.lang), langSel));
  sec.append(card);
  sec.append(el('details', { class: 'card', style: 'padding:12px 18px' }, el('summary', { style: 'cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center' }, T.details), el('div', { class: 'small', style: 'padding-top:10px' }, T.details_text)));
  m.append(sec);
  const aside = el('aside', { class: 'col' });
  const q = el('div', { class: 'card' }, el('h2', {}, T.sources_title), el('p', { class: 'small', style: 'margin:0' }, T.sources_hint));
  const list = el('div', { style: 'display:flex;flex-direction:column;gap:6px;font-size:14px' });
  for (const k of ['jira', 'prometheus', 'github', 'gitlab', 'sonarqube', 'csv']) list.append(el('div', { class: 'row', style: 'min-height:36px' }, el('span', { class: 'mark done', 'aria-hidden': 'true' }, '✓'), el('span', {}, T['src_' + k]), el('span', { class: 'small', style: 'margin-left:auto' }, T.src_always)));
  list.append(el('label', { class: 'row', style: 'min-height:36px;align-items:flex-start' }, el('input', { type: 'checkbox', checked: S.aiDrafts, style: 'width:20px;height:20px;margin-top:3px', onchange: ev => { S.aiDrafts = ev.target.checked; } }), el('span', {}, T.src_ai, el('span', { class: 'small', style: 'display:block' }, T.src_ai_hint))));
  q.append(list); aside.append(q);
  if (S.preview) { const e = S.preview.estimate; aside.append(el('div', { class: 'card', style: 'font-size:14px' }, el('h2', {}, T.estimate_title), el('div', {}, fmt(T.estimate_line, { exports: e.jira_exports, registers: e.registers, stands: e.stands, deltas: e.deltas })))); }
  m.append(aside);
}

function renderStep3(m) {
  const sec = el('section', { class: 'col' });
  sec.append(el('h1', {}, T.h1_step3));
  const running = S.job && S.job.state === 'running';
  const card = el('div', { class: 'card' },
    el('label', { for: 'target', style: 'font-weight:600' }, T.target, ' ', el('span', { class: 'small', style: 'font-weight:400' }, T.target_sub)),
    el('div', { class: 'row' }, el('input', { id: 'target', type: 'text', value: S.outputDir, style: 'flex:1 1 360px;min-width:0', onchange: ev => { S.outputDir = ev.target.value; } }),
      el('button', { type: 'button', class: 'btn', onclick: browse }, T.browse)),
    el('div', { class: 'row', style: 'padding-top:4px' }, el('button', { type: 'button', class: 'btn primary big', disabled: running, onclick: () => generate(false) }, T.generate), el('span', { class: 'small' }, T.generate_hint)));
  if (S.error) card.append(el('div', { class: 'alert', role: 'alert' }, el('strong', {}, T.error_title + ': '), S.error));
  sec.append(card);
  if (S.job) sec.append(renderProgress());
  if (S.job && S.job.state === 'done' && S.job.result) sec.append(renderResult(S.job.result));
  m.append(sec);
  const aside = el('aside', { class: 'col' });
  if (S.job && S.job.result) aside.append(el('div', { class: 'card', style: 'font-size:14px' }, el('h2', {}, T.folder_title), el('pre', { class: 'list' }, S.job.result.listing.join('\n'))));
  aside.append(el('div', { class: 'card', style: 'font-size:14px' }, el('h2', {}, T.after_title), el('a', { href: '#', onclick: ev => { ev.preventDefault(); S.step = 1; S.job = null; render(); } }, T.after_new), el('code', { class: 'small', style: 'white-space:pre-wrap' }, T.after_cli)));
  m.append(aside);
}

function renderProgress() {
  const j = S.job, steps = S.options.steps, byStep = {};
  for (const e of j.events) byStep[e.step] = e;
  const done = steps.filter(s => byStep[s.id] && byStep[s.id].state !== 'running').length;
  const card = el('div', { class: 'card', 'aria-live': 'polite' });
  const head = el('div', { class: 'row' }, el('h2', {}, j.state === 'running' ? T.running : j.state === 'cancelled' ? T.cancel : j.state === 'failed' ? T.error_title : T.step3),
    el('span', { class: 'small' }, fmt(T.step_counter, { done, total: steps.length, s: j.elapsed_s })));
  if (j.state === 'running') head.append(el('button', { type: 'button', class: 'btn sm', style: 'margin-left:auto', onclick: cancel }, T.cancel));
  card.append(head, el('div', { class: 'pbar', role: 'progressbar', 'aria-valuenow': Math.round(done / steps.length * 100), 'aria-valuemin': 0, 'aria-valuemax': 100 }, el('div', { style: `width:${Math.round(done / steps.length * 100)}%` })));
  const ol = el('ol', { class: 'prog' });
  for (const s of steps) { const e = byStep[s.id]; const state = e ? e.state : 'pending';
    ol.append(el('li', { style: state === 'pending' ? 'color:var(--mute)' : '' }, el('span', { class: 'mark ' + (state === 'done' ? 'done' : state === 'running' ? 'run' : state === 'skipped' ? 'skip' : state === 'failed' ? 'fail' : ''), 'aria-hidden': 'true' }, state === 'done' ? '✓' : ''),
      el('span', {}, s.label, e && e.detail ? el('span', { class: 'small' }, ' — ' + (state === 'skipped' ? T.skipped + ': ' : '') + e.detail) : null), el('span', { class: 't' }, e && state === 'done' ? e.elapsed_s + ' s' : ''))); }
  card.append(ol);
  if (j.state === 'cancelled') card.append(el('div', { class: 'notice' }, T.cancelled));
  if (j.state === 'failed') card.append(el('div', { class: 'alert', role: 'alert' }, fmt(T.failed, { error: j.error || '' })));
  return card;
}

function renderResult(r) {
  const card = el('div', { class: 'card okbox' });
  card.append(el('div', { class: 'row' }, el('h2', { style: 'font-size:18px' }, fmt(T.done_title, { name: r.name })), el('span', { class: 'small' }, fmt(T.done_meta, { s: r.elapsed_s, seed: r.seed }))));
  card.append(el('div', { class: 'nums' }, el('div', { class: 'num' }, el('b', {}, String(r.issues)), fmt(T.n_issues, { arts: r.arts })), el('div', { class: 'num' }, el('b', {}, String(r.registers)), fmt(T.n_registers, { solutions: r.solutions })),
    el('div', { class: 'num' }, el('b', {}, String(r.stands)), T.n_stands), el('div', { class: 'num' }, el('b', {}, String(r.providers)), T.n_providers)));
  if (r.story) card.append(el('p', { style: 'margin:0;font-size:14px' }, el('strong', {}, T.story_three + ' '), r.story.summary.join(' ')));
  let roomSel = null;
  if (r.portfolios.length > 1) { roomSel = el('select', { class: 'sm', 'aria-label': T.portfolio }); r.portfolios.forEach((p, i) => roomSel.append(el('option', { value: i }, fmt(T.portfolio_tab, { name: p.name })))); card.append(el('div', { class: 'row' }, roomSel)); }
  const room = () => roomSel ? parseInt(roomSel.value, 10) : 0;
  const acts = el('div', { class: 'row' },
    el('button', { type: 'button', class: 'btn primary', onclick: () => openTarget({ what: 'report', room: room() }) }, T.open_report),
    el('button', { type: 'button', class: 'btn', onclick: () => openTarget({ what: 'conference', room: room() }) }, T.open_conference),
    el('button', { type: 'button', class: 'btn', onclick: () => openTarget({ what: 'delta_last', room: room() }) }, T.open_delta_last),
    el('button', { type: 'button', class: 'btn', onclick: () => openTarget({ what: 'readme', room: room() }) }, T.open_readme),
    el('button', { type: 'button', class: 'btn', onclick: () => openTarget({ what: 'folder', room: room() }) }, T.open_folder));
  if (r.has_drafts) acts.append(el('button', { type: 'button', class: 'btn', onclick: () => openTarget({ what: 'drafts', room: room() }) }, T.open_drafts));
  card.append(acts);
  const n = r.stand_dates.length;
  if (n >= 2) { const a = el('select', { class: 'sm', 'aria-label': T.stand }), b = el('select', { class: 'sm', 'aria-label': T.stand });
    r.stand_dates.forEach((d, i) => { if (i < n - 1) a.append(el('option', { value: i + 1, selected: i === n - 2 }, `${i + 1} · ${d}`)); if (i > 0) b.append(el('option', { value: i + 1, selected: i === n - 1 }, `${i + 1} · ${d}`)); });
    card.append(el('div', { class: 'row', style: 'padding:10px 12px;background:var(--bg);border-radius:6px;font-size:14px' }, el('strong', {}, T.compare), el('span', { class: 'small' }, T.stand), a, el('span', { 'aria-hidden': 'true' }, '→'), b,
      el('button', { type: 'button', class: 'btn sm', style: 'border-color:var(--pri);color:var(--pri-dark);font-weight:600', onclick: () => { const x = parseInt(a.value, 10), y = parseInt(b.value, 10); if (x >= y) { S.error = `${x} → ${y}`; render(); return; } openTarget({ what: 'delta', a: x, b: y, room: room() }); } }, T.open_delta), el('span', { class: 'small' }, T.compare_hint))); }
  if (S.busyOpen) card.append(el('div', { class: 'small', 'aria-live': 'polite' }, S.busyOpen));
  return card;
}

function renderFooter() {
  const f = document.getElementById('footer'); f.replaceChildren();
  const tplTitle = T['tpl_' + S.template] || S.template;
  if (S.step === 1) { const on = S.preview ? S.preview.story.events.filter(e => (S.switches[e.id] !== undefined ? S.switches[e.id] : e.enabled)).length : 0;
    f.append(el('span', { class: 'small' }, fmt(T.footer_step1, { tpl: tplTitle, on })), el('button', { type: 'button', class: 'btn primary spacer', onclick: () => { S.step = 2; render(); } }, T.next_step2)); }
  else if (S.step === 2) { f.append(el('button', { type: 'button', class: 'btn', onclick: () => { S.step = 1; render(); } }, T.back), el('span', { class: 'small' }, fmt(T.footer_step2, { tpl: tplTitle, scale: S.scale.toUpperCase(), stands: effectiveStands(), realism: S.realism, seed: S.seed })),
    el('button', { type: 'button', class: 'btn primary spacer', onclick: () => { S.step = 3; render(); } }, T.next_step3)); }
  else { f.append(el('button', { type: 'button', class: 'btn', onclick: () => { S.step = 2; render(); } }, T.back), el('span', { class: 'small' }, fmt(T.footer_step2, { tpl: tplTitle, scale: S.scale.toUpperCase(), stands: effectiveStands(), realism: S.realism, seed: S.seed }))); }
}

// ---------- actions ----------
async function browse() { const j = await post('browse', { initial: S.outputDir }); if (j.path) { S.outputDir = j.path; render(); } else if (!j.ok) { S.error = T.browse_unavailable; render(); } }
async function generate(confirm) {
  S.error = null; const j = await post('generate', requestBody(confirm));
  if (j.needs_confirm) { showConfirm(j); return; }
  if (!j.ok) { S.error = j.error || (j.busy ? T.running : '?'); render(); return; }
  S.job = { state: 'running', events: [], elapsed_s: 0, result: null, error: null }; render(); pollProgress();
}
function showConfirm(j) {
  const d = document.getElementById('confirm'); d.replaceChildren(el('h2', {}, T.confirm_title), el('p', {}, fmt(T.confirm_text, { path: j.path, n: j.entries })),
    el('div', { class: 'row' }, el('button', { type: 'button', class: 'btn primary', onclick: () => { d.close(); generate(true); } }, T.confirm_yes), el('button', { type: 'button', class: 'btn', onclick: () => { d.close(); document.getElementById('target') && document.getElementById('target').focus(); } }, T.confirm_no)));
  d.showModal();
}
async function pollProgress() { clearTimeout(S.poll); const j = await get('progress'); S.job = j; render(); if (j.state === 'running') S.poll = setTimeout(pollProgress, 600); }
async function cancel() { await post('cancel'); }
async function openTarget(body) { S.busyOpen = '…'; render(); const j = await post('open', body); S.busyOpen = j.ok ? `${T.opened}: ${j.path}` : ''; if (!j.ok) S.error = j.error; render(); }

// ---------- init ----------
(async function init() {
  S.options = await get('options');
  S.dataLang = S.options.data_lang; S.seed = S.options.defaults.seed; S.reference = S.options.defaults.reference; S.realism = S.options.defaults.realism; S.scale = S.options.defaults.scale; S.outputDir = S.options.defaults.output_dir;
  S.structure = clone(S.options.structure_templates.find(x => x.id === 'standard').structure);
  document.getElementById('version').textContent = 'v' + S.options.version + ' · ' + T.beta;
  render(); refreshPreview();
})();
"""


def render_page(lang: str, token: str, version: str = "") -> str:
    """The complete page for ``lang`` with the access key baked into its API calls."""
    t = texts_for(lang)
    texts_json = json.dumps(t, ensure_ascii=False).replace("</", "<\\/")
    manual = MANUALS.get(lang, MANUALS["en"])
    options = "".join(
        f'<option value="{code}"{" selected" if code == lang else ""}>{name}</option>'
        for code, name in LANGUAGE_NAMES.items())
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t['app']} · {t['nav_room']}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">{t['app']}</div>
    <div class="beta" id="version">v{version} · {t['beta']}</div>
    <nav aria-label="Bereiche">
      <a href="#" aria-current="page">{t['nav_room']}</a>
      <a href="https://jaegerfeld.github.io/situation-report/{manual}" rel="noreferrer">{t['nav_manual']}</a>
    </nav>
    <label class="uilang"><span class="sr">{t['ui_lang']}</span>
      <select id="ui-lang" aria-label="{t['ui_lang']}" title="{t['ui_lang']}"
              onchange="location.href = '/' + window.__TOKEN__ + '/?lang=' + this.value">{options}</select>
    </label>
  </header>
  <div class="steps" id="steps" aria-label="Schritte"></div>
  <main id="main"></main>
  <footer id="footer"></footer>
  <dialog id="confirm" aria-labelledby="confirm-h"></dialog>
</div>
<script>window.__TEXTS__ = {texts_json}; window.__TOKEN__ = {json.dumps(token)};</script>
<script>{_JS}</script>
</body>
</html>
"""
