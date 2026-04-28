"""
Claude Code (Anthropic) adapter.

Pulls token usage from the Anthropic Admin API. See:
    docs/data-sources/claude-code.md

Required env vars:
    ANTHROPIC_ADMIN_KEY    - admin API key (different from per-user key)
    ANTHROPIC_ORG_ID       - organization id
"""
from __future__ import annotations

import os
from datetime import date

from .base import Adapter, AdapterMeta, UsageRecord


class ClaudeCodeAdapter(Adapter):
    meta = AdapterMeta(
        id="claude-code",
        name="Claude Code",
        vendor="Anthropic",
        color="#8b5cf6",
        cost_per_1k_tokens=0.025,
    )

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        """
        Production implementation outline:

            import requests
            url = f"https://api.anthropic.com/v1/organizations/{os.environ['ANTHROPIC_ORG_ID']}/usage_report/messages"
            r = requests.get(url, params={
                "starting_at": start.isoformat(),
                "ending_at": end.isoformat(),
                "bucket_width": "1d",
                "group_by": "user_id",
            }, headers={
                "x-api-key": os.environ["ANTHROPIC_ADMIN_KEY"],
                "anthropic-version": "2023-06-01",
            })
            r.raise_for_status()

            records = []
            for bucket in r.json().get("data", []):
                day = date.fromisoformat(bucket["bucket_start"][:10])
                for row in bucket["results"]:
                    email = row.get("user_email", "unknown")
                    team, lob = directory.lookup(email)
                    records.append(UsageRecord(
                        day=day,
                        tool_id=self.meta.id,
                        tool_name=self.meta.name,
                        user_email=email,
                        team=team, lob=lob,
                        tokens=row.get("input_tokens", 0) + row.get("output_tokens", 0),
                    ))
            return records
        """
        if not os.getenv("ANTHROPIC_ADMIN_KEY"):
            return []
        return []

    def healthcheck(self) -> tuple[bool, str]:
        if not os.getenv("ANTHROPIC_ADMIN_KEY"):
            return False, "ANTHROPIC_ADMIN_KEY not set"
        return True, "credentials present"
