---
name: add-data-source
description: Add a new AI tool integration to the Enterprise AI Adoption dashboard. Creates the adapter file, registers it, scaffolds the docs page, and updates .env.example. Use when the user says "add an adapter for X", "integrate X", or "track X usage".
---

# Add a new data source

Use this skill when the user wants to wire a new AI tool (e.g. Cursor,
Tabnine, Codeium, Replit Ghostwriter, internal tooling) into the
Enterprise AI Adoption dashboard.

## Steps

### 1. Confirm the slug
Pick a kebab-case `tool_id` (e.g. `cursor`, `tabnine`, `codeium`). It
must match the filename and the registry key. Confirm with the user
before proceeding.

### 2. Create `adapters/<tool_id_snake>.py`

Use this template — replace `XxxAdapter`, `tool-id`, `Tool Name`,
`Vendor`, color, and the docstring URLs:

```python
"""
<Tool Name> adapter.

Pulls usage from <vendor API name>. See:
    docs/data-sources/<tool-id>.md

Required env vars:
    <VAR_1> - <description>
    <VAR_2> - <description>
"""
from __future__ import annotations
import os
from datetime import date

from .base import Adapter, AdapterMeta, UsageRecord


class XxxAdapter(Adapter):
    meta = AdapterMeta(
        id="<tool-id>",
        name="<Tool Name>",
        vendor="<Vendor>",
        color="#<hex>",                # pick from the spectrum, avoid existing colors
        cost_per_1k_tokens=0.0,        # contracted rate or vendor list price
    )

    def fetch_usage(self, start: date, end: date) -> list[UsageRecord]:
        # Production fetch outline — keep this code in the docstring or
        # commented-out so the file works without dependencies installed.
        if not os.getenv("<PRIMARY_ENV_VAR>"):
            return []
        return []

    def healthcheck(self) -> tuple[bool, str]:
        if not os.getenv("<PRIMARY_ENV_VAR>"):
            return False, "<PRIMARY_ENV_VAR> not set"
        return True, "credentials present"
```

### 3. Register in `adapters/__init__.py`

Add an import and an entry to `REGISTRY`:

```python
from .your_tool import XxxAdapter
# ...
REGISTRY = {
    ...,
    "<tool-id>": XxxAdapter,
}
```

### 4. Document in `docs/data-sources/<tool-id>.md`

Mirror the structure of `docs/data-sources/microsoft-copilot.md`:
- What you get (table of fields)
- Step 1: get credentials
- Step 2: configure the dashboard (the `.env` keys)
- Step 3: endpoints used
- Mapping users to teams (HRIS join)
- Rate limits / costs

### 5. Update `.env.example`

Add a commented section at the bottom for the new tool's env vars.

### 6. Update the index

Add a row to `docs/data-sources/README.md`.

### 7. Verify

```bash
python -c "from adapters import REGISTRY; print(list(REGISTRY))"
curl -s http://localhost:5000/api/health
```

## Rules

- **Never** modify `static/dashboard.html` for a new tool. The
  dashboard auto-renders any tool the adapter exposes via
  `AdapterMeta`.
- **Never** modify `store.py` for a new tool. The aggregator is
  vendor-agnostic by design.
- **Always** add the `docs/data-sources/<tool-id>.md` page in the
  same change. Adapters without docs are unmaintainable.
- **Choose distinct colors.** Existing: cyan #06b6d4, amber #f59e0b,
  pink #ec4899, violet #8b5cf6, green #10b981. Suggest: indigo
  #6366f1, rose #f43f5e, emerald #059669, sky #0ea5e9, fuchsia #d946ef.
- **Don't install vendor SDKs into requirements.txt by default.**
  List them as commented optional installs. Users who don't enable
  the adapter shouldn't have to install its SDK.
