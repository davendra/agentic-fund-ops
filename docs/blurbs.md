# Agentic Fund-Ops — Reusable Copy

> All copy below uses only the project's verified facts. The data is 100% synthetic, and this is a hands-on demonstration project built on Databricks Free Edition — not a production deployment. Confident, but honest.

---

## 1. One-line description

Trustworthy fund-document automation on Databricks: an agentic pipeline that parses, extracts, classifies, and deterministically validates capital-call and distribution notices into governed Delta tables.

---

## 2. One-paragraph summary

Agentic Fund-Ops is a hands-on demonstration of trustworthy fund-document automation built on Databricks Free Edition. It processes 66 fund PDFs — 34 capital calls and 32 distribution notices — across 7 fund families and 3 currencies (USD, EUR, GBP), drawn from a 1,145-file synthetic corpus. The pipeline chains `ai_parse_document` → `ai_query` structured extraction → `ai_classify` routing (66/66) → deterministic SQL validation → Unity Catalog Delta tables, then exposes the results through Genie natural-language-to-SQL, an AI/BI dashboard, and MLflow evaluation. Scored against 19 hand-verified gold documents, `ai_query` extraction reached 96.7% accuracy versus an 81.1% `ai_extract` baseline, and the deterministic validation layer flagged 13 anomalies. The whole project is packaged as a Databricks Asset Bundle, deployed and run as a serverless Job (succeeded), authored and run by Claude Code plus Databricks' official agent-skills. Repo: github.com/davendra/agentic-fund-ops (MIT licensed). The data is entirely synthetic and the build runs on Free Edition — this is a demonstration, not a production system.

---

## 3. LinkedIn-style post (job-seeker)

I built Agentic Fund-Ops — a trustworthy fund-document automation pipeline on Databricks (Free Edition, fully synthetic data, hands-on demo).

It runs 66 fund PDFs (34 capital calls + 32 distribution notices, 7 fund families, 3 currencies) through an agentic chain: `ai_parse_document` → `ai_query` extraction → `ai_classify` routing (66/66) → deterministic SQL validation → Unity Catalog Delta tables.

The point was trust, not just extraction. Against 19 hand-verified gold docs, `ai_query` hit 96.7% accuracy vs an 81.1% `ai_extract` baseline — and a deterministic validation layer caught 13 anomalies the model didn't.

I packaged it as a Databricks Asset Bundle and ran it as a serverless Job (succeeded), with Genie, an AI/BI dashboard, and MLflow eval on top.

Authored and run with Claude Code + Databricks' official agent-skills. Databricks is my newest tool, and this was a great way to learn it properly.

Code is open source (MIT): github.com/davendra/agentic-fund-ops

---

## 4. Recruiter email snippet (3 sentences)

I recently built Agentic Fund-Ops, a hands-on demonstration project on Databricks (Free Edition, synthetic data) that automates fund-document processing for 66 capital-call and distribution notices through an agentic pipeline of `ai_parse_document`, `ai_query` extraction, `ai_classify` routing, and deterministic SQL validation into governed Unity Catalog Delta tables. Measured against 19 hand-verified gold documents, the `ai_query` approach reached 96.7% extraction accuracy versus an 81.1% baseline, and a deterministic validation layer independently flagged 13 anomalies — the project is packaged as a Databricks Asset Bundle and ran successfully as a serverless Job. It's open source under MIT at github.com/davendra/agentic-fund-ops, and it reflects how I pair AI-driven extraction with deterministic controls to build automation people can actually trust.
