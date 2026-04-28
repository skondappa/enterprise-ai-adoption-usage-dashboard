"""
Microsoft Copilot adapter.

Pulls usage from the Microsoft Graph reports API. See:
    docs/data-sources/microsoft-copilot.md

Required env vars:
    MS_TENANT_ID       - Azure AD tenant id
    MS_CLIENT_ID       - app registration client id
    MS_CLIENT_SECRET   - app registration secret
    MS_GRAPH_SCOPE     - default: https://graph.microsoft.com/.default

Required Graph API permissions:
    Reports.Read.All       (delegated or application)
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from .base import Adapter, AdapterMeta, UsageRecord


class MicrosoftCopilotAdapter(Adapter):
    meta = AdapterMeta(
        id="ms-copilot",
        name="Microsoft Copilot",
        vendor="Microsoft",
        color="#06b6d4",
        cost_per_1k_tokens=0.018,
    )

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        """
        Production implementation outline:

            import requests, msal

            app = msal.ConfidentialClientApplication(
                os.environ["MS_CLIENT_ID"],
                authority=f"https://login.microsoftonline.com/{os.environ['MS_TENANT_ID']}",
                client_credential=os.environ["MS_CLIENT_SECRET"],
            )
            token = app.acquire_token_for_client(
                scopes=[os.getenv("MS_GRAPH_SCOPE",
                                  "https://graph.microsoft.com/.default")]
            )["access_token"]

            # Daily Copilot usage (per user, per day)
            url = ("https://graph.microsoft.com/v1.0/reports/"
                   "getMicrosoft365CopilotUsageUserDetail(period='D30')")
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            rows = r.json().get("value", [])

            # Enrich with team / LOB from your HRIS or Azure AD groups
            records = []
            for row in rows:
                email = row["userPrincipalName"]
                team, lob = directory.lookup(email)        # see store.py
                records.append(UsageRecord(
                    day=date.fromisoformat(row["reportDate"]),
                    tool_id=self.meta.id,
                    tool_name=self.meta.name,
                    user_email=email,
                    team=team, lob=lob,
                    tokens=row.get("totalTokensConsumed", 0),
                    sessions=row.get("copilotChatCount", 0),
                ))
            return records

        Until credentials are wired up, this returns an empty list — the
        mock adapter covers the demo scenario.
        """
        if not all(os.getenv(k) for k in ("MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET")):
            return []

        # TODO: implement live fetch (see docstring). For now, no-op when
        # credentials exist but the implementation has not been wired up yet.
        return []

    def healthcheck(self) -> tuple[bool, str]:
        if not os.getenv("MS_TENANT_ID"):
            return False, "MS_TENANT_ID not set"
        return True, "credentials present"
