#!/usr/bin/env python
"""Stage 5 - evaluate extraction accuracy against the hand-verified gold set.

Scores BOTH native strategies (ai_query structured vs ai_extract baseline) on the
gold-labelled documents, field by field, and logs metrics + a comparison artifact
to MLflow (Databricks tracking, local fallback). Only gold fields with a known
(non-null) value are scored - we never penalise a model for a field whose truth
we did not label. This is the "measure before you trust" harness.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "eval" / "gold"

FIELD_TYPE = {
    "fund_name": "name", "currency": "curr",
    "call_number": "id", "distribution_number": "id",
    "notice_date": "date", "due_date": "date", "distribution_date": "date",
    "total_called": "num", "management_fee": "num", "commitment_base": "num",
    "total_proceeds": "num", "return_of_capital": "num", "preferred_return": "num", "gp_catchup": "num",
}


def num_val(s):
    if s is None:
        return None
    t = re.sub(r"[,$€£\s]", "", str(s))
    try:
        return float(t)
    except ValueError:
        m = re.search(r"-?\d+(\.\d+)?", t)
        return float(m.group()) if m else None


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip() if s else None


def date_norm(s):
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    for fmt in ("%B %d, %Y", "%d %B %Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def match(ftype, g, p) -> bool:
    if p is None or str(p).strip() == "":
        return False
    if ftype == "name":
        G, P = norm_name(g), norm_name(p)
        return bool(G and P and (G == P or G in P or P in G))
    if ftype == "curr":
        return str(g).strip().upper() == str(p).strip().upper()
    if ftype == "date":
        return date_norm(g) == date_norm(p)
    if ftype == "num":
        gv, pv = num_val(g), num_val(p)
        if gv is None or pv is None:
            return False
        return abs(pv) <= 0.5 if gv == 0 else abs(gv - pv) <= max(1.0, abs(gv) * 0.005)
    if ftype == "id":
        gv, pv = num_val(g), num_val(p)
        if gv is not None and pv is not None:
            return gv == pv
        return str(g).strip().lower() == str(p).strip().lower()
    return str(g).strip() == str(p).strip()


def fetch(table: str, fields: list[str]) -> dict:
    cols = ", ".join(["file_name"] + [f"cast(`{f}` as string) AS `{f}`" for f in fields])
    out = {}
    for r in fo.run_sql(f"SELECT {cols} FROM {table}"):
        out[r[0]] = {f: r[i + 1] for i, f in enumerate(fields)}
    return out


def main() -> int:
    ns = fo.load_namespace()
    cc_fields = json.loads((REPO / "schemas" / "capital_call.json").read_text())["gold_fields"]
    di_fields = json.loads((REPO / "schemas" / "distribution.json").read_text())["gold_fields"]
    tables = {
        "capital_call": (fo.fq(ns, "silver_schema", "capital_calls"),
                          fo.fq(ns, "silver_schema", "capital_calls_baseline"), cc_fields),
        "distribution": (fo.fq(ns, "silver_schema", "distributions"),
                         fo.fq(ns, "silver_schema", "distributions_baseline"), di_fields),
    }
    primary, baseline = {}, {}
    for dt, (pt, bt, flds) in tables.items():
        primary[dt] = fetch(pt, flds)
        baseline[dt] = fetch(bt, flds)

    STRATS = ["ai_query", "ai_extract"]
    agg = {s: {"known": 0, "match": 0} for s in STRATS}
    by_field = {s: {} for s in STRATS}
    by_doctype = {s: {} for s in STRATS}
    detail = []

    gold_files = sorted(GOLD.glob("*.json"))
    for gfile in gold_files:
        g = json.loads(gfile.read_text())
        fn, dt, labels = g["file"], g["doc_type"], g["labels"]
        rows = {"ai_query": primary[dt].get(fn, {}), "ai_extract": baseline[dt].get(fn, {})}
        for field, gold_val in labels.items():
            if gold_val is None:
                continue
            ft = FIELD_TYPE[field]
            rec = {"file": fn, "doc_type": dt, "field": field, "gold": gold_val}
            for s in STRATS:
                pred = rows[s].get(field)
                ok = match(ft, gold_val, pred)
                agg[s]["known"] += 1
                agg[s]["match"] += int(ok)
                by_field[s].setdefault(field, [0, 0])
                by_field[s][field][0] += int(ok)
                by_field[s][field][1] += 1
                by_doctype[s].setdefault(dt, [0, 0])
                by_doctype[s][dt][0] += int(ok)
                by_doctype[s][dt][1] += 1
                rec[f"{s}_pred"] = pred
                rec[f"{s}_ok"] = ok
            detail.append(rec)

    def acc(d):
        return round(100.0 * d["match"] / d["known"], 1) if d["known"] else 0.0

    results = {
        "gold_docs": len(gold_files),
        "scored_field_instances": agg["ai_query"]["known"],
        "accuracy_pct": {s: acc(agg[s]) for s in STRATS},
        "by_doctype_pct": {s: {dt: round(100.0 * v[0] / v[1], 1) for dt, v in by_doctype[s].items()} for s in STRATS},
        "by_field_pct": {s: {f: round(100.0 * v[0] / v[1], 1) for f, v in by_field[s].items()} for s in STRATS},
    }
    (REPO / "reports" / "eval-results.json").write_text(json.dumps(results, indent=2))
    (REPO / "reports" / "eval-detail.json").write_text(json.dumps(detail, indent=2))

    print("\n=== EXTRACTION ACCURACY vs GOLD ===")
    print(f"  gold docs: {results['gold_docs']}  | scored field-instances: {results['scored_field_instances']}")
    print(f"\n  {'strategy':12}{'overall':>9}{'capital_call':>14}{'distribution':>14}")
    for s in STRATS:
        bd = results["by_doctype_pct"][s]
        print(f"  {s:12}{results['accuracy_pct'][s]:>8}%{bd.get('capital_call',0):>13}%{bd.get('distribution',0):>13}%")
    print(f"\n  {'field':22}{'ai_query':>10}{'ai_extract':>12}")
    for f in [*cc_fields, *[x for x in di_fields if x not in cc_fields]]:
        a = results["by_field_pct"]["ai_query"].get(f)
        b = results["by_field_pct"]["ai_extract"].get(f)
        if a is None and b is None:
            continue
        print(f"  {f:22}{(str(a)+'%') if a is not None else '-':>10}{(str(b)+'%') if b is not None else '-':>12}")

    log_to_mlflow(results, detail)
    return 0


def log_to_mlflow(results: dict, detail: list) -> None:
    try:
        import mlflow
    except Exception as e:  # noqa: BLE001
        print(f"\n  (mlflow not available: {e}; metrics saved to reports/ only)")
        return
    where = None
    try:
        user = fo.client().current_user.me().user_name
        mlflow.set_tracking_uri("databricks")
        mlflow.set_experiment(f"/Users/{user}/agentic-fund-ops-eval")
        where = f"databricks /Users/{user}/agentic-fund-ops-eval"
    except Exception as e:  # noqa: BLE001
        print(f"  (databricks mlflow unavailable: {str(e)[:80]}; using local ./mlruns)")
        mlflow.set_tracking_uri(f"file:{REPO}/mlruns")
        mlflow.set_experiment("agentic-fund-ops-eval")
        where = f"local {REPO}/mlruns"
    try:
        with mlflow.start_run(run_name="extraction-accuracy") as run:
            for s, a in results["accuracy_pct"].items():
                mlflow.log_metric(f"accuracy_{s}", a)
            for s in results["by_field_pct"]:
                for f, a in results["by_field_pct"][s].items():
                    mlflow.log_metric(f"{s}/{f}", a)
            mlflow.log_dict(results, "eval-results.json")
            mlflow.log_dict({"detail": detail}, "eval-detail.json")
            mlflow.set_tag("gold_docs", results["gold_docs"])
            print(f"\n  MLflow run logged -> {where}  (run_id={run.info.run_id})")
    except Exception as e:  # noqa: BLE001
        print(f"\n  (mlflow logging failed: {str(e)[:120]}; metrics saved to reports/)")


if __name__ == "__main__":
    sys.exit(main())
