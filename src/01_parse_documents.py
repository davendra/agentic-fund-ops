#!/usr/bin/env python
"""Stage 2 - parse every landed PDF with Databricks `ai_parse_document`.

Set-based: one warehouse query parses all documents in the landing Volume into
<silver>.parsed_docs. SQL is built by pipeline_sql.parse_sql (shared with the DAB).
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402
import pipeline_sql as ps  # noqa: E402


def main() -> int:
    ns = fo.load_namespace()
    parsed = fo.fq(ns, "silver_schema", "parsed_docs")
    print(f"parsing all PDFs in {fo.volume_path(ns)} -> {parsed} (ai_parse_document, server-side)...")
    fo.run_sql(ps.parse_sql(ns), timeout_s=600)

    rows = fo.run_sql(
        f"""SELECT doc_type, count(*) AS n,
                   sum(CASE WHEN text IS NULL OR length(text) < 50 THEN 1 ELSE 0 END) AS short_or_empty,
                   sum(CASE WHEN parse_error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
                   cast(avg(length(text)) AS int) AS avg_chars
            FROM {parsed} GROUP BY doc_type ORDER BY doc_type"""
    )
    print(f"\n  {'doc_type':16}{'n':>4}{'short':>7}{'errors':>8}{'avg_chars':>11}")
    total = 0
    for r in rows:
        total += int(r[1])
        print(f"  {r[0]:16}{r[1]:>4}{r[2]:>7}{r[3]:>8}{r[4]:>11}")
    print(f"  total parsed: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
