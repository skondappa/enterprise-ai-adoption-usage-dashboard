# Claude Code (Anthropic)

Pulls per-user / per-day token usage from the Anthropic Admin API.

## What you get

| Field             | Source                                                    |
|-------------------|-----------------------------------------------------------|
| input_tokens      | `usage_report/messages` results (grouped by user/day)     |
| output_tokens     | same                                                      |
| cache_read_tokens | same — can dramatically lower effective cost              |
| user_email        | `user_email` (only present if your team uses workspaces)  |
| model             | `claude-opus-4-7` / `claude-sonnet-4-6` / etc             |

## Step 1 — Generate an Admin API key

1. https://console.anthropic.com/settings/admin-keys → **Create admin key**.
   - Admin keys are *separate* from per-user API keys.
   - Only org admins / billing owners can create them.
2. Copy the key — starts with `sk-ant-admin01-...`.
3. Find your **Organization ID** at
   https://console.anthropic.com/settings/organization. Starts with `org_`.

## Step 2 — Configure the dashboard

Add to `.env`:

```bash
ENABLED_ADAPTERS=claude-code
ANTHROPIC_ADMIN_KEY=sk-ant-admin01-...
ANTHROPIC_ORG_ID=org_...
```

Install:

```bash
pip install requests
```

## Step 3 — Endpoint

```
GET https://api.anthropic.com/v1/organizations/{org_id}/usage_report/messages
    ?starting_at=2026-04-01
    &ending_at=2026-04-27
    &bucket_width=1d
    &group_by=user_id
```

Headers:
```
x-api-key: <ANTHROPIC_ADMIN_KEY>
anthropic-version: 2023-06-01
```

Returns daily buckets like:
```json
{
  "data": [
    {
      "bucket_start": "2026-04-26T00:00:00Z",
      "results": [
        { "user_email": "alice@acme.com", "input_tokens": 14200,
          "output_tokens": 3700, "model": "claude-opus-4-7" },
        ...
      ]
    }
  ]
}
```

## Mapping users to teams

Anthropic returns `user_email` directly when users are managed through
**Workspaces**. Pipe it through your HRIS lookup the same way as the
Microsoft Copilot adapter — see
[microsoft-copilot.md](microsoft-copilot.md) for the pattern.

If you use the API directly (not Workspaces), `user_email` will be
absent — group by `api_key_id` instead and maintain a manual mapping.

## Cost calculation

The Admin API returns *tokens*, not dollars. The adapter applies
`cost_per_1k_tokens` from `AdapterMeta` (default `0.025`). Update that
to match your contracted rate, or compute per-model:

| Model           | Input $/1M | Output $/1M |
|-----------------|------------|-------------|
| Opus 4.7        | 15         | 75          |
| Sonnet 4.6      | 3          | 15          |
| Haiku 4.5       | 0.80       | 4           |

For accurate cost, edit `adapters/claude_code.py` to compute per-row:

```python
RATES = {
    "claude-opus-4-7":   (15.0, 75.0),
    "claude-sonnet-4-6": (3.0,  15.0),
    "claude-haiku-4-5":  (0.80, 4.0),
}
in_rate, out_rate = RATES.get(row["model"], (0, 0))
cost = (input_tokens / 1e6) * in_rate + (output_tokens / 1e6) * out_rate
```

## Rate limits

- Admin API: 50 req / min per org. Plenty for daily aggregation.
- Use `bucket_width=1d` (not `1h`) — the dashboard never needs hourly
  granularity and hourly multiplies the response payload by 24×.
