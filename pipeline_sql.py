"""Single source of truth for the pipeline's SQL.

Both the interactive runner scripts (src/0*.py) and the Databricks Asset Bundle
generator (setup/gen_dab.py) build their SQL from these functions, so the
deployable Job and the local run execute byte-identical transformations.
"""
from __future__ import annotations
import json
from pathlib import Path

import fundops_lib as fo

REPO = Path(__file__).resolve().parent
LABELS = {"capital_call": "capital call notice", "distribution": "distribution notice"}


def load_schema(name: str) -> dict:
    return json.loads((REPO / "schemas" / f"{name}.json").read_text())


# ---- parse ----
def parse_sql(ns: dict) -> str:
    parsed = fo.fq(ns, "silver_schema", "parsed_docs")
    vol = fo.volume_path(ns)
    return f"""CREATE OR REPLACE TABLE {parsed} AS
WITH raw AS (
  SELECT _metadata.file_name AS file_name, ai_parse_document(content) AS parsed
  FROM read_files('{vol}/', format => 'binaryFile')
)
SELECT
  file_name,
  CASE WHEN lower(file_name) rlike 'capital[-_ ]?call' THEN 'capital_call'
       ELSE 'distribution' END AS doc_type,
  concat_ws('\\n', transform(cast(parsed:document:elements AS ARRAY<VARIANT>),
                             e -> e:content::string)) AS text,
  try_cast(parsed:error_status AS string) AS parse_error
FROM raw"""


# ---- extract ----
def _ddl(schema: dict) -> str:
    parts = []
    for f in schema["fields"]:
        t = "INT" if f == "num_limited_partners" else ("DOUBLE" if f in schema["numeric_fields"] else "STRING")
        parts.append(f"{f}:{t}")
    return "STRUCT<" + ",".join(parts) + ">"


def _prompt(schema: dict, label: str) -> str:
    lines = [f"- {f}: {schema['descriptions'].get(f, f)}" for f in schema["fields"]]
    return (
        f"You are a fund-administration data extraction engine. From the {label} below, "
        "return ONLY a JSON object with exactly these keys:\n"
        + "\n".join(lines)
        + "\nRules: monetary amounts as plain numbers (no currency symbols, no thousands "
        "separators); dates as ISO YYYY-MM-DD; use null for any field not present. "
        "Return only the JSON object.\n\nDocument:\n"
    )


def extract_primary_sql(ns: dict, doc_type: str, schema: dict, table: str) -> str:
    parsed = fo.fq(ns, "silver_schema", "parsed_docs")
    tbl = fo.fq(ns, "silver_schema", table)
    prompt = _prompt(schema, LABELS[doc_type]).replace("'", "''")
    return f"""CREATE OR REPLACE TABLE {tbl} AS
SELECT file_name, doc_type, ex.*, raw_json AS extracted_json
FROM (
  SELECT file_name, doc_type, from_json(resp.result, '{_ddl(schema)}') AS ex, resp.result AS raw_json
  FROM (
    SELECT file_name, doc_type,
      ai_query('{fo.EXTRACT_MODEL}', CONCAT('{prompt}', text),
               responseFormat => '{{"type":"json_object"}}', failOnError => false,
               modelParameters => named_struct('temperature', CAST(0.0 AS DOUBLE))) AS resp
    FROM {parsed} WHERE doc_type = '{doc_type}'
  )
)"""


def extract_baseline_sql(ns: dict, doc_type: str, schema: dict, table: str) -> str:
    parsed = fo.fq(ns, "silver_schema", "parsed_docs")
    tbl = fo.fq(ns, "silver_schema", table + "_baseline")
    arr = "array(" + ",".join("'" + f + "'" for f in schema["fields"]) + ")"
    return f"""CREATE OR REPLACE TABLE {tbl} AS
SELECT file_name, doc_type, ex.*, to_json(ex) AS extracted_json
FROM (SELECT file_name, doc_type, ai_extract(text, {arr}) AS ex
      FROM {parsed} WHERE doc_type = '{doc_type}')"""


def classify_sql(ns: dict) -> str:
    parsed = fo.fq(ns, "silver_schema", "parsed_docs")
    tbl = fo.fq(ns, "silver_schema", "doc_classification")
    return f"""CREATE OR REPLACE TABLE {tbl} AS
SELECT file_name, doc_type AS filename_type,
       ai_classify(text, array('capital_call','distribution','capital_account',
                               'subscription','lpa','other')) AS predicted_type
FROM {parsed}"""


# ---- validate ----
CAPITAL_CALL_CHECKS = [
    ("total_called_positive", "error", "total_called IS NOT NULL", "total_called > 0",
     "concat('total_called=', total_called)"),
    ("line_items_reconcile", "warning",
     "investment_amount IS NOT NULL AND management_fee IS NOT NULL AND fund_expenses IS NOT NULL AND total_called IS NOT NULL",
     "abs((investment_amount+management_fee+fund_expenses) - total_called) <= 0.01*total_called",
     "concat('components=', round(investment_amount+management_fee+fund_expenses,0), ' vs total=', total_called)"),
    ("dates_ordered", "warning",
     "try_to_date(notice_date) IS NOT NULL AND try_to_date(due_date) IS NOT NULL",
     "try_to_date(due_date) >= try_to_date(notice_date)", "concat(notice_date, ' -> ', due_date)"),
    ("call_within_commitments", "warning",
     "total_called IS NOT NULL AND commitment_base IS NOT NULL", "total_called <= commitment_base",
     "concat('called=', total_called, ' base=', commitment_base)"),
    ("fee_rate_plausible", "info", "mgmt_fee_rate IS NOT NULL", "mgmt_fee_rate > 0 AND mgmt_fee_rate <= 5",
     "concat('rate=', mgmt_fee_rate, '%')"),
]
DISTRIBUTION_CHECKS = [
    ("total_proceeds_positive", "error", "total_proceeds IS NOT NULL", "total_proceeds > 0",
     "concat('total_proceeds=', total_proceeds)"),
    ("waterfall_reconciles", "warning",
     "return_of_capital IS NOT NULL AND preferred_return IS NOT NULL AND gp_catchup IS NOT NULL AND residual_split IS NOT NULL AND total_proceeds IS NOT NULL",
     "abs((return_of_capital+preferred_return+gp_catchup+residual_split) - total_proceeds) <= 0.01*total_proceeds",
     "concat('tiers=', round(return_of_capital+preferred_return+gp_catchup+residual_split,0), ' vs total=', total_proceeds)"),
    ("amounts_non_negative", "error", "true",
     "coalesce(return_of_capital,0) >= 0 AND coalesce(preferred_return,0) >= 0 AND coalesce(gp_catchup,0) >= 0 AND coalesce(residual_split,0) >= 0 AND coalesce(gp_carry_total,0) >= 0",
     "'tier amounts >= 0'"),
    ("carry_within_proceeds", "warning",
     "gp_carry_total IS NOT NULL AND total_proceeds IS NOT NULL", "gp_carry_total <= total_proceeds",
     "concat('carry=', gp_carry_total, ' proceeds=', total_proceeds)"),
]


def _check_select(table: str, name: str, sev: str, applicable: str, cond: str, detail: str) -> str:
    return f"""SELECT file_name, doc_type, '{name}' AS check_name, '{sev}' AS severity,
  CASE WHEN NOT ({applicable}) THEN NULL ELSE ({cond}) END AS passed,
  CASE WHEN NOT ({applicable}) THEN 'n/a' ELSE {detail} END AS detail
FROM {table}"""


def validate_sql(ns: dict) -> str:
    cc = fo.fq(ns, "silver_schema", "capital_calls")
    di = fo.fq(ns, "silver_schema", "distributions")
    out = fo.fq(ns, "silver_schema", "validation_results")
    selects = [_check_select(cc, *c) for c in CAPITAL_CALL_CHECKS]
    selects += [_check_select(di, *c) for c in DISTRIBUTION_CHECKS]
    return f"CREATE OR REPLACE TABLE {out} AS\n" + "\nUNION ALL\n".join(selects)
