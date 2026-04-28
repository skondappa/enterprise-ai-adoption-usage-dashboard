"""
Enterprise AI Adoption — Flask entry point.

Run:
    pip install -r requirements.txt
    python app.py

Then open http://localhost:5000 in your browser.

Configuration is via environment variables (or a .env file — see
.env.example). The most important one is:

    ENABLED_ADAPTERS=mock                      # demo (default)
    ENABLED_ADAPTERS=ms-copilot,gh-copilot     # real sources

See docs/data-sources/ for per-vendor setup.
"""
from __future__ import annotations

import csv
import io
import os

from flask import Flask, jsonify, request, send_from_directory

from store import Store
from local_tracker import my_usage


# Load .env if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


app = Flask(__name__, static_folder="static", static_url_path="/static")
store = Store()


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("static", "dashboard.html")


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------
@app.route("/api/meta")
def api_meta():
    """Tools and LOBs that drive the filters and color mapping."""
    return jsonify({"tools": store.list_tools(), "lobs": store.list_lobs()})


@app.route("/api/teams")
def api_teams():
    """Per-team daily usage for the last 30 days, optionally filtered by LOB."""
    return jsonify(store.list_teams(lob=request.args.get("lob", "all")))


@app.route("/api/team/<int:team_id>/users")
def api_team_users(team_id: int):
    """Top users for a team with per-tool token totals."""
    days = 1 if request.args.get("range") == "day" else 30
    payload = store.team_users(team_id, days=days)
    if payload is None:
        return jsonify({"error": "team not found"}), 404
    return jsonify(payload)


@app.route("/api/export.csv")
def api_export_csv():
    """Stream the team breakdown as CSV."""
    days = 1 if request.args.get("range") == "day" else 30
    teams = store.list_teams(lob=request.args.get("lob", "all"))
    tools = store.list_tools()
    cost_lookup = {t["id"]: t["costPer1k"] for t in tools}
    name_lookup = {t["id"]: t["name"] for t in tools}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Line of Business", "Team", "Tools Adopted",
                "Active Users", "Tokens", "Cost (USD)", "Adoption %"])
    for t in teams:
        adopted, tokens, cost = [], 0, 0.0
        for tid, u in t["toolUsage"].items():
            window = sum(u["daily"][-days:])
            tokens += window
            cost += (window / 1000) * cost_lookup.get(tid, 0)
            if window > 0:
                adopted.append(name_lookup.get(tid, tid))
        users = max((u["users"] for u in t["toolUsage"].values()), default=0)
        adoption = round(len(adopted) / max(len(tools), 1) * 100, 1)
        w.writerow([t["lob"], t["team"], "; ".join(adopted),
                    users, tokens, round(cost, 2), adoption])
    return (buf.getvalue(), 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="ai-adoption.csv"',
    })


@app.route("/api/me")
def api_me():
    """Personal usage from local tool logs (Claude Code, Copilot, etc.)."""
    days = int(request.args.get("days", 30))
    return jsonify(my_usage(window_days=days))


@app.route("/api/health")
def api_health():
    """Lists each adapter's healthcheck status."""
    from adapters import enabled_adapters
    return jsonify({
        "status": "ok",
        "adapters": [
            {"id": a.id, "ok": a.healthcheck()[0], "message": a.healthcheck()[1]}
            for a in enabled_adapters()
        ],
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Re-pull from all enabled adapters. In production this would be a
    scheduled job; here it's exposed for manual / on-demand refresh."""
    store.refresh()
    return jsonify({"status": "refreshed", "records": len(store.records)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
