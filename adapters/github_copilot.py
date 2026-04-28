"""
GitHub Copilot adapter.

Pulls usage from the GitHub Copilot Business / Enterprise reports API.
See: docs/data-sources/github-copilot.md

Required env vars:
    GITHUB_TOKEN       - personal access token or GitHub App token with
                         the `manage_billing:copilot` scope
    GITHUB_ENTERPRISE  - enterprise slug (or set GITHUB_ORG for org-level)
    GITHUB_ORG         - org slug (mutually exclusive with GITHUB_ENTERPRISE)
"""
from __future__ import annotations

import os
from datetime import date

from .base import Adapter, AdapterMeta, UsageRecord


class GithubCopilotAdapter(Adapter):
    meta = AdapterMeta(
        id="gh-copilot",
        name="GitHub Copilot",
        vendor="GitHub",
        color="#10b981",
        cost_per_1k_tokens=0.012,
    )

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        """
        Production implementation outline:

            import requests
            token = os.environ["GITHUB_TOKEN"]
            ent   = os.getenv("GITHUB_ENTERPRISE")
            org   = os.getenv("GITHUB_ORG")
            scope = f"enterprises/{ent}" if ent else f"orgs/{org}"
            url   = f"https://api.github.com/{scope}/copilot/usage"
            r = requests.get(url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
            r.raise_for_status()

            # Returns a list of daily aggregates per editor / language.
            # Note: GitHub does NOT expose per-user tokens — you must
            # treat `total_suggestions_count` as the proxy metric or use
            # the seat assignments endpoint to attribute usage to teams.
            records = []
            for day_row in r.json():
                day = date.fromisoformat(day_row["day"])
                # Roll up by team via seat -> user -> team mapping
                for breakdown in day_row.get("breakdown", []):
                    records.append(UsageRecord(
                        day=day,
                        tool_id=self.meta.id,
                        tool_name=self.meta.name,
                        user_email="aggregate@github",  # GH is org-level only
                        team=breakdown.get("editor", "unknown"),
                        lob="Engineering",
                        tokens=breakdown["suggestions_count"] * 50,  # ~50 tok/suggestion
                        sessions=breakdown["active_users"],
                        suggestions_accepted=breakdown["acceptances_count"],
                    ))
            return records
        """
        if not os.getenv("GITHUB_TOKEN"):
            return []
        return []

    def healthcheck(self) -> tuple[bool, str]:
        if not os.getenv("GITHUB_TOKEN"):
            return False, "GITHUB_TOKEN not set"
        if not (os.getenv("GITHUB_ENTERPRISE") or os.getenv("GITHUB_ORG")):
            return False, "GITHUB_ENTERPRISE or GITHUB_ORG required"
        return True, "credentials present"
