// Vercel serverless function: live data from Databricks fund_ops.silver via the
// SQL Statement Execution API. Credentials come from Vercel env vars (server-side
// only — never shipped to the browser or committed). Falls back to the baked
// snapshot (../data.json) if the workspace is unreachable or the warehouse is cold.
const fallback = require("../data.json");

const HOST = (process.env.DATABRICKS_HOST || "").replace(/\/$/, "");
const TOKEN = process.env.DATABRICKS_TOKEN || "";
const WH = process.env.DATABRICKS_WAREHOUSE_ID || "";
const T = "`fund_ops`.`silver`";

async function q(statement) {
  const body = { warehouse_id: WH, statement, format: "JSON_ARRAY", disposition: "INLINE",
    wait_timeout: "30s", on_wait_timeout: "CONTINUE" };
  let r = await fetch(`${HOST}/api/2.0/sql/statements`, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let j = await r.json();
  const id = j.statement_id;
  const deadline = Date.now() + 45000;
  while (j.status && (j.status.state === "PENDING" || j.status.state === "RUNNING")) {
    if (Date.now() > deadline) throw new Error("timeout");
    await new Promise((s) => setTimeout(s, 1500));
    const g = await fetch(`${HOST}/api/2.0/sql/statements/${id}`, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });
    j = await g.json();
  }
  if (!j.status || j.status.state !== "SUCCEEDED")
    throw new Error((j.status && j.status.error && j.status.error.message) || "query failed");
  return (j.result && j.result.data_array) || [];
}

module.exports = async (req, res) => {
  try {
    if (!HOST || !TOKEN || !WH) throw new Error("missing Databricks env vars");
    const [kpi, cur, fund, dist, trend, rank, anom] = await Promise.all([
      q(`SELECT (SELECT count(*) FROM ${T}.capital_calls),
                (SELECT count(*) FROM ${T}.distributions),
                (SELECT sum(CASE WHEN currency='USD' THEN total_called ELSE 0 END) FROM ${T}.capital_calls),
                (SELECT count(*) FROM ${T}.validation_results WHERE passed=false)`),
      q(`SELECT currency, sum(total_called) FROM ${T}.capital_calls WHERE currency IS NOT NULL GROUP BY currency ORDER BY 2 DESC`),
      q(`SELECT split(file_name,'__')[0] fund, doc_type, count(*) FROM (
            SELECT file_name,doc_type FROM ${T}.capital_calls
            UNION ALL SELECT file_name,doc_type FROM ${T}.distributions) GROUP BY fund,doc_type ORDER BY fund`),
      q(`SELECT coalesce(distribution_type,'(unspecified)'), count(*) FROM ${T}.distributions GROUP BY 1 ORDER BY 2 DESC`),
      q(`SELECT concat(year(try_to_date(notice_date)),'-Q',quarter(try_to_date(notice_date))), sum(total_called)
            FROM ${T}.capital_calls WHERE try_to_date(notice_date) IS NOT NULL GROUP BY 1 ORDER BY 1`),
      q(`SELECT fund_name, sum(total_called), count(*), avg(total_called) FROM ${T}.capital_calls
            WHERE fund_name IS NOT NULL GROUP BY fund_name ORDER BY 2 DESC LIMIT 10`),
      q(`SELECT file_name, doc_type, check_name, severity, detail FROM ${T}.validation_results
            WHERE passed=false ORDER BY severity, file_name`),
    ]);
    const num = (x) => (x === null || x === undefined ? null : Number(x));
    const data = {
      live: true,
      generated_note: "Live from Databricks fund_ops.silver via the SQL Statement Execution API.",
      kpis: { capital_calls: num(kpi[0][0]), distributions: num(kpi[0][1]), usd_called: num(kpi[0][2]),
        anomalies: num(kpi[0][3]), funds: 7, currencies: 3, gold_docs: fallback.eval.gold_docs },
      by_currency: cur.map((r) => ({ currency: r[0], total_called: num(r[1]) })),
      docs_by_fund: fund.map((r) => ({ fund: r[0], doc_type: r[1], n: num(r[2]) })),
      dist_by_type: dist.map((r) => ({ type: r[0], n: num(r[1]) })),
      trend: trend.map((r) => ({ yq: r[0], total_called: num(r[1]) })),
      fund_rankings: rank.map((r) => ({ fund: r[0], total_called: num(r[1]), calls: num(r[2]), avg_call: num(r[3]) })),
      eval: fallback.eval, // accuracy is computed offline by the eval stage, not a live table
      anomalies: anom.map((r) => ({ file: r[0], doc_type: r[1], check: r[2], severity: r[3], detail: r[4] })),
    };
    res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=900");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.status(200).json(data);
  } catch (e) {
    // Never break the page — serve the baked snapshot if the live query fails.
    res.setHeader("Cache-Control", "s-maxage=30");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.status(200).json(Object.assign({}, fallback, { live: false, fallback_reason: String(e).slice(0, 160) }));
  }
};
