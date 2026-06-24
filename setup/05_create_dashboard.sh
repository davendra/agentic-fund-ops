#!/usr/bin/env bash
# Create (and publish) the AI/BI dashboard from dashboards/fund_ops.lvdash.json.
# Dataset queries use bare table names; catalog/schema are injected via the flags below.
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${DATABRICKS_CONFIG_PROFILE:-DEFAULT}"
WAREHOUSE_ID="${FUNDOPS_WAREHOUSE_ID:-e35b4a902313dacd}"
USER_EMAIL="$(databricks current-user me -p "$PROFILE" -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["userName"])')"

DASH_ID=$(databricks lakeview create \
  --display-name "Agentic Fund-Ops Overview" \
  --warehouse-id "$WAREHOUSE_ID" \
  --dataset-catalog fund_ops --dataset-schema silver \
  --serialized-dashboard "$(cat dashboards/fund_ops.lvdash.json)" \
  --json "{\"parent_path\": \"/Users/$USER_EMAIL\"}" \
  -p "$PROFILE" -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["dashboard_id"])')

echo "created dashboard $DASH_ID"
databricks lakeview publish "$DASH_ID" --warehouse-id "$WAREHOUSE_ID" -p "$PROFILE" >/dev/null
echo "published. Open it from the Dashboards section of your workspace."
