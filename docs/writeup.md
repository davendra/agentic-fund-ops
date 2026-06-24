# Agentic Fund-Ops Data Pipeline — project notes

## Why I built this

I wanted a compact, end-to-end demonstration of **agentic data engineering on Databricks** that plays to where I'm strongest: fund-administration operations and AI systems that have to be *trusted*, not just demoed.

For six years I led AI & Automation at Alter Domus (a global fund administrator, ~$2.5tn AUM), where I built production agentic systems — multi-agent trade-settlement automation, an enterprise GenAI platform (605 → 4,000+ users), and intelligent document processing across regulated financial documents. The recurring lesson there: **an LLM that extracts data is only useful if something deterministic checks it.** That pattern — model for judgment, code for arithmetic, humans at the material gates — is the backbone of this project.

The fund documents here come from my own FundAdmin AI work, so I could process realistic capital calls, distribution notices, and LP capital-account statements without touching any client or confidential material. Everything is synthetic.

## What it demonstrates

- **Native Databricks AI Functions, set-based.** One SQL query parses every PDF (`ai_parse_document`); another extracts typed fields across all 91 documents — three document types (capital calls, distribution notices, and LP capital-account statements) — using `ai_query` with structured output. `ai_classify` routes each document to its type, agreeing with the ground-truth label on 90 of 91. No per-document Python loop — the warehouse parallelises it.
- **An eval harness, not a vibe.** I extract two ways — a cheap `ai_extract` baseline and a structured `ai_query` strategy — and score *both* against a hand-verified gold set of 19 capital-call and distribution documents, logged to MLflow. The structured strategy wins **96.7% vs 81.1%**, and the harness is *why* I know that rather than guessing. (Capital accounts are extracted and validated end-to-end but aren't in the accuracy gold set yet.)
- **Deterministic validation as the trust gate.** Arithmetic reconciliation (line items foot to the call total, waterfall tiers foot to proceeds, capital accounts roll forward from opening to closing, dates ordered) surfaced 33 genuine anomalies — including documents I'd deliberately seeded with errors. The largest cluster: **20 of the 25 LP capital-account statements don't reconcile** — the stated closing balance exceeds opening plus disclosed period activity by ~1.6–2.9%. Extraction matched the source documents exactly, so this is a property of the statements themselves, not a parsing error — and the roll-forward check catches every one, which is precisely the kind of break a fund administrator has to catch before it reaches an investor.
- **Governed + queryable.** Unity Catalog silver tables — including `fund_ops.silver.capital_accounts`, which tracks ≈$2.11B of LP NAV across the statements — a Genie Space that answers questions in plain English by generating SQL, and the whole pipeline packaged as a Databricks Asset Bundle that deploys and runs as a serverless Job.

## How it was built

The pipeline was authored and run by an agent — Claude Code driving the workspace through Databricks' official agent-skills and CLI — against a live Unity Catalog workspace. That's the "agentic" part in the literal sense: I described the data-engineering work and the agent built, ran, validated, and measured it.

## Honest scope

This is a hands-on demonstration project, built to show the approach on a real workspace — not a production deployment, and not a claim of years of Databricks tenure. Databricks is the newest tool in my kit; the data-engineering judgment, the eval discipline, and the fund-operations domain knowledge are not. The point of the demo is that those transfer directly.

— Davendra Patel
