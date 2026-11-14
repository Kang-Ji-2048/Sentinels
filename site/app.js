/* Sentinels showcase: loads data/run.json (+ data/case.json if present) and drives the page. */
const COL = { dry_spill_candidate: [239, 91, 69], rain_explained: [106, 166, 216], no_gauge: [125, 135, 150] };
const NEUTRAL = document.documentElement.dataset.variant === "b" ? [36, 61, 89] : [208, 183, 132];
const fmt = n => Number(n).toLocaleString("en-GB");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const title = s => String(s || "").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
const when = t => t ? new Date(t.replace(" ", "T")).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) : "ongoing";

const hours = d => d.duration_hours != null ? `${d.duration_hours} h discharging` : "duration unknown (monitor offline)";

const ENGLAND = { longitude: -1.9, latitude: 52.9, zoom: 5.4, pitch: 0, bearing: 0 };
const isSmall = matchMedia("(max-width: 600px)").matches;
if (isSmall) ENGLAND.zoom = 4.6;

const VARIANT = document.documentElement.dataset.variant || "a";
const BASEMAP = VARIANT === "b"
  ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
  : "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

function applyVariant() {
  document.querySelectorAll(".variant-switch a").forEach(a => a.classList.toggle("on", a.getAttribute("href") === "?v=" + VARIANT));
  if (VARIANT !== "c") return;
  // Map first: move the hero into the scrollytelling as step 0, over the map.
  const hero = document.querySelector(".hero");
  const wrap = document.createElement("div");
  wrap.className = "hero-card";
  while (hero.firstChild) wrap.appendChild(hero.firstChild);
  hero.appendChild(wrap);
  hero.classList.add("step", "in-map");
  hero.dataset.step = "0";
  document.querySelector(".steps").prepend(hero);
}

async function main() {
  applyVariant();
  const run = await (await fetch("data/run.json")).json();
  let caseData = null;
  try { const r = await fetch("data/case.json"); if (r.ok) caseData = await r.json(); } catch (_) { /* no case yet */ }

  const dry = run.spills.filter(s => s.verdict === "dry_spill_candidate");
  const caseSpill = (caseData && run.spills.find(s => s.id === caseData.site_id))
    || dry.filter(s => !s.monitor_offline && s.duration_hours != null).sort((a, b) => b.duration_hours - a.duration_hours)[0]
    || dry[0];

  fillStats(run, dry.length);
  bars(run.by_company);
  document.getElementById("bars-cap").textContent = `Fig. 3 — Dry-day spill candidates by water company, 48 h to ${when(run.run_at)}`;
  renderCase(caseSpill, caseData);
  setupMap(run.spills, caseSpill);
  reveals();
}

function fillStats(run, nDry) {
  const vals = { overflows: run.overflows, recent_spills: run.recent_spills, dry: nDry };
  document.querySelectorAll("[data-k]").forEach(el => { el.textContent = fmt(vals[el.dataset.k]); });
  document.getElementById("asof").textContent = `Live run, ${when(run.run_at)} UK time`;
}

function bars(byCompany) {
  const rows = Object.entries(byCompany).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map(r => r[1]));
  const el = document.getElementById("bars");
  el.innerHTML = rows.map(([c, n]) => `<div class="bar"><span>${esc(c)}</span><div class="track"><div class="fill" data-w="${(100 * n / max).toFixed(1)}"></div></div><span class="n">${n}</span></div>`).join("");
  new IntersectionObserver((es, o) => {
    if (es[0].isIntersecting) { el.querySelectorAll(".fill").forEach((f, i) => setTimeout(() => f.style.width = f.dataset.w + "%", i * 70)); o.disconnect(); }
  }, { threshold: .3 }).observe(el);
}

/* ---------------- Map ---------------- */
function setupMap(spills, caseSpill) {
  if (!window.deck) { document.getElementById("deck").innerHTML = '<p style="padding:120px 24px;color:#6f7f89">Map failed to load.</p>'; return; }
  const tip = document.getElementById("tip");
  let step = 0;
  const layer = () => new deck.ColumnLayer({
    id: "spills", data: spills, diskResolution: 16, radius: step === 3 ? 350 : (isSmall ? 3500 : 2600), extruded: true, pickable: true, autoHighlight: true,
    highlightColor: [255, 255, 255, 90],
    getPosition: d => [d.longitude, d.latitude],
    getElevation: d => {
      const h = Math.max(d.duration_hours || 0, 0.4);
      if (step === 0) return 400;
      if (step >= 2 && d.verdict !== "dry_spill_candidate") return 300;
      return h * (step === 3 ? 120 : 1500);
    },
    getFillColor: d => {
      if (step === 0) return [...NEUTRAL, 200];
      const c = COL[d.verdict] || NEUTRAL;
      if (step >= 2 && d.verdict !== "dry_spill_candidate") return [...c, 45];
      if (step === 3 && d.id !== caseSpill.id) return [...c, 120];
      return [...c, 235];
    },
    updateTriggers: { getElevation: step, getFillColor: step },
    transitions: { getElevation: { duration: 1400, easing: t => 1 - Math.pow(1 - t, 3) }, getFillColor: 900 },
  });

  const views = [
    ENGLAND,
    { ...ENGLAND, pitch: 50, bearing: -12 },
    { ...ENGLAND, pitch: 55, bearing: 12, zoom: ENGLAND.zoom + .2 },
    { longitude: caseSpill.longitude, latitude: caseSpill.latitude, zoom: isSmall ? 10 : 11, pitch: 62, bearing: -25 },
  ];

  const dg = new deck.DeckGL({
    container: "deck",
    mapStyle: BASEMAP,
    initialViewState: views[0],
    controller: isSmall ? false : { scrollZoom: false },
    layers: [layer()],
    onHover: ({ object, x, y }) => {
      if (!object) { tip.hidden = true; return; }
      tip.hidden = false;
      tip.style.left = Math.min(x + 14, innerWidth - 280) + "px"; tip.style.top = (y + 14) + "px";
      tip.innerHTML = `<div class="t">${esc(title(object.receivingwatercourse) || object.id)}</div>
        <div>${esc(object.company)} · ${esc(object.id)}</div>
        <div class="m">${esc(object.verdict.replace(/_/g, " "))}<br>${hours(object)}<br>
        rain 24 h before: ${object.max_mm_0_24h_before ?? "n/a"} mm</div>`;
    },
  });

  const go = s => {
    if (s === step) return;
    step = s;
    dg.setProps({
      layers: [layer()],
      initialViewState: { ...views[s], transitionDuration: s === 3 ? 3200 : 1800, transitionInterpolator: new deck.FlyToInterpolator({ speed: 1.2 }) },
    });
  };
  const stepEls = document.querySelectorAll(".step");
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    stepEls.forEach(x => x.classList.toggle("active", x === e.target));
    go(+e.target.dataset.step);
  }), { rootMargin: "-45% 0px -45% 0px" });
  stepEls.forEach(el => io.observe(el));

  // Retitle the last step for the case being followed.
  const last = document.querySelector('.step[data-step="3"] .card');
  last.querySelector("h3").textContent = `${title(caseSpill.receivingwatercourse)}, ${caseSpill.company}`;
  const g = caseSpill.gauges || [];
  const mm = g.flatMap(x => [x.mm_0_24h_before, x.mm_24_48h_before]);
  last.querySelector("p").textContent = `${caseSpill.latesteventend ? "Discharged" : "Discharging"} for ${caseSpill.duration_hours} hours. ${g.length} rain gauge${g.length === 1 ? "" : "s"} nearby recorded between ${Math.min(...mm)} and ${Math.max(...mm)} mm in the two days before it began. This is the case we follow through the agents below.`;
}

/* ---------------- Case ---------------- */
function renderCase(s, c) {
  document.getElementById("case-title").textContent = `${title(s.receivingwatercourse)} · ${s.company}`;
  const statusTxt = { 1: "discharging", 0: "stopped", "-1": "monitor offline" }[s.status] ?? s.status;
  document.getElementById("case-kv").outerHTML = `<dl class="kv">
    <dt>Overflow</dt><dd>${esc(s.id)}</dd>
    <dt>Spill started</dt><dd>${when(s.latesteventstart)}</dd>
    <dt>Spill ended</dt><dd>${when(s.latesteventend)}</dd>
    <dt>Duration</dt><dd>${s.duration_hours != null ? s.duration_hours + " h" : "unknown (monitor offline)"}</dd>
    <dt>Feed status now</dt><dd>${esc(statusTxt)}</dd>
    <dt>Verdict</dt><dd class="hot">${esc(s.verdict.replace(/_/g, " "))}</dd></dl>`;
  const wet = g => Math.max(g.mm_0_24h_before, g.mm_24_48h_before);
  const scale = Math.max(0.5, ...(s.gauges || []).map(wet));
  document.getElementById("gauges").innerHTML = (s.gauges || []).map(g => {
    const tot = wet(g);
    return `<div class="gauge"><div class="g-h"><span>Gauge ${esc(g.station)} · ${g.km} km</span><span>${tot} mm</span></div>
      <div class="g-t"><div class="g-f" style="width:${100 * tot / scale}%"></div><div class="g-th" style="left:${100 * 0.25 / scale}%"></div></div></div>`;
  }).join("");

  if (!c) return;
  document.getElementById("pending-note").textContent =
    `Real output from one traced run, decided ${when(c.decided_at)}. Final verdict: ${String(c.final_verdict).replace(/_/g, " ")}.`;
  const set = (k, html) => { const b = document.querySelector(`[data-agent="${k}"] .body`); b.classList.remove("pending"); b.innerHTML = html; };
  if (c.case) set("investigator", `<p>${esc(c.case.summary)}</p>
    <ul>${(c.case.breach_indicators || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    <p>Severity <span class="pill">${esc(c.case.severity)}</span> Repeat offender <span class="pill">${c.case.repeat_offender ? "yes" : "no"}</span></p>`);
  if (c.skeptic) {
    const conf = Number(c.skeptic.breach_confidence);
    document.querySelector('[data-agent="skeptic"] h4 small').textContent = c.skeptic.model || "different model";
    set("skeptic", `<p><b>Strongest objection:</b> ${esc(c.skeptic.strongest_objection)}</p>
      <ul>${(c.skeptic.innocent_explanations || []).map(x => `<li>${esc(x.explanation)} <span class="pill">${esc(x.plausibility)}</span></li>`).join("")}</ul>
      <div class="conf"><span>breach confidence</span><div class="track"><div class="fill" style="width:${conf * 100}%"></div></div><span>${conf.toFixed(2)}</span></div>`);
  }
  if (c.evidence) {
    const srcs = c.evidence.searches.flatMap(q => q.sources || []).filter((x, i, a) => x.url && a.findIndex(y => y.url === x.url) === i).slice(0, 8);
    set("evidence", `<p>${c.evidence.searches.length} live searches.</p>
      <ul>${c.evidence.searches.map(q => `<li>${esc(q.query)}</li>`).join("")}</ul>
      <p><b>Sources cited</b></p><ul class="sources">${srcs.map(x => `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.name || x.url)}</a></li>`).join("")}</ul>`);
  } else {
    set("evidence", "<p>Skipped: the skeptic's confidence was too low to spend a web search on this case.</p>");
  }
  if (c.report && window.marked) set("drafter", `<div class="report">${marked.parse(esc(c.report).replace(/&gt;/g, ">"))}</div>`);
  else if (!c.report) set("drafter", "<p>No report drafted for this verdict.</p>");
}

function reveals() {
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: .2 });
  document.querySelectorAll(".band h2, .band .sub, .why > div, .panel, .limits li").forEach(el => { el.classList.add("reveal"); io.observe(el); });
  const flow = document.querySelector(".flow");
  flow.querySelectorAll(".node").forEach((n, i) => n.style.transitionDelay = (i * 70) + "ms");
  io.observe(flow);
}

main();
