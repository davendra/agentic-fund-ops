"""Shared helpers for the Agentic Fund-Ops pipeline.

The pipeline is SQL-first: every stage issues SQL (incl. ai_parse_document /
ai_extract) to the serverless SQL warehouse via the Databricks SDK statement
execution API. No local Spark required — runs anywhere the CLI is authed.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

REPO = Path(__file__).resolve().parent
PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
# Convenience default for this demo's Free Edition serverless warehouse (not a
# secret — useless without the workspace host + auth). Override for any other
# workspace via the FUNDOPS_WAREHOUSE_ID env var; the bundle resolves by name.
WAREHOUSE_ID = os.environ.get("FUNDOPS_WAREHOUSE_ID", "e35b4a902313dacd")
CONFIG_PATH = REPO / "reports" / "resolved-config.json"

# Foundation Model endpoint used for any ai_query()-based extraction / fallback.
EXTRACT_MODEL = os.environ.get("FUNDOPS_MODEL", "databricks-meta-llama-3-3-70b-instruct")

_w: WorkspaceClient | None = None


def client() -> WorkspaceClient:
    global _w
    if _w is None:
        _w = WorkspaceClient(profile=PROFILE)
    return _w


def run_sql(stmt: str, timeout_s: int = 300) -> list[list]:
    """Execute SQL, polling to completion. Returns rows (list of lists). Raises on error."""
    w = client()
    resp = w.statement_execution.execute_statement(
        statement=stmt, warehouse_id=WAREHOUSE_ID, wait_timeout="30s"
    )
    deadline = time.time() + timeout_s
    while resp.status and resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        if time.time() > deadline:
            raise TimeoutError(f"statement timed out after {timeout_s}s")
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    state = resp.status.state if resp.status else None
    if state != StatementState.SUCCEEDED:
        msg = resp.status.error.message if (resp.status and resp.status.error) else str(state)
        raise RuntimeError(f"SQL failed: {msg}\n--- statement ---\n{stmt[:800]}")
    return (resp.result.data_array if resp.result else None) or []


def try_sql(stmt: str, timeout_s: int = 300) -> tuple[bool, str]:
    """Like run_sql but returns (ok, error_message) instead of raising."""
    try:
        run_sql(stmt, timeout_s)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def save_namespace(ns: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(ns, indent=2))


def load_namespace() -> dict:
    """Resolved catalog/schema names written by setup/01_bootstrap_uc.py."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    # sensible default before bootstrap runs
    return {
        "catalog": "workspace",
        "raw_schema": "fund_ops_raw",
        "silver_schema": "fund_ops_silver",
        "volume": "landing",
        "warehouse_id": WAREHOUSE_ID,
    }


def fq(ns: dict, schema_key: str, obj: str) -> str:
    """Fully-qualified name, e.g. fq(ns,'silver_schema','capital_calls')."""
    return f"`{ns['catalog']}`.`{ns[schema_key]}`.`{obj}`"


def volume_path(ns: dict, *parts: str) -> str:
    base = f"/Volumes/{ns['catalog']}/{ns['raw_schema']}/{ns['volume']}"
    return "/".join([base, *parts]) if parts else base
