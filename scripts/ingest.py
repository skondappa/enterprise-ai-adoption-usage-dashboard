"""
One-shot ingestion across all enabled adapters.

Useful for:
    - Cron / Airflow / EventBridge schedules
    - Verifying credentials without running the dashboard
    - Backfilling a date range manually

Usage:
    python scripts/ingest.py                    # last 30 days
    python scripts/ingest.py --days 90          # last 90 days
    python scripts/ingest.py --adapter ms-copilot
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running as `python scripts/ingest.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters import REGISTRY, enabled_adapters  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Pull AI usage from all enabled adapters.")
    parser.add_argument("--days", type=int, default=30, help="Lookback window")
    parser.add_argument("--adapter", help="Only run a single adapter id")
    args = parser.parse_args()

    end = date.today()
    start = end - timedelta(days=args.days - 1)

    if args.adapter:
        cls = REGISTRY.get(args.adapter)
        if cls is None:
            print(f"Unknown adapter: {args.adapter}")
            print(f"Known: {', '.join(REGISTRY)}")
            sys.exit(2)
        adapters = [cls()]
    else:
        adapters = enabled_adapters()

    print(f"Ingesting {start} -> {end} from {len(adapters)} adapter(s)")
    grand_total = 0
    for a in adapters:
        ok, msg = a.healthcheck()
        marker = "[OK]" if ok else "[--]"
        print(f"  {marker} {a.id:<14} {msg}")
        if not ok:
            continue
        try:
            records = a.fetch_usage(start, end)
        except Exception as exc:
            print(f"     ERROR: {exc}")
            continue
        tokens = sum(r.tokens for r in records)
        grand_total += tokens
        print(f"     {len(records):,} records · {tokens:,} tokens")

    print(f"\nTotal tokens across all adapters: {grand_total:,}")


if __name__ == "__main__":
    main()
