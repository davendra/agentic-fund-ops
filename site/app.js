/* Agentic Fund-Ops — static site. Loads the baked data.json snapshot and renders
   KPIs, charts (Chart.js) and the validation-anomalies table. No backend. */
const C = { navy: "#0B1F33", coral: "#FF5A3C", teal: "#0FB5A0", gold: "#E8B23A", slate: "#5B6B7B", line: "#e4e9f0" };

const money = (v) => {
  const a = Math.abs(v);
  if (a >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
  if (a >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return "$" + (v / 1e3).toFixed(0) + "K";
  return "$" + v;
};

function kpis(d) {
  const k = d.kpis;
  const acc = d.eval.accuracy_pct.ai_query;
  const ca = k.capital_accounts || 0;
  const cards = [
    { v: k.capital_calls + k.distributions + ca, l: "documents" },
    { v: k.capital_calls, l: "capital calls" },
    { v: k.distributions, l: "distributions" },
    { v: ca, l: "capital accounts" },
    { v: money(k.usd_called), l: "USD called" },
    { v: k.nav ? money(k.nav) : "—", l: "LP NAV tracked" },
    { v: k.anomalies, l: "anomalies flagged" },
    { v: acc + "%", l: "extraction accuracy" },
  ];
  document.getElementById("kpis").innerHTML = cards
    .map((c) => `<div class="kpi"><div class="v">${c.v}</div><div class="l">${c.l}</div></div>`)
    .join("");
}

function baseOpts(extra = {}) {
  return Object.assign({
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { backgroundColor: C.navy } },
    scales: { x: { grid: { display: false }, ticks: { color: C.slate, font: { size: 11 } } },
              y: { grid: { color: C.line }, ticks: { color: C.slate, font: { size: 11 } }, beginAtZero: true } },
  }, extra);
}

function charts(d) {
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = C.slate;

  // currency
  new Chart(document.getElementById("chart-currency"), {
    type: "bar",
    data: { labels: d.by_currency.map((r) => r.currency),
      datasets: [{ data: d.by_currency.map((r) => r.total_called), backgroundColor: C.teal, borderRadius: 6, maxBarThickness: 90 }] },
    options: baseOpts({ plugins: { legend: { display: false },
      tooltip: { backgroundColor: C.navy, callbacks: { label: (c) => money(c.parsed.y) } } },
      scales: { x: { grid: { display: false }, ticks: { color: C.slate } },
                y: { grid: { color: C.line }, beginAtZero: true, ticks: { color: C.slate, callback: (v) => money(v) } } } }),
  });

  // docs by fund (stacked)
  const funds = [...new Set(d.docs_by_fund.map((r) => r.fund))];
  const pick = (t) => funds.map((f) => (d.docs_by_fund.find((r) => r.fund === f && r.doc_type === t) || {}).n || 0);
  new Chart(document.getElementById("chart-funds"), {
    type: "bar",
    data: { labels: funds, datasets: [
      { label: "capital_call", data: pick("capital_call"), backgroundColor: C.teal, borderRadius: 4 },
      { label: "distribution", data: pick("distribution"), backgroundColor: C.coral, borderRadius: 4 },
      { label: "capital_account", data: pick("capital_account"), backgroundColor: C.gold, borderRadius: 4 } ] },
    options: baseOpts({ plugins: { legend: { display: true, position: "top", labels: { boxWidth: 12, font: { size: 11 } } }, tooltip: { backgroundColor: C.navy } },
      scales: { x: { stacked: true, grid: { display: false }, ticks: { color: C.slate, font: { size: 9 }, maxRotation: 60, minRotation: 60 } },
                y: { stacked: true, grid: { color: C.line }, beginAtZero: true, ticks: { color: C.slate } } } }),
  });

  // LP net asset value by fund (capital accounts) — only if data present
  const navEl = document.getElementById("chart-nav");
  if (navEl && d.nav_by_fund && d.nav_by_fund.length) {
    new Chart(navEl, {
      type: "bar",
      data: { labels: d.nav_by_fund.map((r) => r.fund.replace(/[-_]/g, " ")),
        datasets: [{ data: d.nav_by_fund.map((r) => r.nav), backgroundColor: C.gold, borderRadius: 6, maxBarThickness: 48 }] },
      options: baseOpts({ indexAxis: "y",
        plugins: { legend: { display: false }, tooltip: { backgroundColor: C.navy, callbacks: { label: (c) => money(c.parsed.x) } } },
        scales: { x: { grid: { color: C.line }, beginAtZero: true, ticks: { color: C.slate, callback: (v) => money(v) } },
                  y: { grid: { display: false }, ticks: { color: C.slate, font: { size: 10 } } } } }),
    });
  }

  // distributions by type (doughnut)
  const palette = [C.teal, C.coral, C.gold, C.navy, C.slate, "#8aa0b3"];
  new Chart(document.getElementById("chart-disttype"), {
    type: "doughnut",
    data: { labels: d.dist_by_type.map((r) => r.type),
      datasets: [{ data: d.dist_by_type.map((r) => r.n), backgroundColor: palette, borderWidth: 2, borderColor: "#fff" }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: "58%",
      plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } }, tooltip: { backgroundColor: C.navy } } },
  });

  // trend (line)
  new Chart(document.getElementById("chart-trend"), {
    type: "line",
    data: { labels: d.trend.map((r) => r.yq),
      datasets: [{ data: d.trend.map((r) => r.total_called), borderColor: C.teal, backgroundColor: "rgba(15,181,160,.12)",
        fill: true, tension: .25, pointRadius: 2, pointBackgroundColor: C.teal, borderWidth: 2 }] },
    options: baseOpts({ plugins: { legend: { display: false }, tooltip: { backgroundColor: C.navy, callbacks: { label: (c) => money(c.parsed.y) } } },
      scales: { x: { grid: { display: false }, ticks: { color: C.slate, font: { size: 9 }, maxRotation: 60, minRotation: 60 } },
                y: { grid: { color: C.line }, beginAtZero: true, ticks: { color: C.slate, callback: (v) => money(v) } } } }),
  });

  // eval comparison
  const e = d.eval.accuracy_pct;
  new Chart(document.getElementById("chart-eval"), {
    type: "bar",
    data: { labels: ["ai_query\n(structured)", "ai_extract\n(baseline)"],
      datasets: [{ data: [e.ai_query, e.ai_extract], backgroundColor: [C.teal, C.slate], borderRadius: 7, maxBarThickness: 110 }] },
    options: baseOpts({ plugins: { legend: { display: false }, title: { display: true, text: "Extraction accuracy (%)", color: C.navy, font: { family: "Space Grotesk", size: 14 } },
      tooltip: { backgroundColor: C.navy, callbacks: { label: (c) => c.parsed.y + "%" } } },
      scales: { x: { grid: { display: false }, ticks: { color: C.navy, font: { size: 12 } } },
                y: { grid: { color: C.line }, beginAtZero: true, max: 100, ticks: { color: C.slate, callback: (v) => v + "%" } } } }),
  });
}

function anomalies(d) {
  document.getElementById("anom-count").textContent = d.kpis.anomalies;
  document.getElementById("gold-docs").textContent = d.eval.gold_docs;
  const tb = document.querySelector("#anom-table tbody");
  tb.innerHTML = d.anomalies.map((a) =>
    `<tr><td title="${a.file}">${a.file.replace(/\.pdf$/, "")}</td><td>${a.check}</td><td class="sev ${a.severity}">${a.severity}</td></tr>`
  ).join("");
}

function setSource(d) {
  const el = document.getElementById("data-source");
  if (!el) return;
  if (d.live) { el.textContent = "● Live from Databricks"; el.className = "src live"; }
  else { el.textContent = "● Snapshot"; el.className = "src snap"; }
}

// Try the live serverless endpoint (Vercel) first; fall back to the baked
// snapshot (data.json) — which is what GitHub Pages serves.
fetch("/api/data")
  .then((r) => (r.ok ? r.json() : Promise.reject(new Error("no api"))))
  .catch(() => fetch("data.json").then((r) => r.json()))
  .then((d) => { kpis(d); charts(d); anomalies(d); setSource(d); })
  .catch((e) => console.error("data load failed", e));
