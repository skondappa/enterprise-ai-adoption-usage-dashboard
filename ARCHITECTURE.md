# Enterprise AI Adoption Dashboard — Architecture

Diagrams use [Mermaid](https://mermaid.js.org/). View them by:
- Opening this file on GitHub / GitLab (renders natively)
- VS Code with the *Markdown Preview Mermaid Support* extension
- Pasting any block into <https://mermaid.live>

---

## 1. System overview

```mermaid
flowchart LR
    subgraph SRC["AI Telemetry Sources"]
        direction TB
        MS["Microsoft Graph API<br/><i>Copilot usage</i>"]
        AWS["AWS CloudWatch<br/><i>Q Developer metrics</i>"]
        KIRO["Kiro Telemetry<br/><i>IDE events</i>"]
        GH["GitHub Copilot<br/>Business API"]
        ANT["Anthropic Admin API<br/><i>Claude Code</i>"]
    end

    subgraph ETL["Ingestion & Normalization"]
        direction TB
        SCHED["Scheduler<br/>(Airflow / cron / Lambda)"]
        NORM["Normalizer<br/><i>canonical schema</i>"]
        STORE[("Warehouse<br/>Postgres / BigQuery")]
        CACHE[("Cache<br/>Redis · 5 min TTL")]
    end

    subgraph BACK["Backend — Flask"]
        DS["data_source.py<br/><i>source-of-truth adapter</i>"]
        API["app.py<br/><i>REST API</i>"]
        AUTH["Auth Middleware<br/><i>SSO / OIDC</i>"]
    end

    subgraph FRONT["Frontend — Browser"]
        UI["dashboard.html<br/>+ Chart.js"]
        EXP["html2canvas + jsPDF<br/><i>CSV / PDF export</i>"]
    end

    subgraph USERS["Consumers"]
        EXEC["Executives<br/>LOB Heads"]
        MGR["Engineering<br/>Managers"]
        FIN["Finance<br/><i>cost tracking</i>"]
    end

    MS  --> SCHED
    AWS --> SCHED
    KIRO --> SCHED
    GH  --> SCHED
    ANT --> SCHED

    SCHED --> NORM --> STORE
    STORE --> CACHE
    CACHE --> DS
    DS    --> API
    AUTH  --> API
    API   --> UI
    UI    --> EXP
    UI    --> EXEC
    UI    --> MGR
    EXP   --> FIN

    classDef src   fill:#1e293b,stroke:#06b6d4,color:#e5e7eb
    classDef etl   fill:#1e293b,stroke:#f59e0b,color:#e5e7eb
    classDef back  fill:#1e293b,stroke:#6366f1,color:#e5e7eb
    classDef front fill:#1e293b,stroke:#ec4899,color:#e5e7eb
    classDef user  fill:#1e293b,stroke:#10b981,color:#e5e7eb
    class MS,AWS,KIRO,GH,ANT src
    class SCHED,NORM,STORE,CACHE etl
    class DS,API,AUTH back
    class UI,EXP front
    class EXEC,MGR,FIN user
```

---

## 2. Request flow — loading the dashboard

```mermaid
sequenceDiagram
    autonumber
    actor User as Browser
    participant UI as dashboard.html
    participant API as Flask /api
    participant Auth as SSO Middleware
    participant DS as data_source.py
    participant Cache as Redis
    participant Store as Warehouse

    User->>UI: GET /
    UI->>API: GET /api/meta
    API->>Auth: validate session
    Auth-->>API: ok (claims)
    API->>DS: list_tools(), list_lobs()
    DS->>Cache: meta:tools, meta:lobs
    alt cache hit
        Cache-->>DS: payload
    else cache miss
        DS->>Store: SELECT tools, lobs
        Store-->>DS: rows
        DS->>Cache: SET (TTL 5m)
    end
    DS-->>API: JSON
    API-->>UI: 200 { tools, lobs }
    UI->>API: GET /api/teams?lob=all
    API->>DS: list_teams("all")
    DS->>Cache: teams:all
    Cache-->>DS: payload (or fetch from Store)
    DS-->>API: JSON
    API-->>UI: 200 [...teams]
    UI->>UI: aggregate + render charts
    UI-->>User: rendered dashboard
```

---

## 3. ETL — daily ingestion job

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Scheduler<br/>(02:00 UTC daily)
    participant Pull as Source Adapter
    participant MS as Microsoft Graph
    participant AWS as AWS Q Metrics
    participant GH as GitHub Copilot
    participant Norm as Normalizer
    participant DB as Warehouse

    Cron->>Pull: trigger ingest
    par fan-out
        Pull->>MS: GET /reports/getCopilotUsage
        MS-->>Pull: usage rows
    and
        Pull->>AWS: GetMetricData (Q.*)
        AWS-->>Pull: data points
    and
        Pull->>GH: GET /enterprises/{e}/copilot/usage
        GH-->>Pull: usage rows
    end
    Pull->>Norm: raw payloads
    Norm->>Norm: map → canonical schema<br/>(team, tool, date, tokens, users)
    Norm->>DB: UPSERT usage_daily
    DB-->>Norm: ok
    Norm-->>Cron: status: success · n rows
```

---

## 4. Canonical data model

```mermaid
erDiagram
    LOB ||--o{ TEAM : contains
    TEAM ||--o{ USER : employs
    TEAM ||--o{ USAGE_DAILY : produces
    USER ||--o{ USAGE_DAILY : generates
    TOOL ||--o{ USAGE_DAILY : measured_by

    LOB {
        string name PK
        string owner_email
    }
    TEAM {
        int id PK
        string name
        string lob FK
        string manager_email
    }
    USER {
        string email PK
        string name
        string role
        int team_id FK
    }
    TOOL {
        string id PK
        string name
        string vendor
        decimal cost_per_1k_tokens
    }
    USAGE_DAILY {
        date day PK
        string user_email FK
        string tool_id FK
        int team_id FK
        int tokens
        int sessions
        int suggestions_accepted
    }
```

---

## 5. Component responsibilities

| Layer | Component | Responsibility |
|---|---|---|
| Sources | Vendor APIs | Authoritative usage telemetry per tool |
| ETL | Scheduler | Triggers daily ingestion (Airflow DAG / Lambda + EventBridge / cron) |
| ETL | Normalizer | Maps vendor schemas to canonical `usage_daily` shape |
| Storage | Warehouse | Long-term storage; powers historical queries (Postgres or BigQuery) |
| Storage | Cache | 5-minute TTL Redis layer in front of warehouse — keeps API <100ms |
| Backend | `data_source.py` | Single abstraction over cache + warehouse; the only file that touches storage |
| Backend | `app.py` | Stateless Flask app; thin REST layer that calls `data_source` |
| Backend | Auth | SSO/OIDC middleware (e.g., Authlib, Flask-OIDC) — required for prod |
| Frontend | `dashboard.html` | Renders KPIs, charts, drill-downs from JSON; no business logic |
| Frontend | jsPDF / html2canvas | Client-side export — keeps server stateless |

---

## 6. Where to plug in your real telemetry

In `data_source.py`, replace each function below:

| Function | Today (mock) | Production (suggested) |
|---|---|---|
| `list_tools()` | hard-coded list | static config table or `tools` warehouse table |
| `list_lobs()` | hard-coded list | HRIS export (Workday / SuccessFactors) |
| `list_teams(lob)` | generated | `SELECT ... FROM usage_daily JOIN team ... GROUP BY team, tool, day` against the warehouse, with Redis caching |
| `team_users(team_id, days)` | generated | Same query, group by `user_email` instead of team |
| `export_csv_rows(...)` | iterates teams | Stream rows from a server-side cursor for large orgs |

Keep the **JSON shapes documented in `app.py` route docstrings stable** — the front-end only knows about those, so swapping the backing storage requires zero UI changes.

---

## 7. Scaling & deployment notes

```mermaid
flowchart LR
    LB["Load Balancer<br/>(ALB / nginx)"] --> APP1["Flask · app.py"]
    LB --> APP2["Flask · app.py"]
    LB --> APP3["Flask · app.py"]
    APP1 --> CACHE[("Redis")]
    APP2 --> CACHE
    APP3 --> CACHE
    CACHE -. miss .-> DB[("Warehouse")]
    CDN["CDN<br/><i>static assets</i>"] --> LB

    classDef box fill:#1e293b,stroke:#6366f1,color:#e5e7eb
    class LB,APP1,APP2,APP3,CACHE,DB,CDN box
```

- **Stateless Flask** — scale horizontally; pin sessions to Redis if SSO is sticky.
- **CDN for `dashboard.html` + Chart.js / jsPDF** — they're already CDN-loaded, so the only origin asset is the HTML itself.
- **ETL is async** — dashboard never blocks on ingestion; users always see last-cached snapshot.
- **Cost guardrails** — alert if `kpiCost` projection exceeds budget; surface in dashboard as a banner.
