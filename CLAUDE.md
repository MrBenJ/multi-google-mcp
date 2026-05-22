# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local stdio MCP server exposing Gmail / Google Calendar / Google Drive tools to a single user, with **multi-account routing**: every tool call takes an `account` label (e.g. `"work"`, `"personal"`) and the server resolves it to the matching OAuth credentials under `~/.config/multi-google-mcp/accounts/<label>.json`. Designed for personal local use only — not for hosting.

## Commands

Dependencies are managed with `uv` (a Python lock file is committed in `uv.lock`):

- `uv sync` — install dev + runtime deps into `.venv`
- `uv run pytest` — full unit test suite (mocks the Google client; no network)
- `uv run pytest tests/tools/test_gmail.py::test_name` — single test
- `uv run pytest tests/shaping` — only the payload-shaping tests
- `uv run ruff check .` — lint (config in `pyproject.toml`, line length 100, py311)
- `uv run mypy` — strict type-check (Google + mcp libs are excused via overrides)
- `uv tool install .` — install the two console scripts (`multi-google-mcp`, `multi-google-mcp-auth`) onto `PATH`
- `MCP_E2E_ACCOUNT=<label> uv run python scripts/e2e_smoke.py` — real end-to-end smoke that boots the server as a subprocess, drives every tool against live Google APIs, and cleans up. Requires a dedicated test account already added via `multi-google-mcp-auth add <label>`.

CI runs `ruff check`, `mypy`, and `pytest` on every push/PR to `main` (`.github/workflows/ci.yml`).

## Architecture

### Two entry points (`pyproject.toml [project.scripts]`)

- `multi_google_mcp.server:main` — the stdio MCP server. Builds an `mcp.server.Server`, registers tools from `TOOL_REGISTRY`, runs over `mcp.server.stdio.stdio_server`.
- `multi_google_mcp.auth_cli:main` — the `add` / `list` / `remove` CLI that drives `google_auth_oauthlib.InstalledAppFlow` and persists tokens.

### The `TOOL_REGISTRY` pattern (`src/multi_google_mcp/server.py`)

All tool definitions live in a single list of `{name, description, schema, handler}` dicts. `build_app()` enumerates this list for both `list_tools` and `call_tool`. **Adding a new tool means appending one dict here** — there is no decorator/auto-discovery layer. Each `handler` is `lambda args: tool_module.fn(**args)`, so the JSON schema's property names must match the underlying function's keyword arguments exactly.

`_invoke_tool` wraps every handler call and translates failures into a stable `"error: ..."` text payload — `MultiGoogleMcpError` (account/oauth/size) verbatim, `HttpError` formatted with status + reason, `ValueError`/`TypeError`/`KeyError` as "invalid arguments", anything else as "internal error". The MCP transport never sees a Python exception. Preserve this convention when adding tools — don't let exceptions escape `_invoke_tool`.

### Layering: `tools/` vs `shaping/`

- `tools/{gmail,calendar,drive}.py` — call Google APIs via `googleapiclient.discovery.build`, then hand raw responses to the shaping module.
- `shaping/{gmail,calendar,drive}.py` — pure functions that compact Google's verbose API payloads into the small dicts returned to the model. **Keep API calls out of `shaping/`** and keep payload massaging out of `tools/`; the shaping tests in `tests/shaping/` rely on this split (they feed canned dicts and assert structure).

Each tool module has a private `_service(account)` helper that does `creds = _store.credentials(account); creds = _store.refresh_if_needed(account, creds); return build(...)`. Token refresh happens lazily on every call — there is no global service cache.

### Credentials (`accounts.py`)

- One JSON file per account under `config.ACCOUNTS_DIR` (`~/.config/multi-google-mcp/accounts/`).
- Labels are validated against a strict slug regex (`^[A-Za-z0-9_-]{1,64}$`) — this is the **path-traversal guard**; do not loosen it.
- Writes go through `_atomic_write_json`: `os.open` with `O_CREAT|O_EXCL|O_WRONLY` + mode `0o600`, then `os.replace`. Refresh tokens must never be momentarily world-readable.
- `_file_lock` (fcntl flock on a sidecar `.lock`) guards the read-modify-write in `_on_refresh` so the server and the auth CLI can't race.
- A refresh that fails with `"invalid_grant"` raises `AccountNeedsReauth` — that's the signal the user has to rerun `multi-google-mcp-auth add <label>` (revoked, scope changed, or 7-day test-mode expiry).

### Size caps (`config.py`)

- `MAX_DRIVE_BYTES` (10 MiB) — applied differently for the two Drive file kinds:
  - **Native** Docs/Sheets/Slides report `size=0` in metadata, so `drive_read_file` streams the export through `MediaIoBaseDownload` and raises `DriveFileTooLarge` mid-stream once the buffer crosses the cap.
  - **Binary** files: size is pre-checked from metadata before any download.
  - Uploads: payload size checked after base64 decode in `_media()`.
- `MAX_GMAIL_BODY_BYTES` (256 KiB) — `gmail_get_message` truncates with a marker that includes the original byte count, so the agent can decide whether to skip or widen.

### Adding OAuth scope

Edit `config.SCOPES` and then **every account** must be re-added via `multi-google-mcp-auth add <label>` — Google requires re-consent on scope changes. There is no merge/upgrade flow.

## Testing layout

- `tests/conftest.py` — `tmp_config_dir` redirects `config.CONFIG_DIR` to a tmp path; `saved_account` drops a token file with a fake client_secret; `mock_build` patches `googleapiclient.discovery.build` in all three tool modules at once and returns the shared `MagicMock` service + a list of recorded `(api, version)` build calls.
- `tests/tools/` — drive the tool functions with the mocked service, assert what was called and what was returned.
- `tests/shaping/` — pure-data tests on the shaping functions; no mocks.
- `scripts/e2e_smoke.py` — the only thing that hits real Google APIs. It is **not** part of `pytest`; run it manually before releases.

## Conventions

- Strict mypy (`disallow_untyped_defs` etc. via `strict = true`). New code needs annotations; only the Google/mcp library boundaries are exempt via the `[[tool.mypy.overrides]]` block.
- Ruff selects `E, F, W, I, B, UP` — Python ≥ 3.11 idioms (`X | None` over `Optional[X]`, `list[X]` over `List[X]`).
- `from __future__ import annotations` at the top of every module.
- The MCP transport sees only JSON strings or `"error: ..."` strings — never raise an exception out of a tool handler.
