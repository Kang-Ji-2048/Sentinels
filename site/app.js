/* Sentinels showcase: loads data/run.json (+ data/case.json if present) and drives the page. */
const COL = { dry_spill_candidate: [200, 16, 46], rain_explained: [18, 53, 91], no_gauge: [110, 120, 125] };   // Figma tokens
const NEUTRAL = [18, 53, 91];
const fmt = n => Number(n).toLocaleString("en-GB");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const title = s => String(s || "").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
const when = t => t ? new Date(t.replace(" ", "T")).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) : "ongoing";

const hours = d => d.duration_hours != null ? `${d.duration_hours} h discharging` : "duration unknown (monitor offline)";

const ENGLAND = { longitude: -1.9, latitude: 52.9, zoom: 5.4, pitch: 0, bearing: 0 };
const isSmall = matchMedia("(max-width: 600px)").matches;
if (isSmall) ENGLAND.zoom = 4.6;

// Show the demo video only once site/media/demo.mp4 exists; until then a placeholder.
async function setupVideo() {
  const v = document.getElementById("demo-video");
  try {
    const r = await fetch("media/demo.mp4", { method: "HEAD" });
    if (!r.ok) return;
    v.hidden = false;
    document.getElementById("video-pending").remove();
  } catch (_) { /* keep the placeholder */ }
}

async function main() {
  setupVideo();
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
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const dry = spills.filter(d => d.verdict === "dry_spill_candidate");
  let step = -1;          // discrete styling state (nearest step)
  let cam = null;         // current camera, driven by scroll
  let pulse = 0;

  const views = [
    { ...ENGLAND, pitch: 20 },
    { ...ENGLAND, pitch: 35, bearing: -10, zoom: ENGLAND.zoom + .1 },
    { ...ENGLAND, pitch: 40, bearing: 8, zoom: ENGLAND.zoom + .2 },
    { longitude: caseSpill.longitude, latitude: caseSpill.latitude, zoom: isSmall ? 10 : 10.6, pitch: 45, bearing: -18 },
  ];

  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const size = d => Math.min(2.6 + 1.9 * Math.sqrt(Math.max(d.duration_hours || 0, 0.2)), 13);   // px, area ~ hours
  const links = spills.flatMap(d => (d.gauges || []).filter(g => g.lat != null)
    .map(g => ({ from: [d.longitude, d.latitude], to: [g.lon, g.lat], dry: d.verdict === "dry_spill_candidate", isCase: d.id === caseSpill.id, g })));
  const gauges = [...new Map([...links].sort((a, b) => a.isCase - b.isCase).map(l => [l.g.station, l])).values()];  // case links win
  const caseLinks = links.filter(l => l.isCase);
  const NO_DEPTH = { depthCompare: "always", depthWriteEnabled: false };   // flat overlay: never clipped by the ground
  const T = { duration: 900, easing: t => t * (2 - t) };

  const layers = () => {
    const s = Math.max(step, 0);
    const spillAlpha = d => (s >= 2 && d.verdict !== "dry_spill_candidate") ? 50 : (s === 3 && d.id !== caseSpill.id) ? 110 : 235;
    const colour = d => s === 0 ? NEUTRAL : (COL[d.verdict] || NEUTRAL);
    const linkAlpha = l => s === 0 ? 0 : s === 1 ? 90 : s === 2 ? (l.dry ? 80 : 12) : (l.isCase ? 220 : 10);
    return [
      new deck.LineLayer({
        id: "links", parameters: NO_DEPTH, data: links, getSourcePosition: l => l.from, getTargetPosition: l => l.to,
        getColor: l => [18, 53, 91, linkAlpha(l)], getWidth: l => (s === 3 && l.isCase ? 2 : 1), widthUnits: "pixels",
        updateTriggers: { getColor: s, getWidth: s }, transitions: { getColor: T },
      }),
      new deck.ScatterplotLayer({
        id: "gauges", parameters: NO_DEPTH, billboard: true, data: gauges, getPosition: l => l.to, radiusUnits: "pixels",
        getRadius: l => (s === 3 && l.isCase ? 5 : 2.2), stroked: true, lineWidthUnits: "pixels", getLineWidth: 1,
        getFillColor: l => [243, 246, 241, s === 0 ? 0 : (s === 3 && !l.isCase ? 40 : 255)],
        getLineColor: l => [18, 53, 91, s === 0 ? 0 : (s === 3 && !l.isCase ? 60 : 255)],
        updateTriggers: { getRadius: s, getFillColor: s, getLineColor: s }, transitions: { getFillColor: T, getRadius: T },
      }),
      new deck.ScatterplotLayer({   // 10 km search radius around the followed case
        id: "radius", parameters: NO_DEPTH, data: s === 3 ? [caseSpill] : [], getPosition: d => [d.longitude, d.latitude],
        getRadius: 10000, radiusUnits: "meters", stroked: true, filled: true,
        getFillColor: [232, 197, 71, 60], getLineColor: [184, 146, 20, 255], lineWidthUnits: "pixels", getLineWidth: 1,
      }),
      new deck.ScatterplotLayer({   // soft glow
        id: "glow", parameters: NO_DEPTH, billboard: true, data: spills, getPosition: d => [d.longitude, d.latitude], radiusUnits: "pixels",
        getRadius: d => size(d) * 2.1, getFillColor: d => [...colour(d), spillAlpha(d) * 0.16],
        updateTriggers: { getFillColor: s }, transitions: { getFillColor: T },
      }),
      new deck.ScatterplotLayer({   // pulse ring on dry-day spills
        id: "pulse", parameters: NO_DEPTH, billboard: true, data: s >= 2 ? dry : [], getPosition: d => [d.longitude, d.latitude], radiusUnits: "pixels",
        getRadius: d => size(d), radiusScale: 1 + 1.6 * pulse, stroked: true, filled: false,
        lineWidthUnits: "pixels", getLineWidth: 1.2, getLineColor: d => [200, 16, 46, (s === 3 && d.id !== caseSpill.id ? 40 : 170) * (1 - pulse)],
        updateTriggers: { getLineColor: s },
      }),
      new deck.ScatterplotLayer({
        id: "spills", parameters: NO_DEPTH, billboard: true, data: spills, getPosition: d => [d.longitude, d.latitude], radiusUnits: "pixels",
        getRadius: d => size(d) * (s === 3 && d.id === caseSpill.id ? 1.4 : 1), pickable: true, autoHighlight: true,
        highlightColor: [255, 255, 255, 70], stroked: true, lineWidthUnits: "pixels", getLineWidth: 1,
        getFillColor: d => [...colour(d), spillAlpha(d)], getLineColor: d => [255, 255, 255, spillAlpha(d) * 0.8],
        updateTriggers: { getFillColor: s, getLineColor: s, getRadius: s }, transitions: { getFillColor: T, getRadius: T },
      }),
      new deck.TextLayer({
        id: "labels", parameters: NO_DEPTH, data: s === 3 ? caseLinks : [], getPosition: l => l.to,
        getText: l => `${l.g.km} km · ${Math.max(l.g.mm_0_24h_before, l.g.mm_24_48h_before)} mm`,
        getSize: 13, getColor: [20, 32, 43, 255], getPixelOffset: [0, -16], fontFamily: "Archivo, sans-serif", fontWeight: 600,
        outlineWidth: 5, outlineColor: [243, 246, 241, 255], fontSettings: { sdf: true }, characterSet: "auto",
      }),
    ];
  };

  const box = document.getElementById("deck");
  // MapLibre owns the camera; the deck.gl overlay follows the map's own move events, so the street map
  // and the data redraw together. (Not interleaved: that mode can't add layers until the style has loaded.)
  const v0 = views[0];
  const map = new maplibregl.Map({
    container: "deck",
    style: "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
    center: [v0.longitude, v0.latitude], zoom: v0.zoom, pitch: v0.pitch, bearing: v0.bearing,
    interactive: false,             // the camera is driven by scrolling
    attributionControl: { compact: true },
    pixelRatio: Math.min(devicePixelRatio || 1, 2),
    fadeDuration: 0,
  });
  const overlay = new deck.MapboxOverlay({
    layers: layers(),
    onHover: ({ object, x, y }) => {
      if (!object || !object.company) { tip.hidden = true; return; }
      tip.hidden = false;
      tip.style.left = Math.min(x + 14, innerWidth - 280) + "px"; tip.style.top = (y + 14) + "px";
      tip.innerHTML = `<div class="t">${esc(title(object.receivingwatercourse) || object.id)}</div>
        <div>${esc(object.company)} · ${esc(object.id)}</div>
        <div class="m">${esc(object.verdict.replace(/_/g, " "))}<br>${hours(object)}<br>
        rain 24 h before: ${object.max_mm_0_24h_before ?? "n/a"} mm</div>`;
    },
  });
  map.addControl(overlay);

  const fly = new deck.FlyToInterpolator({ curve: 1.3 });
  const stepEls = [...document.querySelectorAll(".step")];

  // Scroll position -> continuous progress t in [0, steps-1].
  function progress() {
    const mid = innerHeight / 2;
    const centres = stepEls.map(el => { const r = el.getBoundingClientRect(); return r.top + r.height / 2 - mid; });
    if (centres[0] >= 0) return 0;
    for (let i = 0; i < centres.length - 1; i++) {
      if (centres[i + 1] > 0) return i + (-centres[i]) / (centres[i + 1] - centres[i]);
    }
    return centres.length - 1;
  }

  function cameraAt(t) {
    const i = Math.min(Math.floor(t), views.length - 2);
    const f = ease(Math.min(Math.max(t - i, 0), 1));
    const size = { width: box.clientWidth, height: box.clientHeight };
    const a = { ...views[i], ...size }, b = { ...views[i + 1], ...size };
    return fly.interpolateProps(a, b, f);
  }

  // Smoothly chase the scroll target every frame (critically damped), so fast scrolls still glide.
  let target = 0, shown = 0, lastT = performance.now(), running = false;
  function frame(now) {
    try { step_(now); } catch (e) { console.error(e); }   // never let one bad frame stop the animation
    if (running) requestAnimationFrame(frame);
  }
  function step_(now) {
    const dt = Math.min(now - lastT, 64); lastT = now;
    target = progress();
    shown += (target - shown) * (1 - Math.exp(-dt / (reduced ? 1 : 140)));
    if (Math.abs(target - shown) < 1e-4) shown = target;
    const c = cameraAt(shown);
    if (!reduced) c.bearing += 3 * Math.sin(now / 7000);     // slow drift keeps the scene alive
    cam = c;
    pulse = reduced ? 0 : (now % 2400) / 2400;
    // Hysteresis: only switch styling once clearly past the halfway point, so colours never flicker.
    const s = step < 0 ? Math.round(shown) : (shown > step + 0.6 ? Math.round(shown) : shown < step - 0.6 ? Math.round(shown) : step);
    if (s !== step) {
      step = s;
      stepEls.forEach(x => x.classList.toggle("active", +x.dataset.step === s));
    }
    map.jumpTo({ center: [c.longitude, c.latitude], zoom: c.zoom, pitch: c.pitch, bearing: c.bearing });
    overlay.setProps({ layers: layers() });
  }
  new IntersectionObserver(([e]) => {
    if (e.isIntersecting && !running) { running = true; lastT = performance.now(); requestAnimationFrame(frame); }
    else if (!e.isIntersecting) running = false;
  }, { rootMargin: "200px 0px" }).observe(document.getElementById("map"));

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
      <div class="conf"><span>skeptic: breach likely?</span><div class="track"><div class="fill" style="width:${conf * 100}%"></div></div><span>${conf.toFixed(2)}</span></div>`);
  }
  if (c.evidence) {
    const srcs = c.evidence.searches.flatMap(q => q.sources || []).filter((x, i, a) => x.url && a.findIndex(y => y.url === x.url) === i).slice(0, 8);
    set("evidence", `<p>${c.evidence.searches.length} live searches.</p>
      <ul>${c.evidence.searches.map(q => `<li>${esc(q.query)}</li>`).join("")}</ul>
      <p><b>Sources cited</b></p><ul class="sources">${srcs.map(x => `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.name || x.url)}</a></li>`).join("")}</ul>`);
  } else {
    set("evidence", "<p>Skipped: the skeptic was near-certain this spill is innocent, so no web search was spent on it.</p>");
  }
  if (c.ruling) {
    const r = c.ruling, from = Number(c.skeptic_confidence ?? c.skeptic?.breach_confidence), to = Number(r.final_confidence);
    set("adjudicator", `<p>${esc(r.reasoning)}</p>
      <div class="ruling"><div><h6>Refuted</h6><ul>${(r.objections_refuted || []).map(x => `<li>${esc(x)}</li>`).join("") || "<li>None</li>"}</ul></div>
      <div><h6>Still standing</h6><ul>${(r.objections_standing || []).map(x => `<li>${esc(x)}</li>`).join("") || "<li>None</li>"}</ul></div></div>
      <div class="conf"><span>${isNaN(from) ? "" : from.toFixed(2) + " → "}final</span><div class="track"><div class="fill" style="width:${to * 100}%"></div></div><span>${to.toFixed(2)}</span></div>`);
  } else {
    set("adjudicator", "<p>Not needed: the skeptic was near-certain this spill is innocent, so the case stopped early.</p>");
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
