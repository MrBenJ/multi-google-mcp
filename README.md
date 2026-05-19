# multi-google-mcp

A local **Model Context Protocol** server that gives Claude Desktop (or any
stdio MCP client) access to multiple Google accounts. Each tool call takes
an explicit `account` label so the agent can operate across accounts in the
same conversation.

**Scope:**
- Gmail: search, read, send, modify labels (incl. trash)
- Google Calendar: list, read, create, update, delete events
- Google Drive: search, read, upload, update, delete files

**Designed for personal local use** on a single machine. Tokens live under
`~/.config/multi-google-mcp/`. Not for hosting or sharing.

---

## Prerequisites

- macOS, Linux, or WSL
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pipx`
- A Google account with admin access to a GCP project (free tier is fine)

---

## Quick install (let an agent do it)

If you have an AI agent running this repo locally (Claude Desktop, Codex CLI,
etc.), you can ask it to install this server for you end-to-end — including
the Google Cloud setup. Just tell your agent:

> "Install this server. The runbook is in `agents/install/`."

It will pick the right runbook for your harness and walk you through every
step, including Google Cloud project setup if you haven't done it yet.

Currently supported harnesses:

- **Claude Desktop** — [`agents/install/claude-desktop.md`](agents/install/claude-desktop.md)
- **Codex CLI** — [`agents/install/codex.md`](agents/install/codex.md)

For manual setup, see the "Manual install" section below.

---

## Manual install

### GCP setup (one-time)

Hand these steps to anyone using this server for the first time.

### 1. Create a GCP project

1. Open https://console.cloud.google.com
2. Project picker → **New Project** → name it (e.g. "multi-google-mcp")
3. Wait for the project to be created and select it

### 2. Enable the three APIs

In the project, go to **APIs & Services → Library** and search/enable each:

- **Gmail API**
- **Google Calendar API**
- **Google Drive API**

### 3. Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen**
2. User type: **External**, then **Create**
3. App information:
   - App name: `multi-google-mcp` (anything is fine)
   - User support email: your email
   - Developer contact: your email
4. **Save and continue**
5. Scopes screen: click **Save and continue** (we'll request scopes from the app, not here)
6. Test users: **Add users** — add every Gmail address you intend to connect.
   In **Testing** publishing status, only these emails can authenticate.
7. **Save and continue → Back to dashboard**

> Keep publishing status as **Testing**. For personal use this is fine.
> One quirk: in Testing mode Google sometimes expires refresh tokens
> after 7 days unless the consenting account is also a test user — which
> we just added, so you're covered.

### 4. Create the OAuth client

1. **APIs & Services → Credentials**
2. **Create credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `multi-google-mcp` (anything is fine)
5. **Create**
6. **Download JSON** (the small download icon next to your client)
7. Move that file to:
   ```
   ~/.config/multi-google-mcp/client_secret.json
   ```
   Create the directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/multi-google-mcp
   ```

---

### Install

```bash
# from a clone of this repo
uv tool install .
```

This puts two commands on your `PATH`:

- `multi-google-mcp` — the MCP server (started by Claude Desktop)
- `multi-google-mcp-auth` — manage local OAuth tokens

### Add your first account

```bash
multi-google-mcp-auth add personal
```

A browser window opens. Sign in, accept the scopes. The CLI writes
`~/.config/multi-google-mcp/accounts/personal.json`.

To add another account use a different label:

```bash
multi-google-mcp-auth add work
```

List configured accounts:

```bash
multi-google-mcp-auth list
```

Remove an account:

```bash
multi-google-mcp-auth remove personal
```

### Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and
add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "multi-google": {
      "command": "multi-google-mcp"
    }
  }
}
```

Restart Claude Desktop. You should see the tools listed; ask Claude
something like:

> "Search my work Gmail for unread mail from yesterday."

Claude will call `gmail_search` with `account="work"`.

## Verifying your setup

Add a dedicated test account (e.g. a throwaway Gmail) and run the
end-to-end smoke script. It boots the actual MCP server as a subprocess,
drives every tool surface over stdio against real Google APIs, and cleans
up after itself.

```bash
multi-google-mcp-auth add test-account
MCP_E2E_ACCOUNT=test-account uv run python scripts/e2e_smoke.py
```

Takes ~30 seconds. If everything passes, your local setup is good.

## Adding scopes or new accounts later

- **New account:** rerun `multi-google-mcp-auth add <label>`.
- **Changed scopes:** edit `SCOPES` in `src/multi_google_mcp/config.py`,
  rerun `multi-google-mcp-auth add <label>` for each account — Google
  requires re-consent when scopes change.

## Troubleshooting

| Error | What it means | Fix |
|---|---|---|
| `Account 'work' not configured` | No token file for that label | `multi-google-mcp-auth add work` |
| `Account 'work' needs reauthentication` | Refresh token rejected (revoked, scope changed, or 7d test-mode expiry) | `multi-google-mcp-auth add work` |
| `OAuth client not configured` | `~/.config/multi-google-mcp/client_secret.json` missing | Re-download from GCP Credentials |
| Google `403: insufficient permissions` | Scope wasn't requested or wasn't granted | Add the scope in `config.py`, re-auth |
| Browser hangs on `localhost:<port>` after consent | Local callback failed | Re-run `add`; firewall/VPN may be intercepting localhost |

## Project layout

See [`docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md`](docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md)
and [`docs/superpowers/plans/2026-05-18-multi-google-mcp.md`](docs/superpowers/plans/2026-05-18-multi-google-mcp.md)
for the design and step-by-step implementation history.
