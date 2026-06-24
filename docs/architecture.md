# Architecture & Process Diagrams

All diagrams use [Mermaid](https://mermaid.js.org/) and render directly on GitHub.

---

## 1. End-to-end pipeline

```mermaid
flowchart TD
    PDF["66 fund PDFs<br/>capital calls + distributions<br/>7 funds · USD/EUR/GBP"]

    subgraph ingest["Ingest"]
        VOL[("Unity Catalog Volume<br/>/Volumes/fund_ops/raw/landing")]
    end

    subgraph extract["AI extraction - native AI Functions"]
        PARSE["PARSE<br/>ai_parse_document"]
        PARSED[("silver.parsed_docs")]
        EXTRACT["EXTRACT · ai_query<br/>Llama-3.3-70B, structured JSON"]
        BASELINE["ai_extract<br/>baseline"]
        CLASSIFY["CLASSIFY · ai_classify<br/>routing check 66/66"]
    end

    subgraph trust["Govern and gate"]
        SILVER[("silver.capital_calls<br/>silver.distributions")]
        VALIDATE["VALIDATE<br/>deterministic SQL reconciliation"]
        VR[("silver.validation_results<br/>13 anomalies flagged")]
    end

    subgraph serve["Serve, visualise, measure"]
        GENIE["Genie Space<br/>natural-language to SQL"]
        DASH["AI/BI Dashboard<br/>KPIs · charts · anomaly table"]
        EVAL["MLflow eval"]
        METRIC["ai_query 96.7%<br/>vs ai_extract 81.1%"]
    end

    GOLD[("eval/gold<br/>19 hand-verified docs")]
    DAB["Databricks Asset Bundle<br/>to serverless Job"]

    PDF -->|upload| VOL
    VOL --> PARSE --> PARSED
    PARSED --> EXTRACT
    PARSED -. baseline .-> BASELINE
    PARSED --> CLASSIFY
    EXTRACT --> SILVER
    SILVER --> VALIDATE --> VR
    SILVER --> GENIE
    SILVER --> DASH
    VR --> DASH
    SILVER --> EVAL
    BASELINE --> EVAL
    GOLD --> EVAL
    EVAL --> METRIC
    VALIDATE -. packaged as .-> DAB
```

---

## 2. The agentic build loop

How the pipeline was authored and run — an agent (Claude Code + Databricks' official agent-skills) drives the workspace.

```mermaid
sequenceDiagram
    actor Dev as Engineer
    participant Agent as Claude Code and skills
    participant SDK as Databricks CLI and SDK
    participant WS as Databricks workspace
    Dev->>Agent: build an agentic fund-ops pipeline
    Agent->>SDK: probe capabilities (ai_ functions, Genie)
    SDK->>WS: run test queries
    WS-->>Agent: native path available
    loop each stage: parse, extract, classify, validate
        Agent->>SDK: set-based SQL (ai_parse_document, ai_query, ai_classify)
        SDK->>WS: execute on SQL warehouse
        WS-->>Agent: governed Delta tables
    end
    Agent->>Agent: deterministic validation and MLflow eval vs gold
    Agent->>WS: deploy Asset Bundle, run Job, create Genie and dashboard
    Agent-->>Dev: tables, dashboard, 96.7% measured accuracy
```

---

## 3. Pipeline as a deployable Job (DAB task DAG)

The same SQL, packaged as a Databricks Asset Bundle and run as a serverless Job. Tasks fan out from `parse` and re-converge at `validate`.

```mermaid
flowchart LR
    parse["parse<br/>01_parse.sql"]
    ecc["extract_capital_calls<br/>02_extract_capital_calls.sql"]
    edi["extract_distributions<br/>02_extract_distributions.sql"]
    cls["classify<br/>02_classify.sql"]
    val["validate<br/>03_validate.sql"]

    parse --> ecc
    parse --> edi
    parse --> cls
    ecc --> val
    edi --> val
```

---

## 4. The evaluation harness — measure before you trust

Two native extraction strategies are scored against the same hand-verified gold set; only fields whose ground-truth was labelled are scored.

```mermaid
flowchart TD
    P[("silver.parsed_docs")]
    A["ai_query<br/>structured output"]
    B["ai_extract<br/>label-array baseline"]
    AT[("capital_calls<br/>distributions")]
    BT[("*_baseline")]
    GOLD[("eval/gold · 19 docs<br/>hand-verified, with provenance")]
    CMP{"field-by-field compare<br/>known fields only<br/>(num tolerance, ISO dates,<br/>name normalisation)"}
    M["MLflow run<br/>ai_query 96.7%<br/>ai_extract 81.1%"]

    P --> A --> AT --> CMP
    P --> B --> BT --> CMP
    GOLD --> CMP
    CMP --> M
```

---

## 5. Genie — natural language to SQL

```mermaid
sequenceDiagram
    actor U as Analyst
    participant G as Genie Space
    participant W as SQL Warehouse
    participant T as fund_ops.silver
    U->>G: Total capital called by currency?
    G->>G: generate SQL
    G->>W: SELECT currency, SUM(total_called) GROUP BY currency
    W->>T: query governed tables
    T-->>W: rows
    W-->>G: result
    G-->>U: USD 2.43B, EUR 462.5M, GBP 260M plus the generated SQL
```

---

## 6. Table lineage (Unity Catalog)

```mermaid
flowchart LR
    V[("raw.landing<br/>(Volume: 66 PDFs)")]
    PD[("silver.parsed_docs")]
    CC[("silver.capital_calls")]
    DI[("silver.distributions")]
    DC[("silver.doc_classification")]
    VR[("silver.validation_results")]
    CCB[("silver.capital_calls_baseline")]
    DIB[("silver.distributions_baseline")]

    V -->|ai_parse_document| PD
    PD -->|ai_query| CC
    PD -->|ai_query| DI
    PD -->|ai_extract| CCB
    PD -->|ai_extract| DIB
    PD -->|ai_classify| DC
    CC -->|validate| VR
    DI -->|validate| VR
```
