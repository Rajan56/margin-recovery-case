/* Margin Recovery Case: page logic. Plain JavaScript, no libraries.
   Every number comes from DATA (data/case_results.json), produced by python/02_analysis.py. */
(function () {
"use strict";

// ------------------------------------------------------------------ helpers
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const NS = "http://www.w3.org/2000/svg";
const MINUS = "−";
function sv(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function txt(parent, x, y, s, attrs = {}) {
  const t = sv("text", Object.assign({ x, y }, attrs), parent);
  t.textContent = s;
  return t;
}
const sign = (x, d = 1) => (x > 0 ? "+" : x < 0 ? MINUS : "") + Math.abs(x).toFixed(d);
const eur = (x, d = 1) => (x < 0 ? MINUS : "") + "€" + Math.abs(x).toFixed(d) + "m";
const eurS = (x, d = 1) => (x > 0 ? "+" : x < 0 ? MINUS : "") + "€" + Math.abs(x).toFixed(d) + "m";
const pct = (x, d = 1) => (x < 0 ? MINUS : "") + Math.abs(x).toFixed(d) + "%";
const int = (x) => Math.round(x).toLocaleString("en-US");
const niceDate = (iso) => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

function svgFor(el, h) {
  el.innerHTML = "";
  const w = Math.max(280, el.clientWidth || 600);
  const s = sv("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img" }, el);
  return { s, w, h };
}
function ticks(min, max, n = 5) {
  const span = max - min, step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => span / s <= n) || mag * 10;
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

// tooltip
const tip = $("#tip");
function showTip(html, ev) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  const pad = 14, r = tip.getBoundingClientRect();
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - pad;
  if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - pad;
  tip.style.left = Math.max(8, x) + "px";
  tip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => (tip.style.opacity = 0);
function hover(node, html) {
  node.classList.add("hit");
  node.addEventListener("mousemove", ev => showTip(typeof html === "function" ? html() : html, ev));
  node.addEventListener("mouseleave", hideTip);
  node.addEventListener("touchstart", ev => { showTip(typeof html === "function" ? html() : html, ev.touches[0]); }, { passive: true });
}
document.addEventListener("touchstart", ev => { if (!ev.target.closest(".hit")) hideTip(); }, { passive: true });

// ------------------------------------------------------------ derived facts
const P24 = DATA.pnl["2024"], P25 = DATA.pnl["2025"];
const BR = Object.fromEntries(DATA.bridge.map(b => [b.label, b.value]));
const PC = Object.fromEntries(DATA.price_by_contract.map(c => [c.contract, c]));
const CF = DATA.cts_findings, EN = DATA.energy;
const initTotal = DATA.initiatives.reduce((a, i) => a + i.value, 0);
const market = BR["Fibre cost"] + BR["Energy cost"] + BR["FX (SEK)"];
const D = {
  sales25: eur(P25.net_sales),
  salesGrowthTxt: sign((P25.net_sales / P24.net_sales - 1) * 100) + "% vs FY2024",
  ebitda25: eur(P25.ebitda),
  ebitdaChgTxt: eurS(P25.ebitda - P24.ebitda) + " vs FY2024",
  ebitdaChgAbs: eur(Math.abs(P25.ebitda - P24.ebitda)),
  margin25: pct(P25.ebitda_margin * 100),
  marginChgTxt: sign((P25.ebitda_margin - P24.ebitda_margin) * 100) + " pp, from " + pct(P24.ebitda_margin * 100),
  initTotal: eur(initTotal),
  initPpTxt: "about " + sign(initTotal / P25.net_sales * 100) + " pp margin, full year",
  marketEffect: eur(Math.abs(market)),
  volEffect: eur(BR["Volume"]),
  fixedEffect: eur(Math.abs(PC["Fixed annual"].effect)),
  negCount: String(CF.negative_ebitda_count),
  negSmall: String(CF.negative_by_tier.Small || 0),
  negValueAbs: eur(Math.abs(CF.negative_ebitda_value)),
  smallOrderNeg: CF.small_order_negative,
  whalePeak: pct(CF.peak_whale_pct),
  reconGap: "€" + DATA.bridge_reconciliation_gap_eur.toFixed(2),
  excessMwh: int(EN.excess_mwh_2025) + " MWh",
  excessCost: eur(EN.excess_cost_2025, 2),
  excessAnnual: eur(EN.excess_cost_annual, 2) + "/yr",
  excessCo2: int(EN.excess_co2_t) + " t",
  alertWeek: niceDate(EN.alert_week_p3),
  aprYoy: "+" + EN.monthly_yoy_p3["04"].toFixed(1) + "%",
};
$$("[data-k]").forEach(e => { if (D[e.dataset.k] != null) e.textContent = D[e.dataset.k]; });

// ------------------------------------------------------------ 1. KPI tree
(function kpiTree() {
  const pt = (p, k) => p[k] * 1e6 / p.volume_t;
  const nodes = [
    ["Volume", P24.volume_t / 1000, P25.volume_t / 1000, "kt", true, 0],
    ["Price", pt(P24, "net_sales"), pt(P25, "net_sales"), "€/t", true, 0],
    ["Fibre", pt(P24, "fibre"), pt(P25, "fibre"), "€/t", false, 0],
    ["Energy", pt(P24, "energy"), pt(P25, "energy"), "€/t", false, 1],
    ["Other variable", pt(P24, "other_variable"), pt(P25, "other_variable"), "€/t", false, 1],
    ["Cost-to-serve", (P24.freight + P24.order_handling) * 1e6 / P24.volume_t, (P25.freight + P25.order_handling) * 1e6 / P25.volume_t, "€/t", false, 1],
    ["Fixed", pt(P24, "fixed"), pt(P25, "fixed"), "€/t", false, 0],
    ["FX", DATA.meta.fx_2024_avg, DATA.meta.fx_2025_avg, "SEK/€", false, 2],
  ];
  const tree = $("#kpiTree");
  tree.innerHTML = `<div class="node root"><div class="t">EBITDA margin</div><div class="v">${pct(P24.ebitda_margin * 100)} → ${pct(P25.ebitda_margin * 100)} · EBITDA per tonne €${(P24.ebitda * 1e6 / P24.volume_t).toFixed(0)} → €${(P25.ebitda * 1e6 / P25.volume_t).toFixed(0)}</div></div>`;
  const br = document.createElement("div");
  br.className = "branches";
  nodes.forEach(([name, a, b, u, upGood, d]) => {
    const ch = (b / a - 1) * 100, good = upGood ? ch > 0 : ch < 0;
    const note = name === "FX" ? "SEK weaker" : (good ? "helps" : "hurts");
    br.insertAdjacentHTML("beforeend",
      `<div class="node"><div class="t">${name}</div><div class="v">${a.toFixed(d)} → ${b.toFixed(d)} ${u}</div><div class="chg ${good ? "up" : "down"}">${sign(ch)}% · ${note}</div></div>`);
  });
  tree.appendChild(br);
})();

// code tabs
$$("#codeTabs button").forEach(b => b.addEventListener("click", () => {
  $$("#codeTabs button").forEach(x => x.setAttribute("aria-selected", x === b));
  ["sql", "py", "dax"].forEach(k => ($("#code-" + k).hidden = k !== b.dataset.tab));
}));

// ------------------------------------------------------- 3. waterfall bridge
function drawWaterfall() {
  const el = $("#waterfall");
  const rows = [{ label: "EBITDA FY2024", value: P24.ebitda, total: true }]
    .concat(DATA.bridge.map(b => ({ label: b.label, value: b.value })))
    .concat([{ label: "EBITDA FY2025", value: P25.ebitda, total: true }]);
  const rowH = 30, top = 8, bottom = 26;
  const { s, w, h } = svgFor(el, top + rows.length * rowH + bottom);
  const L = Math.min(130, w * 0.34), R = 52;
  const max = Math.ceil(Math.max(P24.ebitda, P25.ebitda + 20) / 10) * 10;
  const x = v => L + (v / max) * (w - L - R);
  ticks(0, max, 4).forEach(t => {
    sv("line", { x1: x(t), x2: x(t), y1: top, y2: h - bottom, stroke: "var(--grid)" }, s);
    txt(s, x(t), h - 8, t, { "text-anchor": "middle" });
  });
  let run = 0;
  rows.forEach((r, i) => {
    const y = top + i * rowH + 6, bh = rowH - 12;
    let a, b, color;
    if (r.total) { a = 0; b = r.value; run = r.value; color = "var(--total)"; }
    else { a = run; b = run + r.value; run = b; color = r.value >= 0 ? "var(--pos)" : "var(--neg)"; }
    const x0 = x(Math.min(a, b)), x1 = x(Math.max(a, b));
    const g = sv("g", {}, s);
    sv("rect", { x: L - 4, y: y - 5, width: w - L - R + 4 + R, height: rowH, fill: "transparent" }, g);
    sv("rect", { x: x0, y, width: Math.max(2, x1 - x0), height: bh, rx: 3, fill: color }, g);
    if (i < rows.length - 1) {
      const nx = x(run);
      sv("line", { x1: nx, x2: nx, y1: y + bh, y2: y + rowH, stroke: "var(--axis)", "stroke-width": 1 }, s);
    }
    txt(g, L - 10, y + bh / 2 + 4, r.label, { "text-anchor": "end", class: "lbl", "font-weight": r.total ? 650 : 400 });
    txt(g, x1 + 6, y + bh / 2 + 4, r.total ? eur(r.value) : eurS(r.value), { class: "val" });
    const share = r.total ? "" : `<br>${Math.abs(r.value / (P25.ebitda - P24.ebitda) * 100).toFixed(0)}% of the net change`;
    const notes = {
      "Volume": "Tonnes up, valued at FY2024 average unit contribution.",
      "Mix": "Growth came from lower-margin customers and segments.",
      "Price": "Price per tonne in constant currency. Split by contract type on the right.",
      "Fibre cost": "Containerboard cost per tonne rose with tight wood supply.",
      "Energy cost": "Energy prices up, plus the drift at Sweden Central (step 5).",
      "Cost-to-serve": "Freight and order-handling rates per tonne.",
      "Other variable": "Inks, starch, glue.",
      "Fixed costs": "Wage inflation and maintenance, constant currency.",
      "FX (SEK)": "Weaker SEK translates Swedish sales into fewer euros; SEK costs partly offset.",
    };
    hover(g, `<b>${r.label}</b><br>${r.total ? eur(r.value, 2) : eurS(r.value, 2)}${share}${notes[r.label] ? "<br>" + notes[r.label] : ""}`);
  });
}

function drawPriceSplit() {
  const el = $("#priceSplit");
  const rows = DATA.price_by_contract.slice().sort((a, b) => a.effect - b.effect);
  const rowH = 44;
  const { s, w, h } = svgFor(el, rows.length * rowH + 6);
  const L = Math.min(118, w * 0.34), R = 8, pad = 58;
  const lim = Math.max(...rows.map(r => Math.abs(r.effect)));
  const x = v => L + pad + (v + lim) / (2 * lim) * (w - L - R - 2 * pad);
  sv("line", { x1: x(0), x2: x(0), y1: 0, y2: h, stroke: "var(--axis)" }, s);
  rows.forEach((r, i) => {
    const y = i * rowH + 12, bh = 18;
    const g = sv("g", {}, s);
    sv("rect", { x: 0, y: y - 8, width: w, height: rowH - 4, fill: "transparent" }, g);
    const a = x(Math.min(0, r.effect)), b = x(Math.max(0, r.effect));
    sv("rect", { x: a, y, width: Math.max(2, b - a), height: bh, rx: 3, fill: r.effect < 0 ? "var(--neg)" : "var(--pos)" }, g);
    txt(g, L - 10, y + 8, r.contract, { "text-anchor": "end", class: "lbl" });
    txt(g, L - 10, y + 23, `${sign(r.price_change_pct)}% per t`, { "text-anchor": "end", "font-size": 11.5 });
    const vx = r.effect < 0 ? a - 6 : b + 6;
    txt(g, vx, y + 13, eurS(r.effect), { class: "val", "text-anchor": r.effect < 0 ? "end" : "start" });
    hover(g, `<b>${r.contract}</b><br>Price ${sign(r.price_change_pct, 2)}% per tonne<br>EBITDA effect ${eurS(r.effect, 2)}<br>${r.volume_share}% of FY2025 volume`);
  });
}

// ------------------------------------------------------ 4. customers
const TIER = { Key: "var(--s1)", Mid: "var(--s2)", Small: "var(--s3)" };
$("#tierLegend").innerHTML = Object.entries(TIER).map(([t, c]) => `<span><i style="background:${c};border-radius:50%"></i>${t} accounts</span>`).join("");

function drawWhale() {
  const el = $("#whale");
  const { s, w, h } = svgFor(el, 250);
  const L = 44, R = 16, T = 14, B = 30;
  const cs = DATA.customers, wc = DATA.whale_curve, n = wc.length;
  const ymax = 120;
  const x = i => L + (i / (n - 1)) * (w - L - R);
  const y = v => T + (1 - v / ymax) * (h - T - B);
  [0, 25, 50, 75, 100].forEach(t => {
    sv("line", { x1: L, x2: w - R, y1: y(t), y2: y(t), stroke: t === 100 ? "var(--axis)" : "var(--grid)" }, s);
    txt(s, L - 8, y(t) + 4, t + "%", { "text-anchor": "end" });
  });
  [1, 20, 40, 60, 80].forEach(t => txt(s, x(t - 1), h - 10, t, { "text-anchor": "middle" }));
  const pk = wc.indexOf(Math.max(...wc));
  sv("path", { d: `M${x(pk)},${y(wc[pk])} ` + wc.slice(pk).map((v, i) => `L${x(pk + i)},${y(v)}`).join(" ") + ` L${x(n - 1)},${y(0)} L${x(pk)},${y(0)} Z`, fill: "var(--wash)" }, s);
  sv("path", { d: wc.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" "), fill: "none", stroke: "var(--accent)", "stroke-width": 2, "stroke-linejoin": "round" }, s);
  sv("circle", { cx: x(pk), cy: y(wc[pk]), r: 4.5, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2 }, s);
  txt(s, x(pk) - 6, y(wc[pk]) - 9, `Peak ${wc[pk]}%`, { "text-anchor": "end", class: "val" });
  txt(s, x(n - 1) - 4, y(wc[n - 1]) - 10, `${wc[n - 1].toFixed(0)}%`, { "text-anchor": "end", class: "val" });
  // crosshair
  const cross = sv("line", { y1: T, y2: h - B, stroke: "var(--axis)", opacity: 0 }, s);
  const dot = sv("circle", { r: 4, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2, opacity: 0 }, s);
  const hitr = sv("rect", { x: L, y: T, width: w - L - R, height: h - T - B, fill: "transparent" }, s);
  const move = ev => {
    const pt = ev.touches ? ev.touches[0] : ev;
    const bb = s.getBoundingClientRect();
    const px = (pt.clientX - bb.left) * (w / bb.width);
    const i = Math.max(0, Math.min(n - 1, Math.round((px - L) / (w - L - R) * (n - 1))));
    const c = cs[i];
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("opacity", 1);
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(wc[i])); dot.setAttribute("opacity", 1);
    showTip(`<b>#${i + 1} ${c.id}</b> · ${c.tier}<br>EBITDA ${eurS(c.ebitda, 2)} (${pct(c.margin)})<br>Cumulative ${wc[i]}% of total`, pt);
  };
  hitr.classList.add("hit");
  hitr.addEventListener("mousemove", move);
  hitr.addEventListener("touchmove", move, { passive: true });
  hitr.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); });
}

function drawScatter() {
  const el = $("#scatter");
  const { s, w, h } = svgFor(el, 250);
  const L = 44, R = 12, T = 12, B = 34;
  const cs = DATA.customers;
  const lx = v => Math.log10(v), x0 = lx(2), x1 = lx(80);
  const x = v => L + (lx(v) - x0) / (x1 - x0) * (w - L - R);
  const ymin = -30, ymax = 30;
  const y = v => T + (1 - (v - ymin) / (ymax - ymin)) * (h - T - B);
  [-30, -15, 0, 15, 30].forEach(t => {
    sv("line", { x1: L, x2: w - R, y1: y(t), y2: y(t), stroke: t === 0 ? "var(--axis)" : "var(--grid)" }, s);
    txt(s, L - 8, y(t) + 4, t + "%", { "text-anchor": "end" });
  });
  [2, 5, 10, 20, 50].forEach(t => txt(s, x(t), h - 16, t, { "text-anchor": "middle" }));
  txt(s, (L + w - R) / 2, h - 2, "average order, tonnes (log scale)", { "text-anchor": "middle", "font-size": 11 });
  sv("line", { x1: x(6), x2: x(6), y1: T, y2: h - B, stroke: "var(--axis)", "stroke-dasharray": "0" , opacity: 0.8 }, s);
  txt(s, x(6) + 4, T + 10, "6 t", { "font-size": 11 });
  ["Key", "Mid", "Small"].forEach(t => cs.filter(c => c.tier === t).forEach(c => {
    const g = sv("g", {}, s);
    sv("circle", { cx: x(c.avg_order_t), cy: y(Math.max(ymin, Math.min(ymax, c.margin))), r: 12, fill: "transparent" }, g);
    sv("circle", { cx: x(c.avg_order_t), cy: y(Math.max(ymin, Math.min(ymax, c.margin))), r: 4.5, fill: TIER[t], stroke: "var(--surface)", "stroke-width": 1.5 }, g);
    hover(g, `<b>${c.id}</b> · ${c.tier} · ${c.contract}<br>${c.segment}, ${c.plant}<br>Avg order ${c.avg_order_t} t · cost-to-serve €${c.cts_per_t}/t<br>EBITDA ${eurS(c.ebitda, 2)} (${pct(c.margin)})`);
  }));
}

(function tierTable() {
  const rows = DATA.tier_summary.slice().sort((a, b) => ["Key", "Mid", "Small"].indexOf(a.tier) - ["Key", "Mid", "Small"].indexOf(b.tier));
  $("#tierTable").innerHTML = `<tr><th>Tier</th><th class="n">Customers</th><th class="n">Volume share</th><th class="n">Cost-to-serve per t</th><th class="n">EBITDA</th><th class="n">EBITDA margin</th><th class="n">Loss-making</th></tr>` +
    rows.map(r => `<tr><td><span class="dot" style="background:${TIER[r.tier]}"></span>${r.tier}</td><td class="n">${r.customers}</td><td class="n">${r.volume_share}%</td><td class="n">€${r.cts_per_t.toFixed(0)}</td><td class="n">${eur(r.ebitda)}</td><td class="n">${pct(r.margin)}</td><td class="n">${CF.negative_by_tier[r.tier] || 0} of ${r.customers}</td></tr>`).join("");
})();

// ------------------------------------------------------------ 5. energy
let plantSel = "P3";
$("#plantSeg").innerHTML = DATA.plants.map(p => `<button data-p="${p.id}" class="${p.id === plantSel ? "on" : ""}">${p.name}</button>`).join("");
$$("#plantSeg button").forEach(b => b.addEventListener("click", () => {
  plantSel = b.dataset.p;
  $$("#plantSeg button").forEach(x => x.classList.toggle("on", x === b));
  drawEnergy();
}));

function drawEnergy() {
  const el = $("#energy");
  const ser = EN.series[plantSel];
  const { s, w, h } = svgFor(el, 270);
  const L = 44, R = 12, T = 16, B = 30;
  const n = ser.weeks.length;
  const all = ser.intensity.concat(ser.baseline);
  const ymin = Math.floor(Math.min(...all) * 20) / 20 - 0.02, ymax = Math.ceil(Math.max(...all) * 20) / 20 + 0.02;
  const x = i => L + i / (n - 1) * (w - L - R);
  const y = v => T + (1 - (v - ymin) / (ymax - ymin)) * (h - T - B);
  ticks(ymin, ymax, 4).forEach(t => {
    sv("line", { x1: L, x2: w - R, y1: y(t), y2: y(t), stroke: "var(--grid)" }, s);
    txt(s, L - 8, y(t) + 4, t.toFixed(2), { "text-anchor": "end" });
  });
  const yearStart = ser.weeks.findIndex(d => d.startsWith("2025"));
  sv("line", { x1: x(yearStart), x2: x(yearStart), y1: T, y2: h - B, stroke: "var(--axis)" }, s);
  txt(s, x(yearStart / 2), h - 10, "2024", { "text-anchor": "middle" });
  txt(s, x((yearStart + n) / 2), h - 10, "2025", { "text-anchor": "middle" });
  // excess shading after the drift starts (only where it exists)
  const startIdx = ser.weeks.findIndex(d => d >= EN.anomaly_start);
  if (plantSel === "P3") {
    const top = [], bot = [];
    for (let i = startIdx; i < n; i++) { top.push(`${x(i)},${y(Math.max(ser.intensity[i], ser.baseline[i]))}`); bot.unshift(`${x(i)},${y(ser.baseline[i])}`); }
    sv("polygon", { points: top.concat(bot).join(" "), fill: "var(--wash)" }, s);
  }
  const path = arr => arr.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
  sv("path", { d: path(ser.baseline), fill: "none", stroke: "var(--muted)", "stroke-width": 1.5 }, s);
  sv("path", { d: path(ser.intensity), fill: "none", stroke: "var(--accent)", "stroke-width": 2, "stroke-linejoin": "round" }, s);
  const alertIso = plantSel === "P3" ? EN.alert_week_p3 : (EN.alerts_other_plants[plantSel] || null);
  if (alertIso) {
    const ai = ser.weeks.indexOf(alertIso);
    sv("line", { x1: x(ai), x2: x(ai), y1: T, y2: h - B, stroke: "var(--neg)", "stroke-width": 1.5 }, s);
    sv("circle", { cx: x(ai), cy: y(ser.intensity[ai]), r: 5, fill: "var(--neg)", stroke: "var(--surface)", "stroke-width": 2 }, s);
    const lx = x(ai) > w - 130 ? x(ai) - 6 : x(ai) + 6;
    txt(s, lx, T + 10, "Weekly alert", { class: "val", "text-anchor": x(ai) > w - 130 ? "end" : "start" });
    if (plantSel === "P3") {
      sv("line", { x1: x(startIdx), x2: x(startIdx), y1: T, y2: h - B, stroke: "var(--axis)", "stroke-width": 1 }, s);
      txt(s, x(startIdx) - 4, h - B - 6, "Drift starts", { "text-anchor": "end", "font-size": 11 });
    }
  } else {
    txt(s, w - R, T + 10, "No alert: within normal range", { "text-anchor": "end", class: "lbl" });
  }
  const cross = sv("line", { y1: T, y2: h - B, stroke: "var(--axis)", opacity: 0 }, s);
  const dot = sv("circle", { r: 4, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2, opacity: 0 }, s);
  const hit = sv("rect", { x: L, y: T, width: w - L - R, height: h - T - B, fill: "transparent" }, s);
  hit.classList.add("hit");
  const move = ev => {
    const pt = ev.touches ? ev.touches[0] : ev;
    const bb = s.getBoundingClientRect();
    const i = Math.max(0, Math.min(n - 1, Math.round(((pt.clientX - bb.left) * (w / bb.width) - L) / (w - L - R) * (n - 1))));
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("opacity", 1);
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(ser.intensity[i])); dot.setAttribute("opacity", 1);
    const dev = (ser.intensity[i] / ser.baseline[i] - 1) * 100;
    showTip(`<b>Week of ${niceDate(ser.weeks[i])}</b><br>Actual ${ser.intensity[i].toFixed(3)} MWh/t<br>Baseline ${ser.baseline[i].toFixed(3)} MWh/t<br>Deviation ${sign(dev)}%`, pt);
  };
  hit.addEventListener("mousemove", move);
  hit.addEventListener("touchmove", move, { passive: true });
  hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); });
}

// ---------------------------------------------------------- 6. simulator
const B = DATA.scenario_base;
const INIT = DATA.initiatives;
const IN_YEAR = { I1: 0.5, I2: 0.6, I3: 0.9, I4: 0.4, I5: 0.25, I6: 0 };
const LEVERS = [
  { k: "price", label: "Price vs FY2025", min: -5, max: 5, step: 0.5, base: 0, f: v => sign(v) + "%" },
  { k: "volume", label: "Volume vs FY2025", min: -6, max: 6, step: 0.5, base: 1.5, f: v => sign(v) + "%" },
  { k: "board", label: "Containerboard cost", min: 450, max: 650, step: 5, base: Math.round(B.board_price), f: v => "€" + v + "/t" },
  { k: "energy", label: "Energy price vs FY2025", min: -20, max: 40, step: 5, base: 0, f: v => sign(v, 0) + "%" },
  { k: "cts", label: "Freight and handling rates", min: -5, max: 10, step: 1, base: 2, f: v => sign(v, 0) + "%" },
  { k: "fx", label: "SEK per EUR", min: 10.8, max: 12.8, step: 0.05, base: +B.fx_2025.toFixed(2), f: v => v.toFixed(2) },
  { k: "fixed", label: "Fixed cost inflation", min: 0, max: 6, step: 0.5, base: 3, f: v => sign(v) + "%" },
];
const state = {};
LEVERS.forEach(l => (state[l.k] = l.base));
const on = new Set();
const PRESETS = {
  base: { levers: {}, init: [] },
  down: { levers: { price: -1, volume: -2, board: Math.round(B.board_price) + 15, energy: 10, fx: 12.1 }, init: [] },
  plan: { levers: {}, init: ["I1", "I2", "I3", "I4", "I5"] },
};

function model(st, inits) {
  const v = 1 + st.volume / 100, p = 1 + st.price / 100, fx = st.fx;
  const sales = (B.sales_eur + B.sales_sek_local / fx) * p * v;
  const fibre = B.board_t * v * st.board;
  const energy = (B.energy_eur + B.energy_sek_local / fx) * (1 + st.energy / 100) * v;
  const cts = (B.cts_eur + B.cts_sek_local / fx) * (1 + st.cts / 100) * v;
  const other = B.other_var_eur * v;
  const fixed = (B.fixed_eur + B.fixed_sek_local / fx) * (1 + st.fixed / 100);
  const up = INIT.filter(i => inits.has(i.id)).reduce((a, i) => a + i.value * 1e6 * IN_YEAR[i.id], 0);
  const e = sales - fibre - energy - cts - other - fixed + up;
  return { sales: sales / 1e6, ebitda: e / 1e6, margin: e / sales * 100, up: up / 1e6 };
}

$("#levers").innerHTML = LEVERS.map(l => `<div class="ctrl"><label for="lv-${l.k}">${l.label}</label><output id="out-${l.k}"></output><input type="range" id="lv-${l.k}" min="${l.min}" max="${l.max}" step="${l.step}" value="${l.base}"></div>`).join("");
$("#initToggles").innerHTML = INIT.filter(i => i.value > 0).map(i => `<label><input type="checkbox" data-i="${i.id}"><span>${i.name}</span><span class="n">${eurS(i.value * IN_YEAR[i.id], 2)}</span></label>`).join("");
LEVERS.forEach(l => $("#lv-" + l.k).addEventListener("input", e => { state[l.k] = +e.target.value; $$("#presets button").forEach(b => b.classList.remove("on")); updateSim(); }));
$$("#initToggles input").forEach(c => c.addEventListener("change", () => { c.checked ? on.add(c.dataset.i) : on.delete(c.dataset.i); $$("#presets button").forEach(b => b.classList.remove("on")); updateSim(); }));
$$("#presets button").forEach(b => b.addEventListener("click", () => {
  const p = PRESETS[b.dataset.p];
  LEVERS.forEach(l => { state[l.k] = p.levers[l.k] ?? l.base; $("#lv-" + l.k).value = state[l.k]; });
  on.clear(); p.init.forEach(i => on.add(i));
  $$("#initToggles input").forEach(c => (c.checked = on.has(c.dataset.i)));
  $$("#presets button").forEach(x => x.classList.toggle("on", x === b));
  updateSim();
}));

function updateSim() {
  LEVERS.forEach(l => ($("#out-" + l.k).textContent = l.f(state[l.k])));
  const r = model(state, on);
  $("#simEbitda").textContent = eur(r.ebitda);
  $("#simSub").innerHTML = `Margin ${pct(r.margin)} on sales of ${eur(r.sales)} · ${eurS(r.ebitda - P25.ebitda)} vs FY2025${r.up > 0 ? ` · initiatives ${eurS(r.up, 2)}` : ""}`;
  drawSimChart(r);
  drawTornado();
}

function drawSimChart(r) {
  const el = $("#simChart");
  const { s, w, h } = svgFor(el, 170);
  const bars = [["FY2024", P24.ebitda, P24.ebitda_margin * 100, "var(--total)"], ["FY2025", P25.ebitda, P25.ebitda_margin * 100, "var(--total)"], ["FY2026 scenario", r.ebitda, r.margin, "var(--accent)"]];
  const L = 12, R = 12, T = 22, Bm = 26;
  const max = 80, min = Math.min(0, Math.floor(r.ebitda / 10) * 10);
  const y = v => T + (1 - (v - min) / (max - min)) * (h - T - Bm);
  const bw = Math.min(56, (w - L - R) / 3 * 0.5);
  sv("line", { x1: L, x2: w - R, y1: y(0), y2: y(0), stroke: "var(--axis)" }, s);
  bars.forEach(([lab, v, m, c], i) => {
    const cx = L + (i + 0.5) * (w - L - R) / 3;
    const g = sv("g", {}, s);
    sv("rect", { x: cx - bw / 2, y: Math.min(y(v), y(0)), width: bw, height: Math.max(2, Math.abs(y(v) - y(0))), rx: 4, fill: c }, g);
    txt(g, cx, Math.min(y(v), y(0)) - 6, eur(v), { "text-anchor": "middle", class: "val" });
    txt(g, cx, h - 8, lab, { "text-anchor": "middle", class: "lbl" });
    hover(g, `<b>${lab}</b><br>EBITDA ${eur(v, 2)}<br>Margin ${pct(m)}`);
  });
}

function drawTornado() {
  const base = model(state, on).ebitda;
  const tests = [
    ["Price +1%", { price: state.price + 1 }],
    ["Volume +1%", { volume: state.volume + 1 }],
    ["Containerboard +€10/t", { board: state.board + 10 }],
    ["Energy price +10%", { energy: state.energy + 10 }],
    ["Freight and handling +5%", { cts: state.cts + 5 }],
    ["SEK weaker by 0.30", { fx: state.fx + 0.3 }],
    ["Fixed inflation +1 pt", { fixed: state.fixed + 1 }],
  ].map(([lab, d]) => [lab, model(Object.assign({}, state, d), on).ebitda - base])
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const el = $("#tornado");
  const rowH = 26;
  const { s, w, h } = svgFor(el, tests.length * rowH + 4);
  const L = Math.min(170, w * 0.44), R = 4, pad = 52;
  const lim = Math.max(...tests.map(t => Math.abs(t[1])));
  const x = v => L + pad + (v + lim) / (2 * lim) * (w - L - R - 2 * pad);
  sv("line", { x1: x(0), x2: x(0), y1: 0, y2: h, stroke: "var(--axis)" }, s);
  tests.forEach(([lab, d], i) => {
    const y = i * rowH + 5, bh = 14;
    const a = x(Math.min(0, d)), b = x(Math.max(0, d));
    sv("rect", { x: a, y, width: Math.max(2, b - a), height: bh, rx: 3, fill: d < 0 ? "var(--neg)" : "var(--pos)" }, s);
    txt(s, L - 10, y + 11, lab, { "text-anchor": "end", class: "lbl" });
    txt(s, d < 0 ? a - 5 : b + 5, y + 11, eurS(d), { class: "val", "text-anchor": d < 0 ? "end" : "start" });
  });
}

// ------------------------------------------------------- 7. opportunities
function drawOpp() {
  const el = $("#oppMap");
  const { s, w, h } = svgFor(el, 290);
  const L = 44, R = 16, T = 14, B = 34;
  const x = v => L + (v - 0.5) / 5 * (w - L - R);
  const ymax = Math.ceil(Math.max(...INIT.map(i => i.value)) + 0.5);
  const y = v => T + (1 - v / ymax) * (h - T - B);
  sv("rect", { x: x(0.5), y: y(ymax), width: x(3) - x(0.5), height: y(ymax / 2.5) - y(ymax), fill: "var(--surface-2)" }, s);
  txt(s, x(0.5) + 8, y(ymax) + 16, "Quick wins", { class: "lbl", "font-weight": 650 });
  ticks(0, ymax, 4).forEach(t => {
    sv("line", { x1: L, x2: w - R, y1: y(t), y2: y(t), stroke: "var(--grid)" }, s);
    txt(s, L - 8, y(t) + 4, "€" + t + "m", { "text-anchor": "end" });
  });
  [1, 2, 3, 4, 5].forEach(t => txt(s, x(t), h - 16, t, { "text-anchor": "middle" }));
  txt(s, (L + w - R) / 2, h - 2, "effort (1 = weeks, 5 = new systems and a pilot)", { "text-anchor": "middle", "font-size": 11 });
  const short = { I1: "Index clauses", I2: "Cost-to-serve rules", I3: "Energy alerting", I4: "Trim waste", I5: "Demand sensing", I6: "AI commentary agent" };
  INIT.forEach(i => {
    const g = sv("g", {}, s);
    const cx = x(i.effort), cy = y(i.value);
    sv("circle", { cx, cy, r: 14, fill: "transparent" }, g);
    sv("circle", { cx, cy, r: 6, fill: i.confidence === "Low" ? "var(--surface)" : "var(--accent)", stroke: i.confidence === "Low" ? "var(--accent)" : "var(--surface)", "stroke-width": 2 }, g);
    const narrow = w < 560, right = cx < w - 150;
    const lx = narrow || right ? cx + 10 : cx - 10;
    txt(g, lx, cy + 4, narrow ? i.id : `${i.id} ${short[i.id]}`, { class: "lbl", "text-anchor": narrow || right ? "start" : "end" });
    hover(g, `<b>${i.id} ${i.name}</b><br>${i.value > 0 ? "Full-year value " + eur(i.value, 2) : "Value: controller capacity, about 1,100 h a year"}<br>Effort ${i.effort} of 5 · confidence ${i.confidence}<br>${i.time_to_value}`);
  });
  txt(s, w - R, T + 4, "hollow = low confidence", { "text-anchor": "end", "font-size": 11 });
}

(function initTable() {
  $("#initTable").innerHTML = `<tr><th>Initiative</th><th>Lever</th><th class="n">Full-year value</th><th class="n">Effort</th><th>Confidence</th><th>Time to value</th><th>How the value was sized</th></tr>` +
    INIT.map(i => `<tr><td><b>${i.id}</b> ${i.name}<div class="tiny">${i.how}</div></td><td>${i.lever}</td><td class="n">${i.value > 0 ? eur(i.value, 2) : "capacity"}</td><td class="n">${i.effort}/5</td><td><span class="pill">${i.confidence}</span></td><td class="small">${i.time_to_value}</td><td class="small">${i.basis}</td></tr>`).join("") +
    `<tr><td><b>Total</b></td><td></td><td class="n"><b>${eur(initTotal, 2)}</b></td><td colspan="4" class="small">About ${sign(initTotal / P25.net_sales * 100)} pp of margin at full run-rate.</td></tr>`;
})();

(function trackTable() {
  const small = DATA.tier_summary.find(t => t.tier === "Small");
  const baltics = DATA.yield_gap.find(y => y.plant === "Baltics");
  const best = Math.min(...DATA.yield_gap.map(y => y.usage));
  const rows = [
    ["I1 Index clauses", "Price realisation vs containerboard index", `Fixed ${sign(PC["Fixed annual"].price_change_pct)}% vs indexed ${sign(PC["Indexed"].price_change_pct)}% per t`, "40% of the gap closed at renewal", "Commercial director", "Monthly", "Share of renewed contracts with an index clause"],
    ["I2 Cost-to-serve rules", "Cost-to-serve per t, small accounts", `€${small.cts_per_t.toFixed(0)}/t`, "Below €250/t", "Sales and logistics", "Monthly", "Share of orders below minimum order quantity"],
    ["I3 Energy alerting", "MWh per t vs seasonal baseline", "Sweden Central about +17%", "Within ±3% at every plant", "Plant maintenance", "Weekly", "Alerts open longer than two weeks"],
    ["I4 Trim waste", "Board usage, t per t sold", `Baltics ${baltics.usage.toFixed(3)}`, `${((baltics.usage + best) / 2).toFixed(3)} (half the gap to best)`, "Production managers", "Weekly", "Trim loss % per shift"],
    ["I5 Demand sensing", "Changeovers per 1,000 t; forecast error (MAPE)", `${DATA.ops.orders_per_kt_2025} orders per 1,000 t`, "4% fewer changeovers in the pilot plant", "S&OP lead", "Monthly", "Forecast error on the pilot plant"],
    ["I6 AI commentary agent", "Controller hours on commentary; days to close", `About ${DATA.ops.commentary_hours_month} h per month`, "Under 10 h per month; close one day faster", "Head of controlling", "Monthly", "Share of drafts passing the number check first time"],
  ];
  $("#trackTable").innerHTML = `<tr><th>Initiative</th><th>Lagging KPI</th><th>Baseline FY2025</th><th>Target</th><th>Owner</th><th>Review</th><th>Leading indicator</th></tr>` +
    rows.map(r => `<tr>${r.map((c, j) => `<td class="${j ? "small" : ""}">${j ? c : "<b>" + c + "</b>"}</td>`).join("")}</tr>`).join("");
})();

// agent draft (markdown subset)
(function draft() {
  const lines = DRAFT_MD.split("\n").filter(l => !l.startsWith("# ") && !l.startsWith("_Source"));
  let html = "", inList = false;
  lines.forEach(l => {
    const t = l.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(\d{4}-\d{2}-\d{2})/g, m => niceDate(m));
    if (t.startsWith("- ")) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${t.slice(2)}</li>`; }
    else { if (inList) { html += "</ul>"; inList = false; } if (t.trim()) html += `<p>${t}</p>`; }
  });
  if (inList) html += "</ul>";
  const passed = /Number check PASSED/.test(DRAFT_MD);
  $("#draft").innerHTML = `<div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:8px"><span class="kicker" style="margin:0">Draft for controller review</span>${passed ? '<span class="status">Number check passed: every figure traces to the source</span>' : ""}</div>` + html;
})();

// ------------------------------------------------------------ render + resize
function drawAll() { drawWaterfall(); drawPriceSplit(); drawWhale(); drawScatter(); drawEnergy(); updateSim(); drawOpp(); }
drawAll();
let lastW = window.innerWidth, rt;
window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { if (Math.abs(window.innerWidth - lastW) > 20) { lastW = window.innerWidth; drawAll(); } }, 150); });

// nav highlight
const links = $$("nav.steps a");
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) links.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
}), { rootMargin: "-40% 0px -55% 0px" });
$$("section.step").forEach(s => io.observe(s));

// theme toggle
$("#themeBtn").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
});
})();
