"""
Mock adapter — generates realistic demo data so the dashboard works
without any real credentials. Useful for local dev, demos, and tests.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from .base import Adapter, AdapterMeta, UsageRecord


# A small multi-tool / multi-LOB sample. Edit freely.
_LOBS = {
    "Banking & Finance":   ["Mortgage", "Trading Desk", "Risk & Compliance",
                            "Core Engineering", "Wealth Management"],
    "Insurance":           ["Claims Platform", "Underwriting", "Actuarial", "Customer Portal"],
    "Healthcare":          ["EHR Engineering", "Clinical Analytics", "Patient Apps"],
    "Retail & E-commerce": ["Storefront", "Fulfillment", "Pricing & Promotions", "Loyalty"],
}

_TOOLS = [
    AdapterMeta(id="ms-copilot",  name="Microsoft Copilot",  vendor="Microsoft", color="#06b6d4", cost_per_1k_tokens=0.018),
    AdapterMeta(id="amazon-q",    name="Amazon Q Developer", vendor="AWS",       color="#f59e0b", cost_per_1k_tokens=0.014),
    AdapterMeta(id="kiro",        name="Kiro IDE",           vendor="Kiro",      color="#ec4899", cost_per_1k_tokens=0.020),
    AdapterMeta(id="claude-code", name="Claude Code",        vendor="Anthropic", color="#8b5cf6", cost_per_1k_tokens=0.025),
    AdapterMeta(id="gh-copilot",  name="GitHub Copilot",     vendor="GitHub",    color="#10b981", cost_per_1k_tokens=0.012),
]


class MockAdapter(Adapter):
    """One adapter that fakes data for *all* tools — keeps the demo simple."""

    meta = AdapterMeta(
        id="mock",
        name="Mock (all tools)",
        vendor="demo",
        color="#94a3b8",
        cost_per_1k_tokens=0.0,
    )

    @property
    def tools(self) -> list[AdapterMeta]:
        return _TOOLS

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        records: list[UsageRecord] = []
        team_id = 0
        for lob_idx, (lob, teams) in enumerate(_LOBS.items()):
            for team in teams:
                rng = random.Random(team_id * 31 + 7)
                bias = 0.2 + rng.random() * 0.8
                for tool in _TOOLS:
                    if rng.random() < 0.25 and tool.id not in ("ms-copilot", "amazon-q"):
                        continue
                    n_users = max(1, int((8 + rng.random() * 60) * (0.3 + rng.random() * 0.7)))
                    cur = start
                    d = 0
                    while cur <= end:
                        wave = 1 + 0.4 * math.sin((d + lob_idx) * 0.4)
                        trend = 1 + d * 0.012
                        tokens = int(800 + rng.random() * 6000 * bias * wave * trend)
                        records.append(UsageRecord(
                            day=cur,
                            tool_id=tool.id,
                            tool_name=tool.name,
                            user_email=f"team{team_id}@example.com",
                            team=team,
                            lob=lob,
                            tokens=tokens,
                            sessions=n_users,
                        ))
                        cur += timedelta(days=1)
                        d += 1
                team_id += 1
        return records
