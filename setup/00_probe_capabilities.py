#!/usr/bin/env python
"""Stage 0 — probe Databricks Free Edition for the capabilities this demo needs.

Decides the downstream path:
  - AI Functions (ai_extract / ai_query / ai_parse_document) available?  -> native parse/extract
  - else -> Claude-driven fallback (anthropic + pypdf already installed)
  - Genie available? -> ship a live Genie Space, else example SQL only

Writes reports/capability-probe.json and prints a summary. Read-only against the
workspace except that it starts the serverless warehouse (auto-stops in 10 min).
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
WAREHOUSE_ID = os.environ.get("FUNDOPS_WAREHOUSE_ID", "e35b4a902313dacd")
REPORT = Path(__file__).resolve().parents[1] / "reports" / "capability-probe.json"

w = WorkspaceClient(profile=PROFILE)


def run_sql(stmt: str, timeout_s: int = 120) -> dict:
    """Execute a SQL statement, polling until it finishes. Returns a result dict."""
    resp = w.statement_execution.execute_statement(
        statement=stmt, warehouse_id=WAREHOUSE_ID, wait_timeout="30s"
    )
    deadline = time.time() + timeout_s
    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        if time.time() > deadline:
            return {"ok": False, "error": "timeout waiting for statement"}
        time.sleep(3)
        resp = w.statement_execution.get_statement(resp.statement_id)

    state = resp.status.state if resp.status else None
    if state == StatementState.SUCCEEDED:
        data = resp.result.data_array if resp.result else None
        return {"ok": True, "data": data}
    err = resp.status.error.message if (resp.status and resp.status.error) else str(state)
    return {"ok": False, "error": err}


def probe(name: str, stmt: str) -> dict:
    print(f"  probing {name} ...", flush=True)
    r = run_sql(stmt)
    status = "available" if r["ok"] else "blocked/error"
    print(f"    -> {status}" + (f": {r.get('data')}" if r["ok"] else f": {r['error'][:160]}"))
    return {"name": name, "available": r["ok"], "detail": r.get("data") if r["ok"] else r["error"]}


def main() -> int:
    results: dict = {"workspace": w.config.host, "warehouse_id": WAREHOUSE_ID, "probes": {}}

    # 1. ai_extract — the core extraction primitive
    results["probes"]["ai_extract"] = probe(
        "ai_extract",
        "SELECT ai_extract("
        "'Acme Growth Partners V issued Capital Call No. 3 for USD 3,750,000 due 2025-06-15', "
        "array('fund_name','call_number','amount','due_date')) AS r",
    )

    # 2. ai_query against a Foundation Model endpoint (model name may vary by tier)
    results["probes"]["ai_query"] = probe(
        "ai_query",
        "SELECT ai_query('databricks-meta-llama-3-3-70b-instruct', 'Reply with the single word OK') AS r",
    )

    # 3. Foundation Model serving endpoints actually present
    try:
        endpoints = [e.name for e in w.serving_endpoints.list()]
        print(f"  serving endpoints: {endpoints}")
        results["serving_endpoints"] = endpoints
    except Exception as e:  # noqa: BLE001
        results["serving_endpoints"] = f"error: {e}"
        print(f"  serving endpoints: error: {e}")

    # 4. Genie availability
    try:
        spaces = list(w.genie.list_spaces().spaces or [])
        results["probes"]["genie"] = {
            "name": "genie",
            "available": True,
            "detail": [s.title for s in spaces] or "no spaces yet (API reachable)",
        }
        print(f"  genie: available ({len(spaces)} spaces)")
    except Exception as e:  # noqa: BLE001
        results["probes"]["genie"] = {"name": "genie", "available": False, "detail": str(e)}
        print(f"  genie: blocked/error: {str(e)[:160]}")

    # Decision
    ai_ok = results["probes"]["ai_extract"]["available"]
    results["path"] = "native" if ai_ok else "claude-fallback"
    results["genie_path"] = "live" if results["probes"]["genie"]["available"] else "example-sql"

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(results, indent=2, default=str))
    print("\n=== DECISION ===")
    print(f"  extraction path : {results['path']}")
    print(f"  genie path      : {results['genie_path']}")
    print(f"  report          : {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
