#!/usr/bin/env python
"""Stage 3 - extract structured fields, two native strategies, routed by doc type.

  Primary  (Strategy B): ai_query -> Foundation Model, structured JSON output.
  Baseline (Strategy A): ai_extract(label array).
Plus ai_classify routing validation. All SQL is built by pipeline_sql (shared
with the DAB). Set-based: one query per strategy per doc type.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402
import pipeline_sql as ps  # noqa: E402


def null_rates(tbl: str, gold: list[str]) -> None:
    sel = ", ".join(
        f"cast(round(100.0*sum(CASE WHEN `{f}` IS NULL OR trim(cast(`{f}` AS string))='' "
        f"THEN 1 ELSE 0 END)/count(*),1) AS double) AS {f}" for f in gold
    )
    row = fo.run_sql(f"SELECT count(*) AS n, {sel} FROM {tbl}")[0]
    print(f"    rows: {row[0]} | % NULL per gold field: "
          + ", ".join(f"{f}={v}%" for f, v in zip(gold, row[1:])))


def main() -> int:
    ns = fo.load_namespace()
    cc, di = ps.load_schema("capital_call"), ps.load_schema("distribution")
    ca = ps.load_schema("capital_account")
    print(f"extracting (primary model = {fo.EXTRACT_MODEL}):")
    for doc_type, schema, table in [("capital_call", cc, "capital_calls"),
                                    ("distribution", di, "distributions"),
                                    ("capital_account", ca, "capital_accounts")]:
        print(f"  [primary ai_query] {doc_type} -> {table} ...", flush=True)
        fo.run_sql(ps.extract_primary_sql(ns, doc_type, schema, table), timeout_s=900)
        null_rates(fo.fq(ns, "silver_schema", table), schema["gold_fields"])

    print("baseline extraction (ai_extract):")
    for doc_type, schema, table in [("capital_call", cc, "capital_calls"),
                                    ("distribution", di, "distributions")]:
        print(f"  [baseline ai_extract] {doc_type} -> {table}_baseline ...", flush=True)
        fo.run_sql(ps.extract_baseline_sql(ns, doc_type, schema, table), timeout_s=600)

    print("  [ai_classify] routing validation ...", flush=True)
    fo.run_sql(ps.classify_sql(ns), timeout_s=600)
    tbl = fo.fq(ns, "silver_schema", "doc_classification")
    a = fo.run_sql(
        f"SELECT count(*) n, sum(CASE WHEN filename_type=predicted_type THEN 1 ELSE 0 END) agree FROM {tbl}"
    )[0]
    print(f"    ai_classify vs filename routing: {a[1]}/{a[0]} agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
