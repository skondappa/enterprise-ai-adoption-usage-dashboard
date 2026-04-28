"""
Adapter registry.

Add new adapters here. The dashboard automatically picks them up via
`enabled_adapters()`, which reads the ENABLED_ADAPTERS environment
variable (comma-separated ids).
"""
from __future__ import annotations

import os
from .base import Adapter, AdapterMeta, UsageRecord
from .mock import MockAdapter
from .microsoft_copilot import MicrosoftCopilotAdapter
from .github_copilot import GithubCopilotAdapter
from .amazon_q import AmazonQAdapter
from .claude_code import ClaudeCodeAdapter

# All known adapter classes, keyed by their stable id.
REGISTRY: dict[str, type[Adapter]] = {
    "mock":         MockAdapter,
    "ms-copilot":   MicrosoftCopilotAdapter,
    "gh-copilot":   GithubCopilotAdapter,
    "amazon-q":     AmazonQAdapter,
    "claude-code":  ClaudeCodeAdapter,
}


def enabled_adapters() -> list[Adapter]:
    """Read ENABLED_ADAPTERS env var and instantiate the matching adapters.

    Defaults to "mock" so the dashboard works out of the box without any
    vendor credentials. To enable real sources:
        ENABLED_ADAPTERS=ms-copilot,gh-copilot
    """
    ids = os.getenv("ENABLED_ADAPTERS", "mock").split(",")
    ids = [i.strip() for i in ids if i.strip()]
    instances: list[Adapter] = []
    for tool_id in ids:
        cls = REGISTRY.get(tool_id)
        if cls is None:
            print(f"[adapters] unknown adapter id: {tool_id} — skipping")
            continue
        instances.append(cls())
    return instances


__all__ = [
    "Adapter", "AdapterMeta", "UsageRecord",
    "REGISTRY", "enabled_adapters",
]
