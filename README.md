# Enterprise AI Adoption Dashboard

A self-hostable dashboard that tracks AI tool usage across your enterprise:
**Microsoft Copilot, GitHub Copilot, Amazon Q Developer, Claude Code,
Kiro IDE** — and any other tool you write a 50-line adapter for.

- 📊 Tokens, users, cost — daily and monthly
- 🏢 Roll up by **Line of Business → Team → User**, or filter to a single tool
- 👤 **Me view** — read your *own* local AI usage from session logs
- 🔌 Pluggable adapters for any vendor API
- 📥 CSV / PDF export
- 🐍 Single-file Flask backend, single-file HTML frontend, zero build step

> Works out of the box with realistic mock data. Swap in real vendor
> credentials when you're ready.

## Quick start

```bash
git clone https://github.com/skondappa/enterprise-ai-adoption-usage-dashboard.git
cd enterprise-ai-adoption-usage-dashboard
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>. You'll see the demo with mock data.

## Connect to your real data

```bash
cp .env.example .env
# Edit .env — set ENABLED_ADAPTERS and the credentials for each tool
python app.py
```

Per-tool setup guides:

- [Microsoft Copilot](docs/data-sources/microsoft-copilot.md) — Microsoft Graph reports API
- [GitHub Copilot](docs/data-sources/github-copilot.md) — Copilot Business reports API
- [Amazon Q Developer](docs/data-sources/amazon-q.md) — CloudWatch metrics
- [Claude Code](docs/data-sources/claude-code.md) — Anthropic Admin API

## Add your own tool

Three steps — see [`docs/data-sources/README.md`](docs/data-sources/README.md):

1. `adapters/your_tool.py` inheriting from `Adapter`
2. Register in `adapters/__init__.py`
3. `docs/data-sources/your-tool.md` documenting auth + endpoints

The dashboard auto-discovers it. **No UI changes.**

## Two views in one dashboard

**Enterprise view** (default) — aggregate usage across all teams and LOBs.
Use the header filters:

- **LOB filter** — narrow to a single line of business
- **Tool filter** — narrow to a single tool (e.g. "show me only Claude Code")
- **Daily / Monthly toggle** — last 1 day vs. last 30 days
- **Click any team** in *Top 5* or the heatmap → modal shows the team's top users

**Me view** — click the **Me** button in the header. Shows *your own* AI tool
usage on this machine, parsed from local logs. Today's tokens, 30-day total,
active days, daily sparkline, per-tool breakdown, top projects.

Currently reads:

| Source         | Path                                              | Status                  |
|----------------|---------------------------------------------------|-------------------------|
| Claude Code    | `~/.claude/projects/<project>/<session>.jsonl`    | ✅ Live                 |
| GitHub Copilot | VS Code extension log directory                   | Stub (see local_tracker)|
| Cursor         | `~/.cursor/usage/`                                | Stub                    |

Add a new local source: drop a function into `LOCAL_SOURCES` in
`local_tracker.py`. Contract documented at the top of the file.

## Project layout

```
.
├── app.py                          # Flask entry point
├── store.py                        # in-memory aggregator (enterprise view)
├── local_tracker.py                # personal usage from local logs (Me view)
├── adapters/                       # one file per AI tool
│   ├── base.py                     # abstract Adapter, UsageRecord schema
│   ├── microsoft_copilot.py
│   ├── github_copilot.py
│   ├── amazon_q.py
│   ├── claude_code.py
│   └── mock.py                     # demo data — used when no creds
├── static/
│   └── dashboard.html              # the entire UI
├── docs/
│   ├── data-sources/               # per-vendor integration guides
│   └── ...
├── scripts/
│   └── ingest.py                   # one-shot pull, useful for cron
├── tests/                          # pytest tests for adapters
├── .claude/
│   └── skills/
│       └── add-data-source/        # Claude Code skill for adding tools
├── ARCHITECTURE.md                 # mermaid diagrams
└── requirements.txt
```

## Endpoints

| Endpoint                          | What it returns                                |
|-----------------------------------|------------------------------------------------|
| `GET /`                           | Dashboard HTML                                 |
| `GET /api/meta`                   | Tools + LOBs                                   |
| `GET /api/teams?lob=<lob>`        | Team-level rollups for last 30 days            |
| `GET /api/team/<id>/users`        | Per-user breakdown for a team                  |
| `GET /api/me?days=30`             | Personal usage from local AI tool logs         |
| `GET /api/export.csv`             | Team breakdown as CSV                          |
| `GET /api/health`                 | Per-adapter healthcheck                        |
| `POST /api/refresh`               | Re-pull from all enabled adapters              |

## Production hardening

Before exposing this beyond a demo:

- Add SSO (OIDC / SAML) — Flask-OIDC or Authlib
- Move `Store` from in-memory to Postgres + Redis (5-min cache)
- Run ingestion on a schedule (Airflow, cron, EventBridge) instead of
  inside the request lifecycle
- Stand up behind a load balancer (`gunicorn -w 4 app:app` + nginx)
- Wire `/api/health` into your uptime monitor

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full target topology.

## License

MIT — © 2026 Samyuktha KS. Use it, fork it, embed it.
Vendor API access remains subject to each vendor's terms.

## Author

Built and maintained by **Samyuktha KS**.

If you're rolling this out at your enterprise and want help with
deployment, custom adapters, or production hardening — reach out.

- 📩 Email: s.kondappa31@gmail.com
- 💼 LinkedIn: https://www.linkedin.com/in/samyukta-ks-7118b634/
- 📩 Medium: https://medium.com/@s.kondappa31
- ➕ Follow for more enterprise-scale AI engineering work
