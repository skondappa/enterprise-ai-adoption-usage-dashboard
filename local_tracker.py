"""
Local AI tool tracker — reads usage from this machine, for the current user.

Powers the "Me" view in the dashboard. Useful for individual contributors
who want to see how much they personally lean on AI tools, independent
of any enterprise rollup.

Currently reads from:
    Claude Code  - ~/.claude/projects/*/<session>.jsonl
    ChatGPT      - desktop app conversations OR OpenAI API usage endpoint

Stubs (return [] today, structured so you can wire them up):
    GitHub Copilot  - VS Code extension log directory
    Cursor          - ~/.cursor/usage/

To add a new local source, drop a function into the LOCAL_SOURCES dict.
The function must return a list of dicts with this shape:

    {"day": "2026-04-27", "tokens": int, "tool": str, "project": str}
"""
from __future__ import annotations

import json
import os
import re
import socket
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Claude Code (real implementation — reads JSONL session logs)
# ---------------------------------------------------------------------------
def _claude_code_usage(window_days: int = 30) -> list[dict]:
    home = Path.home() / ".claude" / "projects"
    if not home.exists():
        return []

    cutoff = datetime.now() - timedelta(days=window_days)
    out: list[dict] = []
    usage_re = re.compile(
        r'"usage":\{[^}]*?"input_tokens":(\d+)[^}]*?"output_tokens":(\d+)'
    )
    ts_re = re.compile(r'"timestamp":"([^"]+)"')

    for project_dir in home.iterdir():
        if not project_dir.is_dir():
            continue
        # decode project path: dashes → original path
        project_name = project_dir.name.replace("--", ":/").replace("-", "/")
        # crude shortener for display
        display = project_name.split("/")[-1] or project_name

        for session_file in project_dir.glob("*.jsonl"):
            try:
                with session_file.open(encoding="utf-8") as fh:
                    for line in fh:
                        ts_match = ts_re.search(line)
                        u_match = usage_re.search(line)
                        if not (ts_match and u_match):
                            continue
                        try:
                            ts = datetime.fromisoformat(
                                ts_match.group(1).replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except ValueError:
                            continue
                        if ts < cutoff:
                            continue
                        tokens = int(u_match.group(1)) + int(u_match.group(2))
                        out.append({
                            "day": ts.date().isoformat(),
                            "tokens": tokens,
                            "tool": "Claude Code",
                            "project": display,
                        })
            except (OSError, UnicodeDecodeError):
                continue
    return out


# ---------------------------------------------------------------------------
# GitHub Copilot (stub — wire to your local install)
# ---------------------------------------------------------------------------
def _github_copilot_usage(window_days: int = 30) -> list[dict]:
    """
    Production outline:
        VS Code stores Copilot logs at:
            Windows: %APPDATA%\\Code\\logs\\<date>\\exthost1\\GitHub.copilot\\
            macOS:   ~/Library/Application Support/Code/logs/...
            Linux:   ~/.config/Code/logs/...

        Parse the .log files for `[trace] suggestion accepted` events.
        Each event has a token count via `prompt_tokens` and
        `completion_tokens` fields.
    """
    return []


# ---------------------------------------------------------------------------
# Cursor (stub)
# ---------------------------------------------------------------------------
def _cursor_usage(window_days: int = 30) -> list[dict]:
    """
    Production outline:
        Cursor writes usage to ~/.cursor/usage/usage_YYYY-MM-DD.jsonl
        each line has {"event": "completion", "tokens": int, "ts": ...}
    """
    return []


# ---------------------------------------------------------------------------
# ChatGPT (two paths — desktop app first, then OpenAI API)
# ---------------------------------------------------------------------------
def _chatgpt_desktop_app(window_days: int) -> list[dict]:
    """ChatGPT desktop app stores conversations locally. Counts approximated
    from message lengths since the app does not record token counts."""
    candidates = [
        Path.home() / "AppData" / "Roaming" / "ChatGPT" / "conversations",
        Path.home() / "AppData" / "Local" / "ChatGPT" / "conversations",
        Path.home() / "Library" / "Application Support" / "ChatGPT" / "conversations",
        Path.home() / ".config" / "ChatGPT" / "conversations",
    ]
    folder = next((p for p in candidates if p.exists()), None)
    if folder is None:
        return []

    cutoff = datetime.now() - timedelta(days=window_days)
    out: list[dict] = []
    for f in folder.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        title = data.get("title") or f.stem
        # The desktop app's conversation schema varies; this handles the
        # common shape: {"mapping": {id: {"message": {"create_time": ts,
        # "content": {"parts": [str]}}}}}
        for node in (data.get("mapping") or {}).values():
            msg = (node or {}).get("message") or {}
            ts = msg.get("create_time")
            if not ts:
                continue
            when = datetime.fromtimestamp(ts)
            if when < cutoff:
                continue
            parts = ((msg.get("content") or {}).get("parts") or [])
            chars = sum(len(p) for p in parts if isinstance(p, str))
            # ~4 chars per token is the standard OpenAI rule of thumb
            out.append({
                "day": when.date().isoformat(),
                "tokens": max(1, chars // 4),
                "tool": "ChatGPT",
                "project": title[:40],
            })
    return out


def _chatgpt_via_api(window_days: int) -> list[dict]:
    """Fetch real token usage from the OpenAI usage endpoint.

    Requires an OpenAI **admin** API key (starts with `sk-admin-`) — your
    standard `sk-...` user key cannot read org usage.

    Set:
        OPENAI_ADMIN_KEY=sk-admin-...
        OPENAI_ORG_ID=org-...     # optional, only for multi-org accounts

    Endpoint: https://platform.openai.com/docs/api-reference/usage
    """
    key = os.getenv("OPENAI_ADMIN_KEY")
    if not key:
        return []
    try:
        import requests
    except ImportError:
        return []

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=window_days)).timestamp())
    headers = {"Authorization": f"Bearer {key}"}
    if os.getenv("OPENAI_ORG_ID"):
        headers["OpenAI-Organization"] = os.environ["OPENAI_ORG_ID"]

    try:
        r = requests.get(
            "https://api.openai.com/v1/organization/usage/completions",
            params={"start_time": start_ts, "end_time": end_ts,
                    "bucket_width": "1d", "limit": 31},
            headers=headers, timeout=10,
        )
        r.raise_for_status()
    except Exception as exc:
        print(f"[chatgpt] API call failed: {exc}")
        return []

    out: list[dict] = []
    for bucket in r.json().get("data", []):
        day = datetime.fromtimestamp(bucket["start_time"]).date().isoformat()
        for row in bucket.get("results", []):
            tokens = (row.get("input_tokens", 0) +
                      row.get("output_tokens", 0))
            if tokens:
                out.append({
                    "day": day, "tokens": tokens,
                    "tool": "ChatGPT", "project": row.get("model", "openai-api"),
                })
    return out


def _chatgpt_usage(window_days: int = 30) -> list[dict]:
    rows = _chatgpt_desktop_app(window_days)
    if rows:
        return rows
    return _chatgpt_via_api(window_days)


LOCAL_SOURCES = {
    "Claude Code":    _claude_code_usage,
    "ChatGPT":        _chatgpt_usage,
    "GitHub Copilot": _github_copilot_usage,
    "Cursor":         _cursor_usage,
}


# ---------------------------------------------------------------------------
# Public API used by app.py
# ---------------------------------------------------------------------------
def my_usage(window_days: int = 30) -> dict:
    """Return aggregated personal usage for the dashboard's Me view."""
    rows: list[dict] = []
    for source_name, fn in LOCAL_SOURCES.items():
        try:
            rows.extend(fn(window_days=window_days))
        except Exception as exc:
            print(f"[local-tracker] {source_name} failed: {exc}")

    # Daily totals across all tools
    by_day: dict[str, int] = defaultdict(int)
    by_tool: dict[str, int] = defaultdict(int)
    by_project: dict[str, int] = defaultdict(int)
    for r in rows:
        by_day[r["day"]] += r["tokens"]
        by_tool[r["tool"]] += r["tokens"]
        by_project[r["project"]] += r["tokens"]

    today = date.today()
    daily = []
    for i in range(window_days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        daily.append({"day": d, "tokens": by_day.get(d, 0)})

    today_tokens = by_day.get(today.isoformat(), 0)
    total_tokens = sum(r["tokens"] for r in rows)
    active_days = sum(1 for d in daily if d["tokens"] > 0)

    return {
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "you",
        "host": socket.gethostname(),
        "windowDays": window_days,
        "totalTokens": total_tokens,
        "todayTokens": today_tokens,
        "activeDays": active_days,
        "daily": daily,
        "byTool": [{"tool": t, "tokens": v} for t, v in sorted(by_tool.items(), key=lambda kv: -kv[1])],
        "byProject": [{"project": p, "tokens": v} for p, v in sorted(by_project.items(), key=lambda kv: -kv[1])][:10],
        "sources": [
            {"name": name, "ok": bool(fn(window_days=1)) or name == "Claude Code"}
            for name, fn in LOCAL_SOURCES.items()
        ],
    }
