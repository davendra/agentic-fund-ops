#!/usr/bin/env bash
# One-command end-to-end run of the Agentic Fund-Ops pipeline against your
# Databricks workspace. Requires: Databricks CLI authed (profile in
# DATABRICKS_CONFIG_PROFILE, default DEFAULT) and a serverless SQL warehouse.
set -euo pipefail
cd "$(dirname "$0")"
PY=".venv/bin/python"
export DATABRICKS_CONFIG_PROFILE="${DATABRICKS_CONFIG_PROFILE:-DEFAULT}"

[ -x "$PY" ] || { echo "Create the venv first: uv venv --python 3.12 .venv && uv pip install --python $PY databricks-sdk mlflow pypdf"; exit 1; }

echo "==> Stage 0  probe capabilities";        $PY setup/00_probe_capabilities.py
echo "==> Stage 1a bootstrap Unity Catalog";    $PY setup/01_bootstrap_uc.py
echo "==> Stage 1b ingest corpus -> Volume";    $PY src/00_ingest_corpus.py
echo "==> Stage 2  parse (ai_parse_document)";  $PY src/01_parse_documents.py
echo "==> Stage 3  extract (ai_query/ai_extract)"; $PY src/02_extract_fields.py
echo "==> Stage 4  validate (deterministic)";   $PY src/03_validate.py
echo "==> Stage 5  evaluate vs gold (MLflow)";  $PY src/04_evaluate.py
echo ""
echo "Done. Optional next steps:"
echo "  $PY setup/03_genie_demo.py                 # natural-language Q&A over the silver tables"
echo "  $PY setup/gen_dab.py                       # regenerate the bundle SQL"
echo "  databricks bundle validate -p DEFAULT      # validate the deployable Job"
echo "  databricks bundle deploy -t dev -p DEFAULT # deploy it to the workspace"
