"""
Adapter base class.

Every concrete adapter (Microsoft Copilot, GitHub Copilot, Amazon Q,
Claude Code, ...) inherits from `Adapter` and implements `fetch_usage`.

The adapter is responsible for:
    1. Authenticating against the vendor API.
    2. Pulling raw usage data for the requested window.
    3. Returning a list of canonical `UsageRecord`s — see `models.py` for
       the canonical schema. The dashboard never sees vendor-specific shapes.

Adding a new tool? Inherit from `Adapter`, implement `fetch_usage`, and
register the class in `adapters/__init__.py`. That's it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class UsageRecord:
    """One row of normalized AI tool usage."""
    day: date
    tool_id: str          # stable identifier, e.g. "ms-copilot"
    tool_name: str        # display name, e.g. "Microsoft Copilot"
    user_email: str       # used to roll up to teams via directory lookup
    team: str             # team name (after directory enrichment)
    lob: str              # line of business
    tokens: int           # tokens consumed (or proxy metric — see notes)
    sessions: int = 0
    suggestions_accepted: int = 0
    cost_usd: float = 0.0
    extra: dict = field(default_factory=dict)


@dataclass
class AdapterMeta:
    """Static metadata about the tool this adapter represents."""
    id: str
    name: str
    vendor: str
    color: str            # hex color for charts
    cost_per_1k_tokens: float


class Adapter(ABC):
    """Abstract base. Subclass per vendor."""

    meta: AdapterMeta

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        """Pull raw usage between [start, end] inclusive and normalize."""
        raise NotImplementedError

    def healthcheck(self) -> tuple[bool, str]:
        """Optional: verify the adapter can reach its source. Override
        to call a cheap endpoint and return (ok, message)."""
        return True, "no healthcheck implemented"

    @property
    def id(self) -> str:
        return self.meta.id

    @property
    def name(self) -> str:
        return self.meta.name
