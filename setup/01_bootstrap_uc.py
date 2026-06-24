#!/usr/bin/env python
"""Stage 1 setup — create the Unity Catalog namespace for the pipeline.

Tries a dedicated `fund_ops` catalog first; if catalog creation is not permitted
on this tier (Free Edition often restricts new managed catalogs), falls back to
the always-writable `workspace` catalog with fund_ops_* schemas. Persists whatever
resolved to reports/resolved-config.json so every downstream stage agrees.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402


def main() -> int:
    # Try dedicated catalog
    ns = None
    ok, err = fo.try_sql("CREATE CATALOG IF NOT EXISTS fund_ops COMMENT 'Agentic Fund-Ops demo'")
    if ok:
        # confirm we can actually create a schema in it (storage/location may still block)
        ok2, err2 = fo.try_sql("CREATE SCHEMA IF NOT EXISTS fund_ops.raw")
        if ok2:
            ns = {"catalog": "fund_ops", "raw_schema": "raw", "silver_schema": "silver"}
            print("namespace: dedicated catalog `fund_ops`")
        else:
            print(f"catalog ok but schema blocked ({err2[:120]}); falling back to `workspace`")
    else:
        print(f"catalog creation blocked ({err[:120]}); using `workspace` catalog")

    if ns is None:
        ns = {"catalog": "workspace", "raw_schema": "fund_ops_raw", "silver_schema": "fund_ops_silver"}

    ns["volume"] = "landing"
    ns["warehouse_id"] = fo.WAREHOUSE_ID

    cat, raw, silver = ns["catalog"], ns["raw_schema"], ns["silver_schema"]
    for stmt in [
        f"CREATE SCHEMA IF NOT EXISTS `{cat}`.`{raw}` COMMENT 'Raw landed fund documents'",
        f"CREATE SCHEMA IF NOT EXISTS `{cat}`.`{silver}` COMMENT 'Extracted + validated fund data'",
        f"CREATE VOLUME IF NOT EXISTS `{cat}`.`{raw}`.`{ns['volume']}` COMMENT 'Landing zone for raw PDFs'",
    ]:
        fo.run_sql(stmt)
        print(f"  ok: {stmt.split('IF NOT EXISTS')[1].strip().split(chr(39))[0].strip()}")

    fo.save_namespace(ns)
    print("\nresolved namespace:")
    print(f"  catalog        : {cat}")
    print(f"  raw schema     : {cat}.{raw}  (volume: {fo.volume_path(ns)})")
    print(f"  silver schema  : {cat}.{silver}")
    print(f"  saved -> {fo.CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
