# Agentic Fund-Ops — Brand Guidelines

**Trustworthy fund-document automation on Databricks.**

These guidelines define the visual and verbal identity for Agentic Fund-Ops. Apply them consistently across the README, dashboards, slides, and any public-facing material.

---

## Logo

![Agentic Fund-Ops logo](../assets/logo.jpg)

The mark is a deep-navy rounded-square badge. Inside it, a coral financial document morphs into a set of ascending data bars and a small connected node-flow, capped by a validation check mark. Teal and gold accents pick out the validated and value-bearing elements.

The mark tells the brand story in one glance: a fund document (coral) becomes structured, governed data (ascending bars + node-flow), and is confirmed trustworthy (check mark).

**Usage**
- Keep clear space around the badge equal to at least the corner radius of the rounded square.
- Preserve the rounded-square container — do not crop the mark to a circle or hard rectangle.
- Do not recolour the badge, stretch it, or add drop shadows or gradients beyond those in the source asset.
- On dark surfaces, place the badge on the ink-navy field it already carries; avoid placing it on coral or gold backgrounds where the document element loses contrast.

---

## Wordmark

The wordmark is **Agentic Fund-Ops**, set in **Space Grotesk** (Medium or Semibold).

- Capitalisation: "Agentic Fund-Ops" — capital A, capital F, hyphen, capital O. Never "FundOps", "Fund Ops", or "fund-ops" in running prose (lowercase `agentic-fund-ops` is reserved for the repo/package identifier).
- Default colour is ink-navy `#0B1F33` on light backgrounds, paper `#F7F9FC` on dark backgrounds.
- The coral accent may be used on the hyphen or on "Ops" sparingly for emphasis in hero contexts — never on more than one element at a time.
- Pair the badge to the left of the wordmark, vertically centred, with clear space between them equal to the height of the capital "A".

---

## Colour palette

| Name | Hex | Usage |
|------|------|-------|
| Ink-navy | `#0B1F33` | Primary brand colour: backgrounds, headings, wordmark, logo field |
| Coral | `#FF5A3C` | Accent and energy: source documents, calls-to-action, single-point emphasis |
| Teal | `#0FB5A0` | Validated / governed states: success indicators, "passed" checks, Unity Catalog accents |
| Gold | `#E8B23A` | Fund / value: monetary highlights, fund-family markers, key metrics |
| Paper | `#F7F9FC` | Background: page and panel fills, text on dark surfaces |
| Slate | `#5B6B7B` | Muted text: secondary copy, captions, table rules, disabled states |

**Application notes**
- Ink-navy and paper carry the layout; coral, teal, and gold are accents — use them deliberately, not decoratively.
- Teal signals *governed/validated*, gold signals *fund/value*. Keep those meanings consistent so colour reinforces the message.
- Coral is the highest-energy colour: reserve it for one focal point per view.

---

## Typography

| Role | Typeface | Notes |
|------|----------|-------|
| Headings | **Space Grotesk** | Wordmark, section titles, display metrics. Medium/Semibold. |
| Body | **Inter** | Running text, UI labels, tables. Regular/Medium. |
| Code | **JetBrains Mono** | Code samples, table/column names, CLI commands, SQL. |

- Maintain a clear hierarchy: Space Grotesk for anything that should read as a headline, Inter for everything someone reads in full sentences.
- Set body copy in slate `#5B6B7B` or ink-navy `#0B1F33` depending on weight needed; avoid pure black.
- Use JetBrains Mono for identifiers like `ai_query`, `ai_classify`, and Delta table names so technical terms stay unambiguous.

---

## Voice & tone

- **Precise.** Cite the real numbers and name the real tools — 91 PDFs, `ai_query` extraction at 96.7%, Unity Catalog Delta tables. No vague superlatives.
- **Confident, not boastful.** State what the pipeline does and what it measured; let the evidence carry the weight.
- **Honest.** The corpus is 100% synthetic and this is a hands-on demonstration on Databricks Free Edition, not a production deployment. Never imply production use or years of Databricks tenure — Databricks is the author's newest tool.
- **Technical but clear.** Write for an engineer and a fund-ops reader at once: explain the mechanism, then say plainly why it matters.

---

## Asset inventory

| File | Purpose |
|------|---------|
| `assets/logo.jpg` | Primary brand mark — navy badge with morphing document, data bars, node-flow, and validation check. |
| `assets/hero.jpg` | Hero banner image for the README and landing/title surfaces. |
| `assets/infographic-pipeline.jpg` | Pipeline diagram: `ai_parse_document` → `ai_query` → `ai_classify` → SQL validation → Unity Catalog → Genie + AI/BI + MLflow. |
| `assets/infographic-eval.jpg` | Extraction-accuracy comparison: `ai_query` 96.7% vs `ai_extract` baseline 81.1% over 19 gold documents. |
| `assets/infographic-validation.jpg` | Deterministic validation results, including the 33 anomalies flagged. |
| `assets/infographic-stats.jpg` | Corpus stats: 91 fund PDFs (34 capital-call notices + 32 distribution notices + 25 LP capital-account statements), 7 fund families, 3 currencies. |

---

*Agentic Fund-Ops · MIT licensed · [github.com/davendra/agentic-fund-ops](https://github.com/davendra/agentic-fund-ops). Authored and run by Claude Code + Databricks official agent-skills. All data is synthetic; built on Databricks Free Edition as a hands-on demonstration.*
