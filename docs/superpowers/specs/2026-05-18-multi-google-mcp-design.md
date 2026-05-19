# Multi-Google MCP Server — Design

**Date:** 2026-05-18
**Status:** Draft, pending user review
**Target client:** Claude Desktop (local stdio MCP)
**Scope:** Personal use on a single machine — not published

---

## 1. Goal

A local MCP server that lets Claude Desktop operate across multiple Gmail
accounts, each with read+write access to Gmail, Google Calendar, and Google
Drive. Tokens live on disk under `~/.config/multi-google-mcp/`. The agent
picks which account to use via an explicit `account` argument on every tool.

## 2. Non-goals

- Multi-user / multi-machine deployment
- Hosting / publishing to a registry
- Remote MCP / OAuth-broker server
- Background sync, indexing, or caching
- Retry / backoff policies (errors surface to the agent verbatim)
- Permanent Gmail delete (trash is reversible; agent uses `gmail_modify_labels`
  with `trash=true`)

## 3. Stack

- Python 3.11+
- Packaged with `uv` (works with Claude Desktop `command/args` config)
- `mcp` Python SDK (stdio transport)
- `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- Test stack: `pytest`, `ruff`, `mypy --strict`

## 4. Repository layout

```
multi-google-mcp/
├── pyproject.toml
├── README.md                              # GCP setup + Claude Desktop wiring
├── docs/superpowers/specs/                # this file
├── src/multi_google_mcp/
│   ├── __init__.py
│   ├── server.py                          # MCP entrypoint, tool registry
│   ├── auth_cli.py                        # `multi-google-mcp-auth add|list|remove <label>`
│   ├── accounts.py                        # AccountStore: load/save tokens, build Credentials
│   ├── config.py                          # paths, scopes, constants
│   └── tools/
│       ├── __init__.py
│       ├── gmail.py
│       ├── calendar.py
│       └── drive.py
├── tests/
│   ├── test_accounts.py
│   ├── test_shaping.py                    # response-shaping helpers
│   ├── test_tools_gmail.py                # mocked google service
│   ├── test_tools_calendar.py
│   └── test_tools_drive.py
└── scripts/
    └── e2e_smoke.py                       # live end-to-end smoke (Levels 1+2)
```

## 5. Auth and storage

### 5.1 GCP setup (one-time, documented in README)

1. Create a GCP project.
2. Enable Gmail API, Google Calendar API, Google Drive API.
3. Configure OAuth consent screen as **External**, publishing status **Testing**.
   Add every Gmail address that will be connected as a **test user**.
4. Create OAuth Client ID, application type **Desktop app**.
5. Download `client_secret.json`.
6. Place it at `~/.config/multi-google-mcp/client_secret.json`.

### 5.2 On-disk layout

```
~/.config/multi-google-mcp/
├── client_secret.json              # one OAuth client, shared across accounts
└── accounts/
    ├── personal.json               # refresh token + cached access token + email
    └── work.json
```

All files written with `chmod 600`. Each `accounts/<label>.json` contains:

```json
{
  "label": "work",
  "email": "alice@example.com",
  "refresh_token": "...",
  "access_token": "...",
  "token_expiry": "2026-05-18T22:31:00Z",
  "scopes": ["https://www.googleapis.com/auth/gmail.modify", "..."]
}
```

### 5.3 Auth CLI

Standalone command, runs outside the MCP server:

- `multi-google-mcp-auth add <label>` — opens browser via
  `InstalledAppFlow.run_local_server()`, captures refresh token, writes
  `accounts/<label>.json`. Records the authenticated email alongside the
  user-chosen label so `list_accounts` can show both.
- `multi-google-mcp-auth list` — prints configured `(label, email)` pairs.
- `multi-google-mcp-auth remove <label>` — deletes the token file.

### 5.4 OAuth scopes

A single consent screen requests:

- `https://www.googleapis.com/auth/gmail.modify` — read, send, label, trash
- `https://www.googleapis.com/auth/calendar` — full calendar
- `https://www.googleapis.com/auth/drive` — full drive
- `https://www.googleapis.com/auth/userinfo.email` — record which email each
  label maps to

## 6. Tool surface

17 tools total. Every operational tool takes `account: str` as the first
argument. Each tool returns compact, model-friendly JSON — not raw Google
API payloads.

### 6.1 Discovery (1)

| Tool | Returns |
|---|---|
| `list_accounts()` | `[{"label": "work", "email": "alice@example.com"}, ...]` |

### 6.2 Gmail (4)

| Tool | Notes |
|---|---|
| `gmail_search(account, query, max_results=10)` | Gmail search syntax. Returns `[{id, thread_id, from, subject, snippet, date}]`. |
| `gmail_get_message(account, message_id)` | Full headers + body. HTML→text fallback if no text/plain part. |
| `gmail_send(account, to, subject, body, cc?, bcc?, html=False, in_reply_to?)` | If `in_reply_to` is set, threads via `References`/`In-Reply-To` headers. |
| `gmail_modify_labels(account, message_id, add=[], remove=[], trash=False)` | `trash=True` moves to trash; combine with label edits as needed. |

### 6.3 Calendar (6)

| Tool | Notes |
|---|---|
| `calendar_list_calendars(account)` | `[{id, summary, primary, access_role}]` |
| `calendar_list_events(account, calendar_id="primary", time_min?, time_max?, query?, max_results=10)` | RFC3339 times. |
| `calendar_get_event(account, calendar_id, event_id)` | Full event payload, shaped. |
| `calendar_create_event(account, calendar_id, summary, start, end, description?, attendees?, location?)` | `start`/`end` accept date or datetime. |
| `calendar_update_event(account, calendar_id, event_id, **fields)` | Patches only the fields supplied. |
| `calendar_delete_event(account, calendar_id, event_id)` | |

### 6.4 Drive (6)

| Tool | Notes |
|---|---|
| `drive_search(account, query, max_results=10)` | Drive query syntax (e.g. `name contains 'foo'`). |
| `drive_get_file_metadata(account, file_id)` | id, name, mime, size, parents, modifiedTime, webViewLink. |
| `drive_read_file(account, file_id)` | Exports Google Docs→text, Sheets→CSV (first sheet only — Google's CSV export limitation), Slides→text. Binary files returned as base64 with mime. |
| `drive_upload_file(account, name, content, mime_type, parent_folder_id?)` | `content` is text or base64-encoded bytes. |
| `drive_update_file(account, file_id, content?, name?)` | Either or both. |
| `drive_delete_file(account, file_id)` | Permanent delete (Drive has its own trash; we skip the indirection). |

### 6.5 Token-budget estimate

~17 tools × ~190 tokens average ≈ **~3.2k tokens** of tool schema loaded per
conversation. Within an acceptable range for Claude Desktop and cached by
prompt caching after turn 1.

## 7. Account routing and credentials

`AccountStore` (in `accounts.py`) is the single boundary between disk state
and the Google client libraries:

```python
class AccountStore:
    def list(self) -> list[AccountInfo]: ...
    def credentials(self, label: str) -> google.oauth2.credentials.Credentials: ...
    def save(self, label: str, creds: Credentials, email: str) -> None: ...
```

- `credentials(label)` raises `AccountNotConfigured(label)` if no file exists.
- The returned `Credentials` object is configured with the client_secret so
  the library refreshes automatically on use; a callback writes the new access
  token back via `save()` whenever a refresh happens.
- If the refresh token is rejected (revoked, scope changed, expired in
  "Testing" mode after 7d), the call raises `AccountNeedsReauth(label)`.

## 8. Data flow (per tool call)

1. Claude Desktop calls the tool over stdio.
2. The tool function calls `store.credentials(account)`.
3. Tool builds a Google service: `build("gmail", "v1", credentials=creds, cache_discovery=False)`.
4. Tool calls the Google API, catching `HttpError`.
5. Response is passed through a shaping helper (e.g. `shape_message_summary`)
   to produce compact JSON.
6. Result returned to the MCP runtime.

## 9. Error handling

All errors propagate to the agent as tool-call errors with actionable messages.
No silent fallbacks, no retries in v1.

| Condition | Surfaced as |
|---|---|
| Unknown `account` label | `"Account 'work' not configured. Run: multi-google-mcp-auth add work"` |
| Refresh token rejected | `"Account 'work' needs reauthentication. Run: multi-google-mcp-auth add work"` |
| `client_secret.json` missing | `"OAuth client not configured. See README §Setup."` |
| Google `HttpError` | `{"status": 403, "reason": "forbidden", "message": "..."}` verbatim |
| Validation error (bad RFC3339 time, missing required arg) | Returned by MCP schema validation before the tool runs |

## 10. Response shaping

Tools never return raw Google payloads. Each tool has a small `shape_*`
helper that picks out the fields an LLM agent needs, with predictable
names. Examples:

- Gmail message summary: `{id, thread_id, from, to, cc, subject, snippet, date, labels}`
- Gmail full message: summary + `{body_text, body_html?, attachments: [{filename, mime, size, attachment_id}]}`
- Calendar event: `{id, summary, description?, start, end, location?, attendees?, status, html_link}`
- Drive file metadata: `{id, name, mime, size, parents, modified_time, web_view_link}`

This is the single biggest lever for keeping per-call token cost down.

## 11. Testing

### 11.1 Unit tests (always-on)

- `test_accounts.py` — AccountStore load/save/refresh round-trips with mocked `Credentials`.
- `test_shaping.py` — shaping helpers (Gmail header parsing, mime mapping, RFC3339 handling).
- `test_tools_<surface>.py` — each tool exercised against a `unittest.mock` Google service.

Run on every change. No network, no credentials, deterministic.

### 11.2 End-to-end smoke (opt-in, Levels 1+2)

`scripts/e2e_smoke.py` — single script, runs the full stack against a real
Google test account. Opt-in via env var:

```
MCP_E2E_ACCOUNT=test-account python scripts/e2e_smoke.py
```

**Level 1 — Real Google API round-trips.** Each surface:

- Gmail: send self-email with unique subject → search for it → trash it.
- Calendar: create event in a far-future slot → fetch it → delete it.
- Drive: upload tiny text file → read it back → delete it.

Idempotent — every artifact has a unique tag and is cleaned up before exit,
including on partial failure (try/finally).

**Level 2 — MCP transport round-trip.** Instead of calling tool functions
directly, the script spawns the actual server process and drives it through
the MCP Python client over stdio. Verifies tool registration, schema
validation, and stdio framing alongside the Google calls.

Runs in ~30 seconds. Documented in README under "Verifying your setup."

## 12. README structure (for handoff to another human)

The README is part of the deliverable. Sections:

1. What this is
2. Prerequisites (Python 3.11+, `uv`)
3. GCP setup (step-by-step, with screenshots-or-equivalent prose for each
   GCP console screen — project, API enablement, consent screen, test users,
   OAuth client creation, downloading `client_secret.json`)
4. Install (`uv tool install .` or equivalent)
5. Add your first account (`multi-google-mcp-auth add personal`)
6. Wire into Claude Desktop (sample `claude_desktop_config.json` entry)
7. Verifying your setup (run the E2E smoke against a test account)
8. Adding more accounts
9. Removing / rotating accounts
10. Troubleshooting (common OAuth errors, "needs reauthentication", scope
    expansion requiring re-consent)

## 13. Out of scope for v1 (intentional)

- Permanent Gmail delete (use trash)
- Drive folder creation as a dedicated tool (rare; can be done via
  `drive_upload_file` with `application/vnd.google-apps.folder`)
- Gmail drafts (agent can simply send when ready)
- Gmail `list_labels` (agent can infer labels from message responses)
- Calendar free/busy aggregation (agent can compute from `calendar_list_events`)
- Gmail thread fetch (agent can pull messages individually from a search)
- Background sync / local search index
- Multiple OAuth clients per account
- Service-account or domain-wide-delegation auth
