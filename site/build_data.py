#!/usr/bin/env python
"""Snapshot fund_ops.silver into site/data.json for the static site.

The site is fully static (no runtime Databricks dependency), so we bake a
point-in-time snapshot of the synthetic data + the committed eval/validation
results into one JSON the page reads at load.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import fundops_lib as fo  # noqa: E402


def rows(sql):
    return fo.run_sql(sql, timeout_s=180)


def main() -> int:
    ns = fo.load_namespace()
    C = f"`{ns['catalog']}`.`{ns['silver_schema']}`"
    data = {"generated_note": "Point-in-time snapshot of synthetic fund_ops.silver data."}

    # KPIs
    k = rows(f"""SELECT
        (SELECT count(*) FROM {C}.capital_calls) calls,
        (SELECT count(*) FROM {C}.distributions) dists,
        (SELECT sum(CASE WHEN currency='USD' THEN total_called ELSE 0 END) FROM {C}.capital_calls) usd_called,
        (SELECT count(*) FROM {C}.validation_results WHERE passed=false) anomalies""")[0]
    data["kpis"] = {"capital_calls": int(k[0]), "distributions": int(k[1]),
                    "usd_called": float(k[2]), "anomalies": int(k[3]),
                    "funds": 7, "currencies": 3, "gold_docs": 19}

    data["by_currency"] = [{"currency": r[0], "total_called": float(r[1])}
                           for r in rows(f"SELECT currency, sum(total_called) FROM {C}.capital_calls WHERE currency IS NOT NULL GROUP BY currency ORDER BY 2 DESC")]

    data["docs_by_fund"] = [{"fund": r[0], "doc_type": r[1], "n": int(r[2])} for r in rows(
        f"""SELECT split(file_name,'__')[0] fund, doc_type, count(*) n FROM (
              SELECT file_name, doc_type FROM {C}.capital_calls
              UNION ALL SELECT file_name, doc_type FROM {C}.distributions) GROUP BY fund, doc_type ORDER BY fund""")]

    data["dist_by_type"] = [{"type": r[0], "n": int(r[1])} for r in rows(
        f"SELECT coalesce(distribution_type,'(unspecified)'), count(*) FROM {C}.distributions GROUP BY 1 ORDER BY 2 DESC")]

    data["trend"] = [{"yq": r[0], "total_called": float(r[1])} for r in rows(
        f"""SELECT concat(year(try_to_date(notice_date)),'-Q',quarter(try_to_date(notice_date))) yq,
                   sum(total_called) FROM {C}.capital_calls
            WHERE try_to_date(notice_date) IS NOT NULL GROUP BY 1 ORDER BY 1""")]

    data["fund_rankings"] = [{"fund": r[0], "total_called": float(r[1]), "calls": int(r[2]),
                              "avg_call": float(r[3])} for r in rows(
        f"""SELECT fund_name, sum(total_called), count(*), avg(total_called) FROM {C}.capital_calls
            WHERE fund_name IS NOT NULL GROUP BY fund_name ORDER BY 2 DESC LIMIT 10""")]

    # merge committed eval + validation artifacts
    ev = json.loads((REPO / "samples" / "eval-results.json").read_text())
    data["eval"] = {"accuracy_pct": ev["accuracy_pct"], "by_field_pct": ev["by_field_pct"],
                    "gold_docs": ev["gold_docs"], "scored": ev["scored_field_instances"]}
    vs = json.loads((REPO / "samples" / "validation-summary.json").read_text())
    data["anomalies"] = vs["flagged_anomalies"]

    out = REPO / "site" / "data.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"wrote {out}")
    print(f"  KPIs: {data['kpis']}")
    print(f"  by_currency: {data['by_currency']}")
    print(f"  trend points: {len(data['trend'])} | fund_rankings: {len(data['fund_rankings'])} | anomalies: {len(data['anomalies'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
