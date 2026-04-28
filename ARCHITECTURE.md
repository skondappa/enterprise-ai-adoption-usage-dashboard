# Enterprise AI Adoption Dashboard — Architecture

> **Two ways to read this doc**
> - **Just want to understand it?** Read sections 1 and 2 — plain English with diagrams.
> - **Need to build, deploy, or extend it?** Sections 3+ have the engineering detail.

Diagrams use [Mermaid](https://mermaid.js.org/). They render natively on
GitHub, in VS Code with the *Markdown Preview Mermaid Support* extension,
or by pasting any block into <https://mermaid.live>.

---

## 1. What this thing does — the 60-second version

Your company is paying for several AI tools — Microsoft Copilot, GitHub
Copilot, Claude Code, Amazon Q, Kiro, others. Every team uses something
different, the bills add up, and nobody has a single answer to:

- **Who actually uses what?**
- **What is each tool costing us?**
- **Is anyone getting real value, or are licenses sitting idle?**

This dashboard collects usage from every tool, puts it in one place, and
draws the picture.

```mermaid
flowchart LR
    subgraph A["1 — Where the numbers come from"]
        direction TB
        T1["fa:fa-microsoft  Microsoft Copilot"]
        T2["fa:fa-github  GitHub Copilot"]
        T3["fa:fa-aws  Amazon Q"]
        T4["fa:fa-comments  Claude Code"]
        T5["fa:fa-cube  Kiro IDE"]
    end

    subgraph B["2 — What this app does with them"]
        direction TB
        COLLECT["fa:fa-cloud-download-alt  Pull yesterday's usage<br/><i>once a day, automatically</i>"]
        TIDY["fa:fa-broom  Translate every vendor's<br/>numbers into one common shape"]
        SAVE[("fa:fa-database  Store it<br/><i>so the dashboard loads fast</i>")]
        COLLECT --> TIDY --> SAVE
    end

    subgraph C["3 — Who looks at the dashboard"]
        direction TB
        EXEC["fa:fa-chart-line  Executives & LOB heads<br/><i>spend, adoption, trends</i>"]
        MGR["fa:fa-users  Engineering managers<br/><i>per-team usage</i>"]
        FIN["fa:fa-dollar-sign  Finance<br/><i>cost reporting</i>"]
        ME["fa:fa-user  Each developer<br/><i>their own usage in 'Me' view</i>"]
    end

    A ==> B ==> C

    classDef src   fill:#0f172a,stroke:#06b6d4,color:#e5e7eb,stroke-width:2px
    classDef etl   fill:#0f172a,stroke:#f59e0b,color:#e5e7eb,stroke-width:2px
    classDef user  fill:#0f172a,stroke:#10b981,color:#e5e7eb,stroke-width:2px
    class T1,T2,T3,T4,T5 src
    class COLLECT,TIDY,SAVE etl
    class EXEC,MGR,FIN,ME user
```

**A real-world analogy.** Think of it like a Fitbit dashboard — but for
your team's AI use. Each AI tool is a different sensor on a different
wrist; this app puts every reading on the same chart, in the same units,
so you can compare apples to apples.

---

## 2. How it actually works (still plain English)

Three small things happen, on three different schedules:

```mermaid
flowchart TB
    subgraph NIGHT["At night — 'collect'"]
        direction TB
        S1["fa:fa-cloud  Visit each AI vendor's API"]
        S2["fa:fa-file-import  Download yesterday's usage rows"]
        S3[("fa:fa-database  Save them to our database")]
        S1 --> S2 --> S3
    end

    subgraph DAY["During the day — 'show'"]
        direction TB
        S4["fa:fa-mouse-pointer  Someone opens the dashboard"]
        S5["fa:fa-server  Server reads from <b>our</b> database<br/><i>(never touches the vendors live)</i>"]
        S6["fa:fa-chart-bar  Browser draws charts"]
        S4 --> S5 --> S6
    end

    subgraph ME["Anytime — 'Me view'"]
        direction TB
        S7["fa:fa-user  A developer clicks <b>Me</b>"]
        S8["fa:fa-folder-open  Server reads tool logs<br/>from <i>their own</i> machine"]
        S9["fa:fa-chart-pie  Shows just their usage"]
        S7 --> S8 --> S9
    end

    classDef night fill:#0f172a,stroke:#6366f1,color:#e5e7eb,stroke-width:2px
    classDef day   fill:#0f172a,stroke:#ec4899,color:#e5e7eb,stroke-width:2px
    classDef me    fill:#0f172a,stroke:#10b981,color:#e5e7eb,stroke-width:2px
    class S1,S2,S3 night
    class S4,S5,S6 day
    class S7,S8,S9 me
```

**Why split it into three?** Calling vendor APIs is slow (sometimes
minutes). A dashboard has to feel instant. So the slow work runs once
at night, and the browser only ever talks to our own fast database
during the day. The "Me" view is separate because it reads from your
own laptop — there's no enterprise system that knows what you ran in
your terminal at 11pm.

---

## 3. System overview — for engineers

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
        DS["adapters/*<br/><i>one per vendor</i>"]
        STOREPY["store.py<br/><i>aggregator</i>"]
        API["app.py<br/><i>REST API</i>"]
        AUTH["Auth Middleware<br/><i>SSO / OIDC</i>"]
    end

    subgraph FRONT["Frontend — Browser"]
        UI["dashboard.html<br/>+ Chart.js"]
        EXP["html2canvas + jsPDF<br/><i>CSV / PDF export</i>"]
    end

    MS  --> SCHED
    AWS --> SCHED
    KIRO --> SCHED
    GH  --> SCHED
    ANT --> SCHED

    SCHED --> NORM --> STORE
    STORE --> CACHE
    CACHE --> DS
    DS --> STOREPY --> API
    AUTH --> API
    API --> UI
    UI --> EXP

    classDef src   fill:#0f172a,stroke:#06b6d4,color:#e5e7eb
    classDef etl   fill:#0f172a,stroke:#f59e0b,color:#e5e7eb
    classDef back  fill:#0f172a,stroke:#6366f1,color:#e5e7eb
    classDef front fill:#0f172a,stroke:#ec4899,color:#e5e7eb
    class MS,AWS,KIRO,GH,ANT src
    class SCHED,NORM,STORE,CACHE etl
    class DS,STOREPY,API,AUTH back
    class UI,EXP front
```

---

## 4. Request flow — loading the dashboard

```mermaid
sequenceDiagram
    autonumber
    actor User as Browser
    participant UI as dashboard.html
    participant API as Flask /api
    participant Auth as SSO Middleware
    participant DS as adapters / store.py
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
    DS-->>API: JSON
    API-->>UI: 200 [...teams]
    UI->>UI: aggregate + render charts
    UI-->>User: rendered dashboard
```

---

## 5. ETL — daily ingestion job

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

## 6. Canonical data model

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

## 7. Component responsibilities

| Layer | Component | Responsibility |
|---|---|---|
| Sources | Vendor APIs | Authoritative usage telemetry per tool |
| ETL | Scheduler | Triggers daily ingestion (Airflow DAG / Lambda + EventBridge / cron) |
| ETL | Normalizer | Maps vendor schemas to canonical `usage_daily` shape |
| Storage | Warehouse | Long-term storage; powers historical queries (Postgres or BigQuery) |
| Storage | Cache | 5-minute TTL Redis layer in front of warehouse — keeps API <100ms |
| Backend | `adapters/*` | One file per vendor; the only place that talks to vendor APIs |
| Backend | `store.py` | Aggregates adapter output into the canonical shape |
| Backend | `app.py` | Stateless Flask app; thin REST layer over `store.py` |
| Backend | `local_tracker.py` | Reads tool logs from the user's own machine (Me view) |
| Backend | Auth | SSO/OIDC middleware (e.g., Authlib, Flask-OIDC) — required for prod |
| Frontend | `dashboard.html` | Renders KPIs, charts, drill-downs from JSON; no business logic |
| Frontend | jsPDF / html2canvas | Client-side export — keeps server stateless |

---

## 8. Where to plug in your real telemetry

Each adapter in `adapters/` is the seam where mock data becomes real
data. To wire a vendor in:

1. Open `adapters/{tool}.py`.
2. Replace the mock `fetch()` with real API calls (SDK or `requests`).
3. Make sure each row you return matches the `UsageRecord` shape in
   `adapters/base.py`.
4. Set the credentials referenced in `.env.example` for that tool.

Keep the JSON shapes documented in `app.py` route docstrings stable —
the front-end only knows about those, so swapping the backing storage
requires zero UI changes.

---

## 9. Scaling & deployment notes

```mermaid
flowchart LR
    USERS["fa:fa-users  Browsers"] --> CDN["fa:fa-globe  CDN<br/><i>static assets</i>"]
    CDN --> LB["fa:fa-network-wired  Load Balancer<br/>(ALB / nginx)"]
    LB --> APP1["Flask app #1"]
    LB --> APP2["Flask app #2"]
    LB --> APP3["Flask app #3"]
    APP1 --> CACHE[("fa:fa-bolt  Redis<br/><i>5-min cache</i>")]
    APP2 --> CACHE
    APP3 --> CACHE
    CACHE -. on miss .-> DB[("fa:fa-database  Warehouse")]

    classDef box fill:#0f172a,stroke:#6366f1,color:#e5e7eb,stroke-width:2px
    class USERS,CDN,LB,APP1,APP2,APP3,CACHE,DB box
```

- **Stateless Flask** — scale horizontally; pin sessions to Redis if SSO is sticky.
- **CDN for `dashboard.html` + Chart.js / jsPDF** — they're already CDN-loaded, so the only origin asset is the HTML itself.
- **ETL is async** — dashboard never blocks on ingestion; users always see last-cached snapshot.
- **Cost guardrails** — alert if `kpiCost` projection exceeds budget; surface in dashboard as a banner.
