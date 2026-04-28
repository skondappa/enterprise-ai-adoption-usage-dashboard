"""
In-memory store that aggregates `UsageRecord`s from all enabled adapters
into the JSON shapes the dashboard expects.

For production, swap the in-memory dicts for a real warehouse + cache:
    - Postgres / BigQuery for durable storage
    - Redis for the per-team / per-tool aggregations (5-minute TTL)
The function signatures don't change — only the implementations do.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from adapters import enabled_adapters
from adapters.base import UsageRecord, AdapterMeta
from adapters.mock import _TOOLS, MockAdapter


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
WINDOW_DAYS = 30


class Store:
    """Holds the most recent WINDOW_DAYS of usage in memory."""

    def __init__(self):
        self.records: list[UsageRecord] = []
        self.tools: list[AdapterMeta] = []
        self.refresh()

    def refresh(self) -> None:
        end = date.today()
        start = end - timedelta(days=WINDOW_DAYS - 1)
        records: list[UsageRecord] = []
        tools: dict[str, AdapterMeta] = {}

        for adapter in enabled_adapters():
            # Mock exposes its own tool catalogue; real adapters expose one.
            if isinstance(adapter, MockAdapter):
                for t in adapter.tools:
                    tools[t.id] = t
            else:
                tools[adapter.meta.id] = adapter.meta
            try:
                records.extend(adapter.fetch_usage(start, end))
            except Exception as exc:
                print(f"[store] {adapter.id} fetch failed: {exc}")

        # If no real records came back, fall back to mock so dashboard works.
        if not records:
            mock = MockAdapter()
            for t in mock.tools:
                tools[t.id] = t
            records = mock.fetch_usage(start, end)

        self.records = records
        self.tools = list(tools.values())

    # -----------------------------------------------------------------------
    # Aggregations the API needs
    # -----------------------------------------------------------------------
    def list_tools(self) -> list[dict]:
        return [
            {"id": t.id, "name": t.name, "color": t.color,
             "costPer1k": t.cost_per_1k_tokens}
            for t in self.tools
        ]

    def list_lobs(self) -> list[dict]:
        lobs: dict[str, set[str]] = defaultdict(set)
        for r in self.records:
            lobs[r.lob].add(r.team)
        return [{"name": lob, "teams": sorted(teams)} for lob, teams in lobs.items()]

    def list_teams(self, lob: str = "all") -> list[dict]:
        # Build (lob, team) -> tool_id -> daily list
        end = date.today()
        days = [end - timedelta(days=i) for i in range(WINDOW_DAYS - 1, -1, -1)]
        idx = {d: i for i, d in enumerate(days)}
        tool_ids = [t.id for t in self.tools]

        # team_id is deterministic from (lob, team) for stable drill-down URLs
        teams: dict[tuple[str, str], dict] = {}
        for r in self.records:
            if lob != "all" and r.lob != lob:
                continue
            key = (r.lob, r.team)
            if key not in teams:
                teams[key] = {
                    "lob": r.lob, "team": r.team,
                    "toolUsage": {tid: {"daily": [0] * WINDOW_DAYS, "users": 0}
                                  for tid in tool_ids},
                    "_users": defaultdict(set),  # tool_id -> set of users
                }
            day_idx = idx.get(r.day)
            if day_idx is None:
                continue
            usage = teams[key]["toolUsage"].setdefault(
                r.tool_id, {"daily": [0] * WINDOW_DAYS, "users": 0})
            usage["daily"][day_idx] += r.tokens
            teams[key]["_users"][r.tool_id].add(r.user_email)

        # Finalize user counts and assign stable ids
        out = []
        for i, ((lob_name, team_name), payload) in enumerate(sorted(teams.items())):
            for tid, usage in payload["toolUsage"].items():
                usage["users"] = len(payload["_users"].get(tid, set()))
            del payload["_users"]
            payload["id"] = i
            out.append(payload)
        return out

    def team_users(self, team_id: int, days: int = 30) -> dict | None:
        all_teams = self.list_teams("all")
        if team_id < 0 or team_id >= len(all_teams):
            return None
        team_meta = all_teams[team_id]
        lob, team = team_meta["lob"], team_meta["team"]

        # Aggregate per-user tokens for this team in the window
        per_user: dict[str, dict] = {}
        for r in self.records:
            if r.lob != lob or r.team != team:
                continue
            if (date.today() - r.day).days >= days:
                continue
            u = per_user.setdefault(r.user_email, {
                "name": r.user_email.split("@")[0].replace(".", " ").title(),
                "role": "Engineer",
                "tools": defaultdict(int),
                "totalTokens": 0,
            })
            u["tools"][r.tool_id] += r.tokens
            u["totalTokens"] += r.tokens

        users = sorted(per_user.values(), key=lambda u: u["totalTokens"], reverse=True)
        for u in users:
            u["tools"] = dict(u["tools"])
        return {
            "team": {"id": team_id, "lob": lob, "team": team},
            "users": users[:12],
        }
