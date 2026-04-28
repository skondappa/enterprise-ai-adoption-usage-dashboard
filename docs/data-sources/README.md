# Data Source Integrations

The dashboard pulls usage from one or more **adapters**. Each adapter
talks to a vendor's API, normalizes the result into the canonical
`UsageRecord` shape, and lets the dashboard treat all tools uniformly.

| Tool                | Adapter id    | Setup guide                              | Adapter file                          |
|---------------------|---------------|------------------------------------------|---------------------------------------|
| Microsoft Copilot   | `ms-copilot`  | [microsoft-copilot.md](microsoft-copilot.md) | `adapters/microsoft_copilot.py`   |
| GitHub Copilot      | `gh-copilot`  | [github-copilot.md](github-copilot.md)       | `adapters/github_copilot.py`      |
| Amazon Q Developer  | `amazon-q`    | [amazon-q.md](amazon-q.md)                   | `adapters/amazon_q.py`            |
| Claude Code         | `claude-code` | [claude-code.md](claude-code.md)             | `adapters/claude_code.py`         |
| Mock (demo)         | `mock`        | _no setup — generates fake data_         | `adapters/mock.py`                |

## How the dashboard picks adapters

`ENABLED_ADAPTERS` is the only knob:

```bash
# .env
ENABLED_ADAPTERS=ms-copilot,gh-copilot,claude-code
```

If the env var is empty or any listed adapter returns 0 rows, the dashboard
falls back to the **mock** adapter so you always see *something*.

## Adding a new tool

See the [`add-data-source` skill](../../.claude/skills/add-data-source/SKILL.md)
or follow these steps:

1. Create `adapters/your_tool.py` inheriting from `Adapter`.
2. Implement `fetch_usage(start, end) -> list[UsageRecord]`.
3. Register it in `adapters/__init__.py` (`REGISTRY`).
4. Add a new doc page here describing auth + endpoints.
5. Restart the server.

The dashboard UI requires zero changes — the new tool appears automatically
in all charts, the donut, the heatmap, and the team breakdown.

## The canonical schema

Every adapter must return rows shaped like:

```python
UsageRecord(
    day=date(2026, 4, 27),
    tool_id="ms-copilot",
    tool_name="Microsoft Copilot",
    user_email="alice@example.com",
    team="Mortgage",
    lob="Banking & Finance",
    tokens=12_450,
    sessions=8,
    suggestions_accepted=42,
    cost_usd=0.22,
)
```

If the vendor doesn't expose a field (e.g. GitHub doesn't give per-user
tokens, Amazon Q doesn't give per-user breakdown), use the closest proxy
and document the assumption in the adapter docstring.
