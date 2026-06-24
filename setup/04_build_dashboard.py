#!/usr/bin/env python
"""Build the AI/BI (Lakeview) dashboard JSON over the fund_ops.silver tables.

Writes dashboards/fund_ops.lvdash.json. Dataset queries use BARE table names;
the catalog/schema are supplied at create time via --dataset-catalog/--dataset-schema.
Deploy with setup/05_create_dashboard.sh (or the commands it prints).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "dashboards" / "fund_ops.lvdash.json"

USD_FMT = {"type": "number-currency", "currencyCode": "USD",
           "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}


def counter(name, ds, fname, expr, title, fmt=None):
    value = {"fieldName": fname, "displayName": title}
    if fmt:
        value["format"] = fmt
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds,
            "fields": [{"name": fname, "expression": expr}],
            "disaggregated": False}}],
        "spec": {"version": 2, "widgetType": "counter",
                 "encodings": {"value": value},
                 "frame": {"showTitle": True, "title": title}}}}


def counter_measure(name, ds, measure, title, fmt=None):
    """Counter backed by a dataset-level MEASURE column (robust for conditional sums)."""
    fld = f"measure({measure})"
    value = {"fieldName": fld, "displayName": title}
    if fmt:
        value["format"] = fmt
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds,
            "fields": [{"name": fld, "expression": f"MEASURE(`{measure}`)"}],
            "disaggregated": False}}],
        "spec": {"version": 2, "widgetType": "counter",
                 "encodings": {"value": value},
                 "frame": {"showTitle": True, "title": title}}}}


def bar(name, ds, xname, xexpr, yname, yexpr, title, color=None):
    fields = [{"name": xname, "expression": xexpr}, {"name": yname, "expression": yexpr}]
    enc = {"x": {"fieldName": xname, "scale": {"type": "categorical"}, "displayName": xname},
           "y": {"fieldName": yname, "scale": {"type": "quantitative"}, "displayName": title}}
    if color:
        cname, cexpr = color
        fields.append({"name": cname, "expression": cexpr})
        enc["color"] = {"fieldName": cname, "scale": {"type": "categorical"}, "displayName": cname}
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds, "fields": fields, "disaggregated": False}}],
        "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
                 "frame": {"showTitle": True, "title": title}}}}


def table(name, ds, cols, title):
    fields = [{"name": c[0], "expression": f"`{c[0]}`"} for c in cols]
    columns = [{"fieldName": c[0], "displayName": c[1]} for c in cols]
    return {"widget": {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": ds, "fields": fields, "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "table",
                 "encodings": {"columns": columns},
                 "frame": {"showTitle": True, "title": title}}}}


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


dashboard = {
    "datasets": [
        {"name": "ds_calls", "displayName": "Capital calls",
         "queryLines": ["SELECT file_name, fund_name, total_called, currency FROM capital_calls"],
         "columns": [{"displayName": "USD called",
                      "expression": "SUM(CASE WHEN `currency`='USD' THEN `total_called` ELSE 0 END)"}]},
        {"name": "ds_dist", "displayName": "Distributions",
         "queryLines": ["SELECT file_name, fund_name, total_proceeds, currency, "
                        "coalesce(distribution_type,'(unspecified)') AS distribution_type FROM distributions"]},
        {"name": "ds_validation", "displayName": "Validation results",
         "queryLines": ["SELECT file_name, doc_type, check_name, severity, passed, detail FROM validation_results"],
         "columns": [{"displayName": "Anomalies",
                      "expression": "SUM(CASE WHEN `passed`=false THEN 1 ELSE 0 END)"}]},
        {"name": "ds_docs", "displayName": "Documents by fund",
         "queryLines": ["SELECT split(file_name,'__')[0] AS fund, doc_type FROM capital_calls\n",
                        "UNION ALL\n",
                        "SELECT split(file_name,'__')[0] AS fund, doc_type FROM distributions"]},
        {"name": "ds_anomalies", "displayName": "Flagged anomalies",
         "queryLines": ["SELECT file_name, doc_type, check_name, severity, detail FROM validation_results\n",
                        "WHERE passed = false ORDER BY severity, file_name"]},
    ],
    "pages": [{
        "name": "overview", "displayName": "Fund-Ops Overview",
        "layout": [
            {"widget": {"name": "header", "multilineTextboxSpec": {"lines": [
                "# Agentic Fund-Ops — Document Automation Overview\n\n",
                "AI-extracted, deterministically-validated data from **66 fund-administration PDFs** ",
                "(capital calls + distribution notices, 7 funds, 3 currencies). ",
                "The model extracts; arithmetic **validation gates** it — the anomalies table (bottom-right) ",
                "is what a fund administrator would review. All data is synthetic."]}},
             "position": pos(0, 0, 12, 3)},

            {**counter("kpi_calls", "ds_calls", "calls", "COUNT(`file_name`)", "Capital calls"),
             "position": pos(0, 3, 3, 3)},
            {**counter("kpi_dists", "ds_dist", "dists", "COUNT(`file_name`)", "Distributions"),
             "position": pos(3, 3, 3, 3)},
            {**counter_measure("kpi_usd", "ds_calls", "USD called", "USD capital called", USD_FMT),
             "position": pos(6, 3, 3, 3)},
            {**counter_measure("kpi_anom", "ds_validation", "Anomalies", "Anomalies flagged"),
             "position": pos(9, 3, 3, 3)},

            {**bar("bar_ccy", "ds_calls", "currency", "`currency`", "called", "SUM(`total_called`)",
                   "Capital called by currency"),
             "position": pos(0, 6, 4, 6)},
            {**bar("bar_funds", "ds_docs", "fund", "`fund`", "docs", "COUNT(`fund`)",
                   "Documents processed by fund", color=("doc_type", "`doc_type`")),
             "position": pos(4, 6, 8, 6)},

            {**bar("bar_disttype", "ds_dist", "distribution_type", "`distribution_type`",
                   "count", "COUNT(`file_name`)", "Distributions by type"),
             "position": pos(0, 12, 4, 7)},
            {**table("tbl_anom", "ds_anomalies",
                     [("file_name", "Document"), ("doc_type", "Type"),
                      ("check_name", "Check"), ("severity", "Severity"), ("detail", "Detail")],
                     "Validation anomalies — flagged for review"),
             "position": pos(4, 12, 8, 7)},
        ],
    }],
}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2))
    print(f"wrote {OUT} ({len(dashboard['datasets'])} datasets, "
          f"{len(dashboard['pages'][0]['layout'])} widgets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
