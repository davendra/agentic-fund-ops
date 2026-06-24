#!/usr/bin/env bash
# Rotate the Databricks PAT that the live Vercel site (api/data.js) uses.
# Run LOCALLY, where the Databricks CLI and Vercel CLI are authenticated and the
# Vercel project is linked (site/.vercel). Creates a fresh 90-day token, updates
# the encrypted DATABRICKS_TOKEN env var on Vercel, and redeploys. No secret is
# printed or committed.
set -euo pipefail
cd "$(dirname "$0")"
PROFILE="${DATABRICKS_CONFIG_PROFILE:-DEFAULT}"

TMP="$(mktemp)"
databricks tokens create --comment "agentic-fund-ops site (rotated)" \
  --lifetime-seconds 7776000 -p "$PROFILE" -o json > "$TMP"
TOK="$(python3 -c "import json;print(json.load(open('$TMP'))['token_value'],end='')")"
rm -f "$TMP"

vercel env rm DATABRICKS_TOKEN production -y >/dev/null 2>&1 || true
printf '%s' "$TOK" | vercel env add DATABRICKS_TOKEN production
unset TOK

vercel deploy --prod --yes >/dev/null
echo "✓ PAT rotated, Vercel env updated, site redeployed."
echo "  (Revoke the previous token in Databricks → Settings → Developer → Access tokens if you like.)"
