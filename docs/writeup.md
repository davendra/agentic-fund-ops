# Agentic Fund-Ops Data Pipeline — project notes

## Why I built this

I wanted a compact, end-to-end demonstration of **agentic data engineering on Databricks** that plays to where I'm strongest: fund-administration operations and AI systems that have to be *trusted*, not just demoed.

For six years I led AI & Automation at Alter Domus (a global fund administrator, ~$2.5tn AUM), where I built production agentic systems — multi-agent trade-settlement automation, an enterprise GenAI platform (605 → 4,000+ users), and intelligent document processing across regulated financial documents. The recurring lesson there: **an LLM that extracts data is only useful if something deterministic checks it.** That pattern — model for judgment, code for arithmetic, humans at the material gates — is the backbone of this project.

The fund documents here come from my own [FundAdmin AI](https://github.com/davendra) work, so I could process realistic capital calls and distribution notices without touching any client or confidential material. Everything is synthetic.

## What it demonstrates

- **Native Databricks AI Functions, set-based.** One SQL query parses every PDF (`ai_parse_document`); another extracts typed fields across all documents (`ai_query` with structured output). No per-document Python loop — the warehouse parallelises it.
- **An eval harness, not a vibe.** I extract two ways — a cheap `ai_extract` baseline and a structured `ai_query` strategy — and score *both* against a hand-verified gold set of 19 documents, logged to MLflow. The structured strategy wins **96.7% vs 81.1%**, and the harness is *why* I know that rather than guessing.
- **Deterministic validation as the trust gate.** Arithmetic reconciliation (line items foot to the call total, waterfall tiers foot to proceeds, dates ordered) surfaced 13 genuine anomalies — including documents I'd deliberately seeded with errors.
- **Governed + queryable.** Unity Catalog tables, a Genie Space that answers questions in plain English by generating SQL, and the whole pipeline packaged as a Databricks Asset Bundle that deploys and runs as a serverless Job.

## How it was built

The pipeline was authored and run by an agent — Claude Code driving the workspace through Databricks' official agent-skills and CLI — against a live Unity Catalog workspace. That's the "agentic" part in the literal sense: I described the data-engineering work and the agent built, ran, validated, and measured it.

## Honest scope

This is a hands-on demonstration project, built to show the approach on a real workspace — not a production deployment, and not a claim of years of Databricks tenure. Databricks is the newest tool in my kit; the data-engineering judgment, the eval discipline, and the fund-operations domain knowledge are not. The point of the demo is that those transfer directly.

— Davendra Patel
