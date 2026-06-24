# Agentic Fund-Ops Data Pipeline

**An AI agent that turns messy fund-administration PDFs into governed, validated, queryable data — built end-to-end on Databricks with native AI Functions, Unity Catalog, Genie, MLflow, and Asset Bundles.**

> Capital-call and distribution notices arrive as unstructured PDFs in a dozen different layouts. This pipeline parses them, extracts structured fields with an LLM, **gates the model's output with deterministic arithmetic**, lands governed Delta tables, exposes a natural-language query layer, and **measures its own extraction accuracy against a hand-verified gold set** — all packaged as a one-command deployable Databricks Job.

<table>
<tr>
<td><b>66</b><br>fund PDFs processed</td>
<td><b>7</b><br>fund families, 3 currencies</td>
<td><b>96.7%</b><br>field-extraction accuracy</td>
<td><b>100%</b><br>native Databricks AI</td>
</tr>
</table>

Built as a hands-on demonstration of **agentic data engineering** on Databricks. The agent (Claude Code + Databricks' official agent-skills) authored, ran, and validated this pipeline against a live Unity Catalog workspace. All data is **synthetic** (see [Data](#the-data)).

---

## Architecture

```
 66 fund PDFs (capital calls + distribution notices, 7 funds, USD/EUR/GBP)
        │
        ▼  upload → Unity Catalog Volume  /Volumes/fund_ops/raw/landing
   ┌──────────────────────────────────────────────────────────────────┐
   │ PARSE      ai_parse_document      PDF → text         (set-based)   │
   │ EXTRACT    ai_query → Llama-3.3-70B, structured JSON output        │
   │            ‖ ai_extract (baseline, for the eval comparison)        │
   │ CLASSIFY   ai_classify            routing check (66/66 agree)      │
   │ VALIDATE   deterministic SQL      arithmetic reconciliation gates  │
   └──────────────────────────────────────────────────────────────────┘
        │
        ▼  governed Delta tables in  fund_ops.silver
   ┌─────────────────────────────┬────────────────────────────────────┐
   │ GENIE  natural-language Q&A  │ MLflow GenAI eval                  │
   │ "total called by currency?"  │ ai_query 96.7% vs ai_extract 81.1% │
   │  → generated SQL → answer    │ scored vs 19 hand-verified gold docs│
   └─────────────────────────────┴────────────────────────────────────┘
        │
        ▼  packaged as a Databricks Asset Bundle → deployable serverless Job
```

| Stage | Databricks primitive | What it does |
|------|----------------------|--------------|
| Ingest | Unity Catalog **Volume** | Land raw PDFs in governed storage |
| Parse | **`ai_parse_document`** | PDF → text, set-based over the whole Volume |
| Extract | **`ai_query`** + structured output | LLM extraction into typed columns, schema-driven |
| Classify | **`ai_classify`** | Validate doc-type routing |
| Validate | **deterministic SQL** | Arithmetic reconciliation — the trust gate |
| Serve | **Genie Space** | Natural-language → SQL over the silver tables |
| Visualise | **AI/BI Dashboard** (Lakeview) | KPIs, charts + the live anomaly table over the silver tables |
| Evaluate | **MLflow** (GenAI eval) | Score extraction accuracy vs a gold set |
| Deploy | **Asset Bundle** → Job | One-command, scheduled, serverless |

---

## Headline results

### Extraction accuracy — *measure before you trust*

Two **native** strategies, scored field-by-field against 19 hand-verified gold documents (122 field instances):

| Strategy | Overall | Capital calls | Distributions |
|---|---|---|---|
| **`ai_query` (Llama-3.3-70B, structured output)** | **96.7%** | 97.0% | 96.4% |
| `ai_extract` (label-array baseline) | 81.1% | 71.2% | 92.9% |

The 15-point gap is the whole point: the cheap `ai_extract` baseline silently failed on unfamiliar templates (all-null on some funds, grabbed *"$1.81x MOIC"* as a cash amount, a per-LP list as the commitment base). The eval harness **catches that** — so you ship the strategy you measured, not the one you hoped for. Logged to an MLflow experiment in the workspace.

The remaining `ai_query` misses are genuine and honest — e.g. a notice whose waterfall literally reads *"Preferred Return (8%): SKIPPED"* (gold `0`) that the model returned as null, and a $1.8B commitment base derived from a `1.5% × $1.8B` fee line that the model under-read. (See [`samples/eval-detail.json`](samples/eval-detail.json).)

### Deterministic validation — the trust gate

Every hard check passes (34/34 capital calls, 64/64 distributions on positive-amount / non-negative rules). The **warnings are the value** — the pipeline surfaced **13 anomalies** for human review:

- 8 capital-call **line-item reconciliation** breaks (components ≠ stated total)
- 4 distribution **waterfall** mismatches (tiers ≠ total proceeds)
- 1 **implausible 8.9% management-fee rate** (model confused a loan coupon for the fee)

This is the *"extract with a model, gate with deterministic code"* pattern — the model handles judgment, arithmetic handles trust.

### Genie — ask the lakehouse in English

Real exchanges captured from the Conversation API ([`samples/genie-demo.json`](samples/genie-demo.json)):

> **"What is the total capital called across all funds, by currency?"**
> → `SELECT currency, SUM(total_called) … GROUP BY currency`
> → **$2,431,625,000 USD · €462,500,000 EUR · £260,000,000 GBP**

> **"Which documents failed a validation check?"**
> → `SELECT file_name, check_name … WHERE passed = false`
> → **13 documents** — `waterfall_reconciles`, `line_items_reconcile`, `fee_rate_plausible`

---

## The data

100% **synthetic**. The inputs are capital-call and distribution-notice PDFs drawn from the author's own FundAdmin AI product sample corpus (1,145 synthetic files across fictional funds — *Apex*, *Greenfield*, *Catalyst*, *Pacific Credit*, *Cornerstone RE*, *Meridian*, *European Growth*). **Every** capital-call + distribution PDF in the corpus (66 documents, 7 fund families, USD/EUR/GBP) is processed — not a cherry-picked sample. No client or confidential data is used anywhere.

The documents are deliberately heterogeneous: different layouts per fund, European vs American waterfalls, income vs return-of-capital distributions, recycled capital, multi-currency, and several **intentional inconsistencies** (a misclassified fee, a per-LP table that doesn't foot to the stated total) — which the validation layer is built to catch.

---

## Run it yourself

**Prerequisites:** a Databricks workspace with a serverless SQL warehouse and AI Functions enabled (Free Edition works), the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/) authenticated (`databricks auth login`), and [`uv`](https://github.com/astral-sh/uv).

```bash
# 1. environment
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python databricks-sdk mlflow pypdf

# 2. end-to-end: probe → bootstrap → ingest → parse → extract → validate → evaluate
./run.sh

# 3. natural-language layer, AI/BI dashboard, deployable Job
.venv/bin/python setup/03_genie_demo.py                       # Genie NL→SQL transcript
.venv/bin/python setup/04_build_dashboard.py && ./setup/05_create_dashboard.sh   # AI/BI dashboard
databricks bundle validate -p DEFAULT
databricks bundle deploy -t dev -p DEFAULT     # creates the serverless Job
databricks bundle run  fund_ops_pipeline -t dev -p DEFAULT
```

The pipeline auto-detects what your workspace supports (Stage 0 probe) and resolves a Unity Catalog namespace; a fresh clone runs against the committed 66-PDF dataset without needing the source corpus.

---

## Repository layout

```
fundops_lib.py            shared client + SQL execution helpers
pipeline_sql.py           single source of truth for the pipeline SQL
setup/
  00_probe_capabilities.py   what AI Functions / Genie are available
  01_bootstrap_uc.py         create catalog / schemas / volume
  03_genie_demo.py           NL → SQL transcript
  04_build_dashboard.py      build the AI/BI dashboard JSON
  05_create_dashboard.sh     create + publish the AI/BI dashboard
  gen_dab.py                 emit the bundle SQL from pipeline_sql
src/
  00_ingest_corpus.py        PDFs → Unity Catalog Volume
  01_parse_documents.py      ai_parse_document
  02_extract_fields.py       ai_query (primary) + ai_extract (baseline) + ai_classify
  03_validate.py             deterministic reconciliation
  04_evaluate.py             accuracy vs gold → MLflow
schemas/                   extraction schemas (fields, descriptions, gold fields)
eval/gold/                 19 hand-verified ground-truth labels (with provenance)
genie/genie_space.json     Genie Space definition
dashboards/                AI/BI (Lakeview) dashboard definition (.lvdash.json)
databricks.yml             Asset Bundle
resources/                 Job definition + auto-generated SQL tasks
corpus/landing/            the committed 66-PDF dataset
samples/                   captured run artifacts (accuracy, Genie transcript)
```

---

## Tech

Databricks — Unity Catalog · AI Functions (`ai_parse_document`, `ai_query`, `ai_extract`, `ai_classify`) · Foundation Model APIs · Genie · AI/BI Dashboards (Lakeview) · MLflow · Asset Bundles · serverless SQL. Python · `databricks-sdk`.

## A note on honesty

This is a learning-and-demonstration project, built hands-on to show agentic data-engineering patterns on Databricks against a real workspace — not a claim of production deployment. The value is in the *approach*: set-based AI Functions, a measured eval harness rather than a vibe, and deterministic validation gating LLM output. The data is synthetic; the engineering is real.

*License: MIT.*
