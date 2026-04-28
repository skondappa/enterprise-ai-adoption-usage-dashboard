# GitHub Copilot

Pulls usage from the GitHub Copilot Business / Enterprise reports API.

## What you get

GitHub Copilot exposes **aggregate, daily** usage — not per-user tokens.
You get:

| Field                     | Meaning                                              |
|---------------------------|------------------------------------------------------|
| `total_active_users`      | Distinct users with ≥1 suggestion in the day         |
| `total_engaged_users`     | Users who accepted ≥1 suggestion                     |
| `total_suggestions_count` | All suggestions shown                                |
| `total_acceptances_count` | Suggestions accepted                                 |
| `breakdown[].editor`      | VS Code, JetBrains, Neovim, ...                      |
| `breakdown[].language`    | Per-language counts                                  |

> GitHub does **not** publish tokens directly. The adapter approximates
> tokens as `suggestions_count × 50` (an industry-average suggestion
> length). Adjust the multiplier in `adapters/github_copilot.py` if you
> have better data.

## Step 1 — Get a token

Two options. Pick one.

### Option A: Personal Access Token (fast)

1. https://github.com/settings/tokens → **Generate new token (classic)**.
2. Scope: **`manage_billing:copilot`** (and `read:org` if you go org-level).
3. Copy the token.

### Option B: GitHub App (recommended for production)

1. https://github.com/organizations/&lt;org&gt;/settings/apps → **New GitHub App**.
2. Permissions:
   - **Organization → Administration: Read-only**
   - **Organization → Copilot Business: Read-only**
3. Install on your enterprise / org.
4. Generate a JWT and exchange for an installation token (see
   https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app).

## Step 2 — Configure the dashboard

Add to `.env`:

```bash
ENABLED_ADAPTERS=gh-copilot
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Pick exactly one of these:
GITHUB_ENTERPRISE=acme-corp        # for enterprise-wide
# GITHUB_ORG=acme-engineering      # for a single org
```

Install:

```bash
pip install requests
```

## Step 3 — Endpoints used

| Scope        | URL                                                                      |
|--------------|--------------------------------------------------------------------------|
| Enterprise   | `GET https://api.github.com/enterprises/{enterprise}/copilot/usage`      |
| Organization | `GET https://api.github.com/orgs/{org}/copilot/usage`                    |
| Per-team     | `GET https://api.github.com/orgs/{org}/team/{team_slug}/copilot/usage`   |

The adapter uses the enterprise endpoint by default. If you prefer team
attribution, switch to per-team and iterate over teams from
`GET /orgs/{org}/teams`.

## Mapping to teams

Two common patterns:

1. **GitHub teams = your teams**: use `/orgs/{org}/teams` and call the
   per-team usage endpoint for each.
2. **Email match**: get seat assignments via
   `GET /enterprises/{e}/copilot/billing/seats` (returns `assignee.login`
   and `assignee.email`), then join to your HRIS.

Edit `adapters/github_copilot.py` to use whichever you prefer.

## Rate limits

- Authenticated: 5,000 requests / hour.
- Copilot endpoints support `since` / `until` query params — pull 28 days
  in one request, not 28 daily requests.
