"""
Smoke tests for the adapter contract.

Run:
    pip install pytest
    pytest -q
"""
from __future__ import annotations

from datetime import date, timedelta

from adapters import REGISTRY
from adapters.base import Adapter, UsageRecord


def test_registry_not_empty():
    assert REGISTRY, "REGISTRY should expose at least the mock adapter"
    assert "mock" in REGISTRY


def test_every_adapter_has_meta():
    for adapter_id, cls in REGISTRY.items():
        meta = cls.meta
        assert meta.id == adapter_id, f"{adapter_id}: meta.id mismatch"
        assert meta.name, f"{adapter_id}: name required"
        assert meta.color.startswith("#"), f"{adapter_id}: color must be hex"
        assert meta.cost_per_1k_tokens >= 0


def test_every_adapter_returns_list():
    """Without credentials, real adapters return []. Mock returns records."""
    start = date.today() - timedelta(days=6)
    end = date.today()
    for adapter_id, cls in REGISTRY.items():
        records = cls().fetch_usage(start, end)
        assert isinstance(records, list)
        for r in records:
            assert isinstance(r, UsageRecord)
            assert r.tool_id
            assert r.tokens >= 0


def test_mock_produces_data():
    mock = REGISTRY["mock"]()
    records = mock.fetch_usage(date.today() - timedelta(days=6), date.today())
    assert len(records) > 100
    tools_seen = {r.tool_id for r in records}
    assert "ms-copilot" in tools_seen
    assert "claude-code" in tools_seen


def test_adapter_is_subclass_of_adapter():
    for cls in REGISTRY.values():
        assert issubclass(cls, Adapter)
