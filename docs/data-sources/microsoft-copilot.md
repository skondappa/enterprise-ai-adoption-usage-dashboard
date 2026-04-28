# Microsoft Copilot

Pulls Microsoft 365 Copilot usage via the Microsoft Graph reports API.

## What you get

| Field          | Source                                              |
|----------------|-----------------------------------------------------|
| user_email     | `userPrincipalName`                                 |
| tokens         | `totalTokensConsumed` (where exposed)               |
| sessions       | `copilotChatCount` + `copilotMeetingsCount`         |
| day            | `reportDate`                                        |

Microsoft also exposes per-app breakdowns (Word, Excel, Teams, Outlook,
PowerPoint) — the adapter rolls these up by default. Edit
`adapters/microsoft_copilot.py` if you want per-app charts.

## Step 1 — Register an Azure AD app

1. Go to **Azure Portal → Azure Active Directory → App registrations → New registration**.
2. Name: `enterprise-ai-adoption-dashboard`. Account type: *single tenant*.
3. After it's created, copy the **Application (client) ID** and **Directory (tenant) ID**.

## Step 2 — Grant Graph permissions

Under your new app:

1. **API permissions → Add a permission → Microsoft Graph → Application permissions**.
2. Select **`Reports.Read.All`**.
3. Click **Grant admin consent for &lt;tenant&gt;**. (Requires Global Admin.)

> Microsoft 365 admin centers may anonymize user names by default. If you need
> real emails in the dashboard, an admin must turn this off:
> **Microsoft 365 admin center → Settings → Org settings → Reports → Display
> concealed user, group, and site names → Off**.

## Step 3 — Create a client secret

1. **Certificates & secrets → New client secret**.
2. Copy the **value** (you won't see it again).

## Step 4 — Configure the dashboard

Add to `.env`:

```bash
ENABLED_ADAPTERS=ms-copilot
MS_TENANT_ID=<directory-tenant-id>
MS_CLIENT_ID=<application-client-id>
MS_CLIENT_SECRET=<the-secret-value>
```

Install the runtime libs:

```bash
pip install msal requests
```

Restart `python app.py`. Hit `/api/health` — you should see:

```json
{"adapters": [{"id": "ms-copilot", "ok": true, "message": "credentials present"}]}
```

## Step 5 — Wire up the live fetch

Open `adapters/microsoft_copilot.py` and replace the `return []` near the
bottom of `fetch_usage` with the implementation outlined in the docstring.
The full code is intentionally not bundled because Microsoft updates the
report endpoints occasionally — always check the latest at:

- https://learn.microsoft.com/en-us/graph/api/reportroot-getmicrosoft365copilotusageuserdetail
- https://learn.microsoft.com/en-us/graph/api/resources/microsoft365copilotusageuserdetail

## Mapping users to teams

Microsoft Graph returns `userPrincipalName` (an email). To roll up to teams
and LOBs, you need a **directory** mapping. Two common approaches:

1. **Azure AD groups** — read group memberships:
   ```python
   GET /v1.0/users/{upn}/memberOf?$select=displayName
   ```
   Treat each AAD group as a "team". Map groups to LOBs in your config.

2. **HRIS export** — pull a CSV from Workday / SuccessFactors with
   `(email, team, lob, manager)` and join in `store.py`.

Either way, build a `directory.lookup(email) -> (team, lob)` helper and
call it inside the adapter. See the docstring for the exact line.

## Rate limits

- 10,000 requests / 10 min per app, 130,000 / day per tenant.
- The reports endpoint returns up to 30 days at a time.
- Cache the result for at least 1 hour — the underlying data is computed
  daily, so polling more often wastes quota.
