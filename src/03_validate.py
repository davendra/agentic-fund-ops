#!/usr/bin/env python
"""Stage 4 - deterministic validation of the extracted data.

The agent extracts; deterministic SQL *gates* it (arithmetic reconciliation, date
ordering, plausibility) - failures are unambiguous and auditable. SQL is built by
pipeline_sql.validate_sql (shared with the DAB). Writes <silver>.validation_results.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402
import pipeline_sql as ps  # noqa: E402


def main() -> int:
    ns = fo.load_namespace()
    out = fo.fq(ns, "silver_schema", "validation_results")
    print("running deterministic validation ...")
    fo.run_sql(ps.validate_sql(ns), timeout_s=300)

    rows = fo.run_sql(
        f"""SELECT doc_type, severity,
                   sum(CASE WHEN passed=true THEN 1 ELSE 0 END) AS passed,
                   sum(CASE WHEN passed=false THEN 1 ELSE 0 END) AS failed,
                   sum(CASE WHEN passed IS NULL THEN 1 ELSE 0 END) AS na
            FROM {out} GROUP BY doc_type, severity ORDER BY doc_type, severity"""
    )
    print(f"\n  {'doc_type':14}{'severity':10}{'pass':>6}{'fail':>6}{'n/a':>6}")
    for r in rows:
        print(f"  {r[0]:14}{r[1]:10}{r[2]:>6}{r[3]:>6}{r[4]:>6}")

    fails = fo.run_sql(
        f"SELECT file_name, check_name, severity, detail FROM {out} WHERE passed=false ORDER BY severity, file_name LIMIT 25"
    )
    print(f"\n  {len(fails)} failing checks (anomalies surfaced for review):")
    for r in fails:
        print(f"    [{r[2]:7}] {r[1]:24} {r[0][:42]:42} {r[3][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
