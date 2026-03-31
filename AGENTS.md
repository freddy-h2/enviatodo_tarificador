# AGENTS.md — Custer Boots Delivery Integration

> Instructions for AI coding agents operating in this repository.

## Project Overview

Odoo 19 delivery carrier module integrating **EnviaTodo.com** shipping API for **Custer Boots** (León, Guanajuato, Mexico). The repo contains:

- `odoo/delivery_enviatodo_custer/` — Odoo module (Python + XML) for self-hosted / Odoo.sh
- `odoo/cotizar_enviatodo.py` — Standalone CLI script for quoting shipments
- `zonas_custerboots/` — CSV zone/pricing data for delivery carriers
- `docs_enviatodo/` — EnviaTodo API documentation (Postman collection)

**Key business constants:** Origin ZIP `37000`, box dimensions 44×11×33 cm, weight 1.9 kg.

## Build / Lint / Test Commands

```bash
python3 --version          # 3.12+
pip install requests       # only external dependency (for standalone script)
```

### Linting

Ruff was used during development (`.ruff_cache/` exists). No `pyproject.toml` or `ruff.toml` — use defaults.

```bash
pip install ruff
ruff check odoo/                          # lint all Python files
ruff check odoo/delivery_enviatodo_custer/models/delivery_carrier.py  # single file
ruff format --check odoo/                 # check formatting
ruff format odoo/                         # auto-format
```

### Running the standalone script

```bash
# Requires ENVIATODO_API_KEY and ENVIATODO_USER_ID in environment or .env file
python odoo/cotizar_enviatodo.py 06600              # quote to CDMX
python odoo/cotizar_enviatodo.py 06600 --peso 2.5   # custom weight
python odoo/cotizar_enviatodo.py                    # interactive mode
```

### Odoo module testing

```bash
odoo -d <dbname> -i delivery_enviatodo_custer --stop-after-init           # install
odoo -d <dbname> --test-enable --test-tags /delivery_enviatodo_custer --stop-after-init  # test
```

No unit tests exist yet. Manual testing follows `odoo/PRUEBAS_ENVIATODO.md`.

### Issue tracking

```bash
hb ready              # find available work
hb show <id>          # view issue details
hb update <id> --status in_progress  # claim work
hb close <id>         # complete work
hb sync               # sync with git
```

## Code Style Guidelines

### Python — Odoo Module (`odoo/delivery_enviatodo_custer/`)

#### Imports — order and grouping

```python
# 1. Standard library (alphabetical)
import base64
import json
import logging
import re

# 2. Third-party
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

# 3. Odoo imports (always this exact order)
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
```

Odoo imports use **alphabetical** order: `_, api, fields, models`. Never import unused submodules.

#### Naming conventions

| Element | Convention | Example |
|---|---|---|
| Module-level constants | `UPPER_SNAKE_CASE` | `ENVIATODO_REQUEST_TIMEOUT = 30` |
| Logger | `_logger` | `_logger = logging.getLogger(__name__)` |
| Model class | `PascalCase` | `class DeliveryCarrier(models.Model)` |
| Private methods | `_enviatodo_` prefix | `_enviatodo_check_credentials()` |
| Public API methods | `enviatodo_` prefix | `enviatodo_rate_shipment()` |
| UI action methods | `action_enviatodo_` prefix | `action_enviatodo_test_connection()` |
| Custom fields | `x_studio_` prefix | `x_studio_api_key_enviatodo` |

#### Formatting

- **Line length:** ~88-100 chars (ruff default). Long strings use parenthesized continuation.
- **Quotes:** Double quotes `"` everywhere (field definitions, dict keys, strings).
- **Docstrings:** Google-style with `Args:`, `Returns:`, `Raises:` sections.
- **Comments:** Section headers use `# ---` or `# ===` separator lines.
- **Encoding header:** `# -*- coding: utf-8 -*-` at top of every `.py` file.
- **Trailing commas:** Used in multi-line lists/dicts.

#### Error handling

- **User-facing errors:** Raise `UserError` with `_()` wrapped messages in **Spanish**.
- **API errors:** Map HTTP status codes explicitly (401, 403, 404, 5xx) to specific `UserError` messages.
- **Logging:** `_logger.info()` for API calls, `_logger.warning()` for recoverable errors, `_logger.exception()` for unexpected failures.
- **Never silently swallow exceptions** — always log at minimum.
- **Return dicts** for rate methods: `{"success": bool, "price": float, "error_message": str, "warning_message": str}`.

#### Odoo-specific patterns

- Inherit with `_inherit = "delivery.carrier"` (no `_name` when extending).
- `selection_add` with `ondelete` for extending Selection fields.
- Always call `self.ensure_one()` at the start of single-record methods.
- Use `_(...)` for all user-facing strings (i18n).
- Use `record.write({...})` instead of direct attribute assignment in automated actions.
- Use `message_post()` with `subtype_xmlid='mail.mt_note'` for internal notes.
- Attachment creation via `self.env["ir.attachment"].create({...})`.

### XML Views (`views/`)

- Odoo 17+ syntax: `invisible="delivery_type != 'enviatodo'"` (NOT `attrs={'invisible': [...]}`).
- XPath expressions target `position="after"` on existing pages.
- Group fields into `<group>` elements with descriptive `string` and `name` attributes.
- Use `required="delivery_type == 'enviatodo'"` for conditional requirements.
- Add `password="True"` for sensitive fields like API keys.

### Standalone Script (`cotizar_enviatodo.py`)

- `#!/usr/bin/env python3` shebang. No Odoo dependencies — pure `requests` + stdlib.
- Uses `%` string formatting (not f-strings) for consistency with Odoo conventions.
- Console output uses Unicode box-drawing characters and emoji for readability.

## Git Conventions

```
feat: <description>      # new feature
fix: <description>       # bug fix
docs: <description>      # documentation only
refactor: <description>  # code restructuring
```

Commit messages are in English. Code comments and user-facing strings are in **Spanish**.

## Security

- **Never commit** `.env`, `.env.local`, or files containing API keys/tokens.
- `.env.local` exists in the repo root — it contains real credentials. Do NOT read or expose its contents.
- API keys in Odoo fields use `password="True"` in XML views.

## Key Files Reference

| File | Purpose |
|---|---|
| `odoo/delivery_enviatodo_custer/__manifest__.py` | Module metadata, version `19.0.1.0.0` |
| `odoo/delivery_enviatodo_custer/models/delivery_carrier.py` | Core integration logic (858 lines) |
| `odoo/delivery_enviatodo_custer/views/delivery_carrier_views.xml` | Carrier config form |
| `odoo/cotizar_enviatodo.py` | Standalone CLI quoting tool |
| `odoo/GUIA_IMPLEMENTACION_ENVIATODO.md` | Full implementation guide (SaaS + self-hosted) |
| `odoo/PRUEBAS_ENVIATODO.md` | Manual testing guide (5 phases) |
| `docs_enviatodo/Enviatodo Api V2.json` | Postman API collection |

## Don't

- Don't use `import` statements in Odoo automated action code (sandbox blocks them).
- Don't use `return` at top level in automated actions.
- Don't use `record.field = value` in automated actions — use `record.write({...})`.
- Don't modify the EnviaTodo API base URL unless explicitly instructed.
- Don't change the default box dimensions (44×11×33 cm, 1.9 kg) without business approval.
- Don't push to `main` without ensuring `hb sync` and `git push` both succeed.
