# Agent-driven install runbooks — Design

> **Canonical source:** the implementation that shipped lives in
> `agents/install/claude-desktop.md` and `agents/install/codex.md`. This
> spec captures the design as discussed during brainstorming. Where the
> shipped runbooks differ from this doc (e.g., the absolute-path command
> resolution and refresh-token redact patterns added during code review),
> the runbooks are authoritative.

**Date:** 2026-05-19
**Status:** Draft, pending user review
**Target audience:** Non-technical end-users running an AI agent (Claude
Desktop or Codex CLI) inside a local clone of this repo, who want the agent
to install and configure the server for them end-to-end.

---

## 1. Goal

Add per-harness, agent-targeted install runbooks so an AI agent can walk a
non-technical user through the full installation of `multi-google-mcp` —
including Google Cloud project setup, OAuth client creation, local CLI
install, account authentication, and editing the harness's settings file —
with patient, hand-holding pacing and clean exit ramps if the user can't
finish in one sitting.

Priority order for harness coverage:

1. **Claude Desktop** — first-priority, fully smoke-tested in this PR.
2. **Codex CLI** — second-priority, fully smoke-tested in this PR.
3. **OpenClaw / Hermes / others** — explicitly out of scope here. Follow-up
   PRs add them later under the same `agents/install/` directory and the
   same phase structure established by this PR.

## 2. Non-goals

- No new automation script (no `scripts/install.py`, no `install.sh`). The
  runbook *is* the automation surface; the agent executes shell commands and
  file edits directly.
- No changes to existing server code, tool behavior, or CLI commands.
- No removal of the existing manual "Wire into Claude Desktop" section in
  the README — it stays for users who prefer a manual path.
- No support for harnesses beyond Claude Desktop and Codex in this PR.
- No automated test for the markdown content. Verification is by reviewer
  read-through plus end-to-end smoke test against a real installation.

## 3. Audience and tone

The runbooks are written for **agents reading them in-conversation**, not
for humans reading them top-to-bottom. The agent reads the runbook, then
talks to the user in short, patient, supportive messages. Both runbooks
share the same tone & pacing principles:

- **One step at a time.** Never dump a multi-step block on the user. Each
  micro-step is its own user-facing message that ends with a clear
  checkpoint ("let me know when you've clicked Enable" or "paste back the
  URL when the consent page loads").
- **Reassurance after every checkpoint.** When the user reports success,
  acknowledge it ("Great — the project is created. Next step is enabling
  the Gmail API.") before moving forward.
- **Offer to back up.** If the user sounds lost, the agent offers to repeat
  the last instruction or restart the current phase. Never assume the user
  understood.
- **No jargon unless defined.** First use of "OAuth consent screen" or
  "client ID" gets a one-sentence plain-English explanation in parentheses.
- **Never claim done without proof.** Either the user explicitly confirms
  OR the agent verifies state via a command (e.g., `ls` for a file,
  `jq` for JSON shape).

## 4. File layout

This PR adds two new files and modifies the README:

```
agents/
└── install/
    ├── claude-desktop.md     # NEW — Claude Desktop runbook
    └── codex.md              # NEW — Codex CLI runbook

README.md                     # MODIFIED — adds "Quick install" pointer
                              # section, wraps existing install content
                              # under "Manual install" heading
```

The `agents/install/` directory signals "agent-facing docs, not human
runbook." When OpenClaw/Hermes runbooks ship later, they land here too
(`agents/install/openclaw.md`, `agents/install/hermes.md`).

## 5. README changes

The README currently has these sections in order: Prerequisites, GCP setup,
Install, Add your first account, Wire into Claude Desktop, Verifying your
setup, Adding scopes or new accounts later, Troubleshooting, Project
layout.

After this PR, the structure becomes:

1. Prerequisites (unchanged)
2. **NEW: Quick install (let an agent do it)** — points at the per-harness
   runbooks under `agents/install/` and explains in one short paragraph what
   to ask the agent.
3. **NEW heading: Manual install** — parent heading wrapping the existing
   GCP setup → Install → Add your first account → Wire into Claude Desktop
   subsections, unchanged in content.
4. Verifying your setup (unchanged)
5. Adding scopes or new accounts later (unchanged)
6. Troubleshooting (unchanged)
7. Project layout (unchanged)

## 6. Runbook structure (shared between both harnesses)

Both `agents/install/claude-desktop.md` and `agents/install/codex.md` follow
the same 7-phase linear structure. The agent reads start-to-end and
executes each phase in order. Each phase has the same five blocks.

### 6.1 Phase skeleton

| Phase | Purpose |
|---|---|
| **0. Preflight** | Detect prior state so the agent can resume mid-flow instead of starting from scratch on a rerun. |
| **1. GCP setup** | Walk the user through console.cloud.google.com to create the project, enable the three APIs, configure OAuth consent, create the OAuth client, and place `client_secret.json` at the expected path. |
| **2. Install `uv`** | Ensure `uv` is on PATH. If missing, give the user the official Astral install one-liner and confirm it landed. |
| **3. Install the CLI** | Run `uv tool install .` from the repo, confirm `multi-google-mcp` and `multi-google-mcp-auth` are on PATH. |
| **4. Add first account** | Run `multi-google-mcp-auth add <label>`, walk the user through the browser consent flow, verify the token file appeared. |
| **5. Wire into harness config** | Edit the harness's settings file (Claude Desktop JSON / Codex TOML). Read existing config, merge the new entry (do not clobber other servers), write back. |
| **6. Verify & restart** | Tell the user to fully quit and reopen the harness. Suggest a smoke-test prompt to run from inside it. |

### 6.2 Per-phase block structure

Inside each phase, the runbook provides five named blocks:

1. **Detection** — exact shell commands the agent runs to determine
   "already done" vs "needs doing." Idempotency lives here.
2. **Commands** — the literal shell commands or file-edit specs the agent
   executes to do the work. No improvisation allowed; the agent uses what's
   in the runbook verbatim.
3. **User-facing template** — the plain-language message the agent says to
   the user at each checkpoint inside this phase. Written for a non-technical
   reader. The agent paraphrases freely but stays faithful to the meaning.
4. **Failure** — what the agent does if detection or a command fails: how
   to diagnose, when to retry, when to escalate to the user.
5. **Exit ramp** — how the user can pause this phase and resume later. The
   agent records (in conversation) where the user stopped and tells them
   how to come back.

## 7. Phase 0 — Preflight

Identical detection logic in both runbooks (Claude Desktop and Codex differ
only in which harness-config check they add at the end).

**Detection commands the agent runs in parallel:**

```bash
# GCP credentials
test -f ~/.config/multi-google-mcp/client_secret.json && \
  jq -e '.installed.client_id' ~/.config/multi-google-mcp/client_secret.json >/dev/null

# uv on PATH
command -v uv

# multi-google-mcp CLI installed
command -v multi-google-mcp && command -v multi-google-mcp-auth

# At least one account configured
ls ~/.config/multi-google-mcp/accounts/*.json 2>/dev/null | head -1

# Harness config present (per-harness — Claude Desktop example)
test -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Server already wired into harness config (per-harness — Claude Desktop example)
jq -e '.mcpServers["multi-google"]' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
  2>/dev/null
```

**Agent decision logic:** for each check, the agent reports the result and
decides the entry phase. If all six are green, skip straight to Phase 6
(verify & restart). If only the harness-wiring check is red, jump to Phase
5. And so on.

**User-facing template:** "Let me take a quick look at what's already set
up on your machine… [1-line summary per check]. Based on that, I'll start
at Phase N — [name]. Sound good?"

**Exit ramp:** Preflight has no exit ramp. It's read-only detection.

## 8. Phase 1 — GCP setup (interactive walkthrough)

This is the longest and most user-facing phase. It's broken into nine
sub-phases, each with its own checkpoint. The agent does **one sub-phase
per turn** — never batches.

### 8.1 Sub-phase table

| Sub-phase | Agent action | Verification |
|---|---|---|
| **1a. Open console** | On macOS: `open https://console.cloud.google.com`. On Linux/WSL: print the URL and ask the user to open it. | User reports they're signed in. |
| **1b. Create project** | Instruct user: project picker (top-left) → New Project → name "multi-google-mcp" → Create. | User confirms the project name shows in the top bar. |
| **1c. Enable Gmail API** | `open https://console.cloud.google.com/apis/library/gmail.googleapis.com` (deep-link). Instruct: click blue Enable button. | User confirms the page now says "API Enabled" (or the agent's deep-link to the dashboard returns enabled state). |
| **1d. Enable Calendar API** | `open https://console.cloud.google.com/apis/library/calendar-json.googleapis.com` | Same as 1c. |
| **1e. Enable Drive API** | `open https://console.cloud.google.com/apis/library/drive.googleapis.com` | Same as 1c. |
| **1f. OAuth consent screen** | `open https://console.cloud.google.com/apis/credentials/consent`. Walk through: User type = External → Create → fill App name, support email, dev contact → Save and continue (scopes screen) → Save and continue → Test users: add the user's own Gmail → Save and continue → Back to dashboard. | User confirms publishing status shows "Testing." |
| **1g. Create OAuth client** | `open https://console.cloud.google.com/apis/credentials`. Instruct: Create credentials → OAuth client ID → Application type: Desktop app → Name it → Create → Download JSON. | User says they downloaded the file. |
| **1h. Locate and confirm the downloaded file** | Agent enumerates candidate files with `ls -lt ~/Downloads/client_secret_*.json 2>/dev/null` (newest first, includes mtime). Then routes per §8.1.1 — NEVER blind-globs into a `mv` command. | One specific file path is confirmed with the user. |
| **1i. Move and verify** | With the path confirmed in 1h, agent runs (with the literal confirmed path, no glob): `mkdir -p ~/.config/multi-google-mcp && mv "<CONFIRMED_PATH>" ~/.config/multi-google-mcp/client_secret.json`. | `ls ~/.config/multi-google-mcp/client_secret.json` succeeds AND `jq -e '.installed.client_id' ~/.config/multi-google-mcp/client_secret.json` returns a non-empty string. |

### 8.1.1 Sub-phase 1h decision tree — multi-match safety

A user who has worked with GCP before may have multiple `client_secret_*.json`
files already sitting in `~/Downloads/`. A blind glob (`mv ~/Downloads/client_secret_*.json …`)
fails noisily on multiple matches and, worse, may silently pick the wrong
file on shells that expand to alphabetical order. The agent MUST handle
each match-count case explicitly:

- **Zero matches** — Agent says: *"I don't see a file matching `client_secret_*.json`
  in your Downloads folder. A few possibilities — (a) the browser saved it
  somewhere else (Desktop? a project folder?); (b) the download was renamed
  to something else; (c) the download hasn't finished. Could you tell me
  where the file ended up? I just need the full path."* Then loops back
  with the user-provided path, validates the file exists and parses as
  JSON, and proceeds to 1i.

- **Exactly one match** — Agent says: *"I see one matching file: `<path>`
  (downloaded `<mtime>`). Is this the OAuth client you just created?"*
  Wait for explicit yes/no. On yes → proceed to 1i with that path. On no →
  ask user for the actual path and validate as in the zero-matches case.

- **Multiple matches** — Agent says: *"I found `<N>` files in Downloads
  matching `client_secret_*.json`:"* (lists each with its mtime in
  newest-first order) *"Which one did we just create? Reply with the
  filename, or say 'newest' if you'd like me to use the top one."*
  - If user says "newest" or names the top file → proceed to 1i with that
    path.
  - If user names a different file → proceed to 1i with that path.
  - If user is unsure → agent suggests they re-download from GCP
    Credentials (one fresh download disambiguates everything), then re-runs
    1h on the new file.

In all paths, the agent validates the chosen path with
`jq -e '.installed.client_id' "<chosen-path>"` BEFORE running the `mv`.
A file that doesn't parse as the expected OAuth-client JSON shape is a
hard stop: agent reports the mismatch to the user and re-enters 1h's
decision tree.

### 8.2 GCP-specific exit ramp

If the user says any variant of "I can't do this right now," "let me come
back to this," "I'll finish later," or sounds stuck for more than one
back-and-forth, the agent:

1. Tells them which sub-phase they stopped at (e.g., "You stopped after
   creating the project but before enabling the Gmail API — that's sub-phase
   1c.").
2. Tells them how to resume: "When you're ready, just open this conversation
   again and say 'I'm back — left off at sub-phase 1c' and I'll pick up
   from there."
3. Exits the runbook. Does not attempt Phases 2-6. They depend on GCP
   credentials being present.

### 8.3 Things the agent must NOT do in Phase 1

- Do **not** invent any console.google.com URL. Use only the deep-link URLs
  listed in the runbook's commands block.
- Do **not** claim a sub-phase succeeded without explicit user confirmation
  OR an objective state check (the `jq` verification in 1i).
- Do **not** attempt to log into the user's Google account or use any
  browser-automation tooling. The runbook is strictly conversational at
  this phase.
- Do **not** advance from sub-phase 1i to Phase 2 if `jq` verification
  fails. Stop and ask the user to confirm what they downloaded.
- Do **not** use a globbed path (`client_secret_*.json`) as the source
  argument to `mv` in sub-phase 1i. Always pass the literal file path
  confirmed during the 1h decision tree. See §8.1.1 for the reasoning.

## 9. Phase 2 — Install `uv`

**Detection:** `command -v uv`. If present, skip phase entirely.

**Commands:** If missing, the agent shows the user the official Astral
install one-liner from <https://docs.astral.sh/uv/getting-started/installation/>
and asks them to run it themselves (rather than running it as the agent —
shell installers writing to user `$HOME` should be visible to the user).
Re-runs detection after the user confirms.

**User-facing template:** "I don't see `uv` installed yet. `uv` is the
Python package manager this server uses. Could you paste this command into
your terminal? `curl -LsSf https://astral.sh/uv/install.sh | sh` — then let
me know when it's done so I can confirm it landed."

**Failure:** If detection still fails after the user confirms, ask them to
share the install output. Common cause: shell didn't pick up the new
PATH — instruct user to open a new terminal or run `source ~/.zshrc`.

**Exit ramp:** None — this is a one-command phase.

## 10. Phase 3 — Install the CLI

**Detection:** `command -v multi-google-mcp && command -v multi-google-mcp-auth`.

**Commands:** Agent runs `uv tool install .` from `$(git rev-parse --show-toplevel)`.

**User-facing template:** "Now I'm going to install the server's CLI from
this repo. It puts two commands on your PATH: `multi-google-mcp` (the
server) and `multi-google-mcp-auth` (account manager). Running it now…"

**Failure:** If `uv tool install .` errors, the agent surfaces the full
error to the user (most likely Python version mismatch or network issue),
suggests `python3 --version` to check ≥3.11, and pauses for direction.

**Exit ramp:** None.

## 11. Phase 4 — Add first account

**Detection:** Any `~/.config/multi-google-mcp/accounts/*.json` exists.

**Commands:** Agent asks user for a label, defaulting to `personal`, then
runs `multi-google-mcp-auth add <label>`. This opens a browser for OAuth
consent.

**User-facing template:** "Time to connect your first Google account. I'll
ask `multi-google-mcp-auth` to start the connection flow — a browser
window will pop up asking you to sign in and grant access. What label
should I use for this account? (Suggestion: `personal`.)"

After the command launches: "A browser window should be opening. Sign in
with the account you added as a test user during the consent screen setup
(sub-phase 1f). After you click Allow, the browser tab should say
'Authentication complete.' Let me know when you see that."

**Verification:** `test -f ~/.config/multi-google-mcp/accounts/<label>.json`
plus `jq -e '.refresh_token != null' ~/.config/multi-google-mcp/accounts/<label>.json >/dev/null`.
The boolean predicate plus the `>/dev/null` redirect is load-bearing — running
`jq -e '.refresh_token' <path>` without redirection prints the live OAuth
refresh token to stdout, which is captured by the agent's conversation
transcript. The runbook explicitly forbids the unredirected form.

**Failure:** If the browser hangs on `localhost:<port>` — possible firewall
or VPN interception. Tell the user, suggest disabling VPN temporarily and
re-running `multi-google-mcp-auth add <label>`.

**Exit ramp:** Auth phase can be deferred — Phase 5 can proceed without
an account, the server just won't have anything to call until they add
one. If user wants to defer: agent tells them to run
`multi-google-mcp-auth add <label>` when ready, then skips to Phase 5.

## 12. Phase 5 — Wire into harness config

This phase is the one that differs structurally between Claude Desktop and
Codex. Both follow read-merge-write logic; only the file path, format, and
schema differ.

### 12.1 Claude Desktop variant

**Path:** `$HOME/Library/Application Support/Claude/claude_desktop_config.json`
(macOS). The runbook documents the Windows/Linux paths but flags this PR
ships macOS-tested behavior only.

**Format:** JSON.

**Schema for the new entry (`<MGM_BIN>` is the absolute path resolved at
write time from `command -v multi-google-mcp` — typically
`/Users/<you>/.local/bin/multi-google-mcp` after `uv tool install`):**

```json
{
  "mcpServers": {
    "multi-google": {
      "command": "<MGM_BIN>"
    }
  }
}
```

**Why an absolute path?** Claude Desktop is a GUI app. Launched from
Finder, Dock, or Spotlight it inherits `launchd`'s minimal PATH
(`/usr/bin:/bin:/usr/sbin:/sbin`) — not the shell PATH that contains
`~/.local/bin`. A bare-name `"command": "multi-google-mcp"` works from a
terminal-launched session but fails silently when Claude Desktop is opened
normally. The runbook resolves the absolute path at write time.

**Read-merge-write:**

1. Resolve `MGM_BIN="$(command -v multi-google-mcp)"`. Bail if empty.
2. Read existing config. If file doesn't exist, treat as `{}`.
3. Validate it parses as JSON. If parse fails, stop and surface the error
   — do not overwrite a malformed config.
4. Merge: set `.mcpServers["multi-google"] = { command: "$MGM_BIN" }`.
5. Preserve all other top-level keys and existing `mcpServers` entries.
6. Write back with 2-space indentation.

**Verification:** `jq -r '.mcpServers["multi-google"].command' <path>`
returns a non-empty path, AND `[ -x "<that-path>" ]` succeeds — confirms
both that the entry was written and that the stored command points at an
executable file.

### 12.2 Codex variant

**Path:** `~/.codex/config.toml`.

**Format:** TOML. Codex's MCP config uses `[mcp_servers.<name>]` sections.

**Schema for the new entry (TOML — `<MGM_BIN>` is the absolute path
resolved from `command -v multi-google-mcp`, same rationale as the Claude
Desktop variant):**

```toml
[mcp_servers.multi-google]
command = "<MGM_BIN>"
```

**Read-merge-write:**

1. Resolve `MGM_BIN="$(command -v multi-google-mcp)"`. Bail if empty.
2. Read existing config. If file doesn't exist, treat as empty.
3. Check whether a `[mcp_servers.multi-google]` section already exists.
   - If yes AND the stored command is already executable: leave alone.
   - If yes BUT the stored command is stale (bare name from a pre-runbook
     install, or a no-longer-existent path): rewrite that section in place
     via an awk pass that preserves blank lines and other sections.
4. If no: append the new section to the end of the file with a leading
   blank line for separation.
5. Preserve all other sections unmodified.

**Verification:** `grep -q '^\[mcp_servers\.multi-google\]' ~/.codex/config.toml`,
extract the command back out via `sed -n 's/^command = "\(.*\)"$/\1/p'`,
and require `[ -x "$STORED_CMD" ]`.

Codex itself reads `config.toml` on launch; no other validation needed
beyond verifying the file is still well-formed TOML afterwards (`codex` is
not invoked at this phase — only at verify time in Phase 6).

### 12.3 Shared safety rules for Phase 5

- **Never use `>` redirection to write the config file** — that clobbers
  the entire file. Always read → modify in memory → write back atomically.
- **Always make a backup before writing.** Agent runs `cp <path>
  <path>.bak.<timestamp>` immediately before the write. On failure, tell
  user where the backup is.
- **Never strip existing entries.** If the user already has other MCP
  servers configured, they must survive untouched.

## 13. Phase 6 — Verify & restart

**Detection:** None — this is the closing phase, always runs.

**Commands:** None on the shell side. Agent gives the user verification
instructions for their harness.

**User-facing template (Claude Desktop):** "We're done with the install
side. To activate the server, fully quit Claude Desktop (Cmd+Q, not just
closing the window) and reopen it. Then try asking it: *'Use multi-google
to search my personal Gmail for unread messages from this week.'* If it
calls the `gmail_search` tool, you're good. Let me know what happens."

**User-facing template (Codex):** "We're done with the install side. Open
a new terminal, run `codex` (or start a new session), and try: *'Use
multi-google to search my personal Gmail for unread messages from this
week.'* If it calls the `gmail_search` tool, you're good. Let me know
what happens."

**Failure:** If the user reports the server isn't listed or tools don't
appear: agent walks them through `multi-google-mcp` running manually from
the terminal as a smoke test (`multi-google-mcp` should boot and wait on
stdin; Ctrl-C to exit), confirming the binary works in isolation.

**Exit ramp:** None — Phase 6 is the success terminus.

## 14. Verification plan for this PR

This is documentation, but it's *executable* documentation — the agent
runs commands while reading it. So verification means actually following
each runbook end-to-end on this machine.

**Manual review pass (reviewer + Aria):**

- Every deep-link URL resolves to the right console page.
- Every shell command in commands blocks works as written, no fabricated
  flags.
- Per-harness paths (`~/Library/Application Support/Claude/claude_desktop_config.json`
  and `~/.codex/config.toml`) match what the harness actually reads.
- For each phase, the detection block actually distinguishes "done" from
  "not done" — a reviewer reads each block and asks: "if I restart at this
  phase, will the agent correctly skip what's done?"

**End-to-end smoke test (developer machine):**

- Claude Desktop: full run with a fresh-ish GCP project (or skipping GCP if
  already done), confirming Phase 5 produces a valid `claude_desktop_config.json`
  edit and Phase 6 verification works after a Claude Desktop relaunch.
- Codex: same — full run with the existing Codex install, confirming
  Phase 5 writes a valid `~/.codex/config.toml` section and Codex picks up
  the new MCP server.

**Automated test changes:** None. Existing `pytest` / `ruff` / `mypy` runs
on Phase 3 of `/code-task` should pass unchanged because no Python is
touched.

**Per `/code-task` Phase 2.6:** Docs-only commits must call out the absence
of new tests in the commit body. Implementation plan will reflect this.

## 15. Open questions / deferred decisions

- **Windows / Linux paths for Claude Desktop.** Documented in the runbook
  but not smoke-tested in this PR. The runbook explicitly flags this for
  the user ("Tested on macOS — Windows/Linux paths shown but please report
  issues").
- **OpenClaw / Hermes runbooks.** Out of scope for this PR. Same structure
  will apply, just different Phase 5 implementations.
- **Account-add scope changes.** The runbook does not currently cover the
  case where `multi-google-mcp` has been upgraded and SCOPES changed —
  existing README "Adding scopes or new accounts later" section handles it
  for now.
