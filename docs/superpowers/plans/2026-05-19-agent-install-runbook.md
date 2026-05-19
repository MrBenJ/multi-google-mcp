# Agent-driven install runbooks — Implementation Plan

> **Canonical source:** the implementation that shipped lives in
> `agents/install/claude-desktop.md` and `agents/install/codex.md`. This
> plan captures the task decomposition as originally drafted. The shipped
> runbooks evolved during implementation per code review feedback (refresh-
> token redaction, absolute-path command resolution in harness configs).
> Where examples in this plan still echo earlier patterns, treat the
> runbooks as authoritative.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `agents/install/claude-desktop.md` and `agents/install/codex.md` — agent-targeted install runbooks that walk a non-technical user through end-to-end setup (GCP, uv, CLI install, account auth, harness config wiring). Modify README to point users at the new runbooks while preserving the existing manual instructions.

**Architecture:** Two self-contained per-harness markdown files following the 7-phase structure from the spec (§6.1). Both share Phases 0-4 and 6 by design; Phase 5 differs (Claude Desktop = JSON merge at `~/Library/Application Support/Claude/claude_desktop_config.json`; Codex = TOML append at `~/.codex/config.toml`). README gets a new "Quick install" pointer section above an existing-content "Manual install" parent.

**Tech Stack:** Markdown only. The runbooks describe shell commands and harness-config file shapes — the actual code paths exist already (`uv tool install .`, `multi-google-mcp-auth add`, etc.).

---

## File Structure

**New files:**
- `agents/install/claude-desktop.md` — Claude Desktop runbook, ~7 phase sections.
- `agents/install/codex.md` — Codex CLI runbook, mirrors claude-desktop.md except Phase 5.

**Modified files:**
- `README.md` — adds a "Quick install (let an agent do it)" section after Prerequisites, demotes the existing GCP/Install/Wire/Add-account headings under a new "Manual install" H2 parent.

**Out of scope this PR (deferred to follow-ups):**
- `agents/install/openclaw.md`, `agents/install/hermes.md`.

---

## Task verification reference

**Repo paths used across tasks:**
- Repo root: `/Users/bjunya/code/multi-google-mcp`
- Claude Desktop config: `$HOME/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
- Codex config: `$HOME/.codex/config.toml`
- Client secret target: `~/.config/multi-google-mcp/client_secret.json`
- Account tokens dir: `~/.config/multi-google-mcp/accounts/`

**TDD applicability:** Per `/code-task` Phase 2.6 — this is documentation-only work. No new tests. Each commit body explicitly calls out "No test added — documentation-only change." Existing `pytest` / `ruff` / `mypy` runs in `/code-task` Phase 3 must still pass.

**Verification per task:** Each task ends with a "verification" step that confirms either (a) the file content reads correctly when re-opened, or (b) shell commands cited in that section actually execute cleanly when run by hand.

---

## Task 1: Scaffold `agents/install/` and write Claude Desktop runbook header + Phase 0

**Files:**
- Create: `agents/install/claude-desktop.md`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p /Users/bjunya/code/multi-google-mcp/agents/install
```

- [ ] **Step 2: Write the file header and Phase 0 (Preflight)**

Write `/Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md` with this content:

````markdown
# Install `multi-google-mcp` into Claude Desktop — Agent Runbook

> **Audience:** You are an AI agent (Claude Desktop, Claude Code, Cursor, etc.) running locally inside a clone of the `multi-google-mcp` repo. The human in front of you has asked you to install this server. Follow this runbook end-to-end. The user may have little to no experience with the command line, GCP, or JSON — treat them with patience.

## How to read this runbook

- Each phase has five named blocks: **Detection**, **Commands**, **User-facing template**, **Failure**, **Exit ramp**.
- Do **one phase at a time**. Inside phases with sub-phases (Phase 1), do **one sub-phase per turn**.
- Never claim a step succeeded without either explicit user confirmation OR an objective state check.
- Read everything in **Commands** literally — do not improvise URLs, paths, or shell flags.
- After every checkpoint the user confirms, acknowledge it briefly before moving on. Reassurance after every success.
- If the user sounds lost, stuck, or asks to back up: offer to repeat the last instruction or restart the current phase. Never push forward when the user is confused.

## Tone & pacing

- Short messages. One micro-step at a time.
- Plain English. First use of jargon ("OAuth consent screen", "client ID") gets a one-sentence explanation in parentheses.
- Patient and supportive. If the user has to retry something, that's fine — say so explicitly.
- Never claim done without proof.

---

## Phase 0 — Preflight

Detect what's already done so you can resume mid-flow instead of restarting from scratch on a rerun.

### Detection

Run all six checks (parallel is fine):

```bash
# 1. GCP credentials present and parseable
test -f ~/.config/multi-google-mcp/client_secret.json && \
  jq -e '.installed.client_id' ~/.config/multi-google-mcp/client_secret.json >/dev/null

# 2. uv on PATH
command -v uv

# 3. multi-google-mcp CLI installed
command -v multi-google-mcp && command -v multi-google-mcp-auth

# 4. At least one account configured
ls ~/.config/multi-google-mcp/accounts/*.json 2>/dev/null | head -1

# 5. Claude Desktop config file present
test -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# 6. multi-google server already wired into Claude Desktop config
jq -e '.mcpServers["multi-google"]' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
  2>/dev/null
```

### Commands

None — Phase 0 is read-only detection.

### User-facing template

> "Let me take a quick look at what's already set up on your machine — give me a moment.
>
> Here's what I found:
> - [✓/✗] Google Cloud credentials at `~/.config/multi-google-mcp/client_secret.json`
> - [✓/✗] `uv` installed
> - [✓/✗] `multi-google-mcp` CLI installed
> - [✓/✗] At least one Google account connected
> - [✓/✗] Claude Desktop config file present
> - [✓/✗] `multi-google` server already wired into Claude Desktop
>
> Based on that, I'll start at **Phase N — [name]**. The earlier phases are already done, so we can skip them. Sound good?"

### Decision logic (which phase to enter)

- All six green → Skip to Phase 6 (verify & restart). You're effectively done.
- Only check 6 red → Skip to Phase 5 (wire into config).
- Only checks 4 and 6 red → Skip to Phase 4 (add account).
- Only checks 3, 4, 6 red → Skip to Phase 3 (install CLI).
- Check 2 red → Phase 2 (install uv) onward.
- Check 1 red → Phase 1 (GCP setup) — this is the most common starting point.

If multiple checks are red, enter at the earliest red phase.

### Failure

If a detection command errors unexpectedly (e.g., `jq` not installed): tell the user, ask them to install `jq` first (`brew install jq` on macOS), then re-run Phase 0.

### Exit ramp

None — Phase 0 is read-only.
````

- [ ] **Step 3: Verify the file reads back correctly**

Run:
```bash
ls -la /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
grep -c '^## Phase 0' /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
```

Expected: file exists, grep returns `1`.

- [ ] **Step 4: Verify detection commands run cleanly on this machine**

Run each detection command from the file. They should all execute without syntax errors regardless of whether they succeed or fail (since we're testing whether the commands themselves are well-formed):

```bash
test -f ~/.config/multi-google-mcp/client_secret.json && jq -e '.installed.client_id' ~/.config/multi-google-mcp/client_secret.json >/dev/null; echo "exit: $?"
command -v uv >/dev/null; echo "exit: $?"
command -v multi-google-mcp >/dev/null && command -v multi-google-mcp-auth >/dev/null; echo "exit: $?"
ls ~/.config/multi-google-mcp/accounts/*.json 2>/dev/null | head -1; echo "exit: $?"
test -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json"; echo "exit: $?"
jq -e '.mcpServers["multi-google"]' "$HOME/Library/Application Support/Claude/claude_desktop_config.json" 2>/dev/null; echo "exit: $?"
```

Expected: each command prints an exit code (no `command not found` or shell parse errors).

- [ ] **Step 5: Commit**

```bash
git add agents/install/claude-desktop.md
git commit -m "$(cat <<'EOF'
docs: scaffold Claude Desktop install runbook with Phase 0

Adds agents/install/claude-desktop.md with header, tone guidance, and
the Phase 0 (Preflight) detection block. Subsequent phases land in
follow-up commits.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add Phase 1 (GCP setup) to Claude Desktop runbook

**Files:**
- Modify: `agents/install/claude-desktop.md` (append)

- [ ] **Step 1: Append Phase 1 content**

Append this content to the end of `agents/install/claude-desktop.md`:

````markdown
---

## Phase 1 — GCP setup (interactive walkthrough)

This is the longest and most user-facing phase. Walk the user through one **sub-phase per turn**. Never batch sub-phases. Acknowledge each completion before moving on.

If at any point the user wants to stop ("I'll come back to this later", "can we do this another time"), follow the **Exit ramp** at the bottom of this phase. The rest of the runbook (Phases 2-6) cannot proceed without GCP credentials in place, so the agent halts cleanly.

### Sub-phase 1a — Open the Google Cloud console

**Commands:**
```bash
# macOS:
open https://console.cloud.google.com
# Linux / WSL — print the URL and ask the user to open it themselves.
```

**User-facing template:**

> "First step: I'll open the Google Cloud Console in your browser. Sign in with the Google account that should own this project (you can use the same account you'll be connecting later, or a different admin account — either works). Let me know once you're signed in."

**Checkpoint:** User confirms they're signed in.

---

### Sub-phase 1b — Create a project

**User-facing template:**

> "Now we'll create a project. At the top of the page, find the **project picker** (it's the dropdown right next to the 'Google Cloud' logo). Click it, then click **New Project**.
>
> - **Project name:** `multi-google-mcp` (any name works, this is just a label)
> - **Organization / Location:** leave the defaults
>
> Click **Create**. It takes a few seconds — wait for the notification bell (top right) to say 'project created'. Then click that notification to switch into the new project.
>
> Let me know once you see `multi-google-mcp` in the top bar."

**Checkpoint:** User confirms the project name shows in the top bar.

---

### Sub-phase 1c — Enable Gmail API

**Commands:**
```bash
open https://console.cloud.google.com/apis/library/gmail.googleapis.com
```

**User-facing template:**

> "I'm opening the Gmail API page. Make sure the project bar at the top still says `multi-google-mcp`. Click the blue **Enable** button — it'll take a few seconds, then the page should say 'API Enabled' with a green check.
>
> Let me know when you see that."

**Checkpoint:** User confirms the page now says "API Enabled."

---

### Sub-phase 1d — Enable Calendar API

**Commands:**
```bash
open https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
```

**User-facing template:**

> "Same idea for the Calendar API. Click **Enable**. Tell me when it's done."

**Checkpoint:** User confirms "API Enabled" for Calendar.

---

### Sub-phase 1e — Enable Drive API

**Commands:**
```bash
open https://console.cloud.google.com/apis/library/drive.googleapis.com
```

**User-facing template:**

> "Last one — the Drive API. Click **Enable**, then tell me when it's done. After this, the three APIs we need are turned on."

**Checkpoint:** User confirms "API Enabled" for Drive.

---

### Sub-phase 1f — Configure OAuth consent screen

The OAuth consent screen is the page Google shows your users when they first connect their account. We're setting it up in "Testing" mode, which is the right setting for personal use.

**Commands:**
```bash
open https://console.cloud.google.com/apis/credentials/consent
```

**User-facing template:**

> "Now we configure the consent screen — that's the page Google shows when you first connect your account.
>
> Walk through these settings in order:
> 1. **User Type:** select **External**. Click **Create**.
> 2. **App information:**
>    - App name: `multi-google-mcp` (anything is fine)
>    - User support email: your email address (pick from dropdown)
>    - Developer contact information → email: same email
> 3. Click **Save and continue**.
> 4. On the **Scopes** screen, don't add anything. Just click **Save and continue**.
> 5. On the **Test users** screen, click **Add users** and type your own Gmail address (the same one you plan to connect to this server). Save it. Then **Save and continue**.
> 6. On the Summary screen, click **Back to dashboard**.
>
> You should now see 'Publishing status: Testing' in the dashboard. Let me know when you're there."

**Checkpoint:** User confirms "Publishing status: Testing."

---

### Sub-phase 1g — Create the OAuth client

**Commands:**
```bash
open https://console.cloud.google.com/apis/credentials
```

**User-facing template:**

> "Now we create the OAuth client itself — that's the credential the server uses to ask Google for access.
>
> On this page:
> 1. Click **+ Create credentials** (top of page) → **OAuth client ID**.
> 2. **Application type:** select **Desktop app**.
> 3. **Name:** `multi-google-mcp` (or whatever — this is just a label).
> 4. Click **Create**.
> 5. A dialog will pop up showing your client ID and secret. Click **Download JSON** (the small download icon).
> 6. The file will save to your Downloads folder. Don't rename it.
>
> Let me know once the file is downloaded."

**Checkpoint:** User confirms the file is downloaded.

---

### Sub-phase 1h — Locate and confirm the downloaded file

The downloaded file is typically named `client_secret_<long-id>.apps.googleusercontent.com.json` and lives in `~/Downloads/`. But the user may already have other `client_secret_*.json` files from prior GCP work, so do **not** blind-glob into a move command.

**Commands:**

```bash
# Enumerate candidates, newest first
ls -lt ~/Downloads/client_secret_*.json 2>/dev/null
```

**Decision tree based on match count:**

#### Zero matches

**User-facing template:**

> "I don't see a file matching `client_secret_*.json` in your Downloads folder. A few possibilities:
> - (a) The browser saved it somewhere else (Desktop? a project folder?)
> - (b) The download was renamed to something else
> - (c) The download hasn't finished yet
>
> Could you find the file and tell me its full path? Something like `/Users/yourname/Desktop/client_secret_foo.json` works."

When the user provides a path, validate:

```bash
test -f "<user-provided-path>" && jq -e '.installed.client_id' "<user-provided-path>" >/dev/null
```

If both pass, set `CONFIRMED_PATH=<user-provided-path>` and proceed to Sub-phase 1i.

If validation fails: tell the user the file doesn't look like an OAuth client JSON, and re-enter the decision tree from the top.

#### Exactly one match

**User-facing template:**

> "I see one matching file:
> `~/Downloads/<filename>` (downloaded `<mtime>`)
>
> Is this the OAuth client you just created? (yes/no)"

- On **yes**: set `CONFIRMED_PATH=~/Downloads/<filename>` and proceed to Sub-phase 1i.
- On **no**: ask user for the actual path. Validate as in the zero-matches case.

#### Multiple matches

**User-facing template:**

> "I found `<N>` files in Downloads matching `client_secret_*.json`:
>
> 1. `client_secret_aaa.json` (downloaded `<mtime>`) ← newest
> 2. `client_secret_bbb.json` (downloaded `<mtime>`)
> 3. `client_secret_ccc.json` (downloaded `<mtime>`)
>
> Which one did we just create? Reply with the filename, or say `newest` if you'd like me to use the top one. If you're not sure, the safest move is to delete all of these and re-download from the GCP Credentials page (sub-phase 1g) so there's no ambiguity."

- On `newest` or top filename: set `CONFIRMED_PATH` to that file, proceed to 1i.
- On other filename: set `CONFIRMED_PATH` to that file, proceed to 1i.
- On "I'm not sure" → guide user back to 1g for a fresh download, then re-run 1h.

**Before proceeding to 1i, ALWAYS validate the confirmed path:**

```bash
jq -e '.installed.client_id' "<CONFIRMED_PATH>" >/dev/null
```

If this fails, the file is not a valid OAuth client JSON. Tell the user what shape you expected vs. what you saw, and re-enter the 1h decision tree.

**Checkpoint:** `CONFIRMED_PATH` is set to a specific, validated file.

---

### Sub-phase 1i — Move the file into place

**Commands:**
```bash
mkdir -p ~/.config/multi-google-mcp
mv "<CONFIRMED_PATH>" ~/.config/multi-google-mcp/client_secret.json
```

> **Important:** Substitute the literal path you confirmed in 1h. **Do not** use a glob like `client_secret_*.json` as the source — that re-introduces the multi-match bug 1h exists to prevent.

**Verification:**
```bash
test -f ~/.config/multi-google-mcp/client_secret.json
jq -e '.installed.client_id' ~/.config/multi-google-mcp/client_secret.json >/dev/null
```

Both must succeed.

**User-facing template:**

> "Moving the file into the right place… done. Your OAuth client credentials are now at `~/.config/multi-google-mcp/client_secret.json`. The Google Cloud side is fully set up. Next we'll install the server CLI."

**Checkpoint:** Both verification commands succeed.

---

### Phase 1 — Exit ramp

If the user says any variant of "I can't do this right now," "let me come back to this," "I'll finish later," or sounds stuck for more than one back-and-forth:

1. Tell them exactly which sub-phase they stopped at. Example:
   > "No problem at all. You stopped after creating the project but before enabling the Gmail API — that's sub-phase 1c."
2. Tell them how to resume:
   > "When you're ready to pick this back up, open me (or any other AI agent in this repo) and say *'I'm back — I left off at sub-phase 1c'* and I'll continue from there."
3. Halt the runbook. Do not attempt Phases 2-6. They depend on GCP credentials being present at `~/.config/multi-google-mcp/client_secret.json`.

### Phase 1 — Things you must NOT do

- Do **not** invent any `console.cloud.google.com/...` URL. Use only the deep-link URLs listed in this phase's Commands blocks.
- Do **not** claim a sub-phase succeeded without explicit user confirmation OR an objective state check (the `jq` verification in 1i).
- Do **not** attempt to log into the user's Google account or use any browser-automation tooling. The runbook is strictly conversational at this phase.
- Do **not** advance from sub-phase 1i to Phase 2 if `jq` verification fails. Stop and ask the user to confirm what they downloaded.
- Do **not** use a globbed path (`client_secret_*.json`) as the source argument to `mv`. Always use the literal `CONFIRMED_PATH` from 1h.
````

- [ ] **Step 2: Verify the file structure**

```bash
grep -c '^### Sub-phase 1' /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
```

Expected: `9` (sub-phases 1a through 1i).

- [ ] **Step 3: Verify deep-link URLs are well-formed**

Read the file and confirm these exact deep-link URLs appear:
- `https://console.cloud.google.com`
- `https://console.cloud.google.com/apis/library/gmail.googleapis.com`
- `https://console.cloud.google.com/apis/library/calendar-json.googleapis.com`
- `https://console.cloud.google.com/apis/library/drive.googleapis.com`
- `https://console.cloud.google.com/apis/credentials/consent`
- `https://console.cloud.google.com/apis/credentials`

```bash
grep -c 'console.cloud.google.com' /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
```

Expected: at least `6`.

- [ ] **Step 4: Commit**

```bash
git add agents/install/claude-desktop.md
git commit -m "$(cat <<'EOF'
docs: add Phase 1 GCP walkthrough to Claude Desktop runbook

Nine sub-phases (1a-1i) walking a non-technical user through GCP project
creation, API enablement, OAuth consent setup, OAuth client creation,
and client_secret.json placement. Includes the zero/one/many decision
tree for sub-phase 1h to handle users with prior GCP downloads in
~/Downloads.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add Phases 2-4 (uv, CLI install, account auth) to Claude Desktop runbook

**Files:**
- Modify: `agents/install/claude-desktop.md` (append)

- [ ] **Step 1: Append Phases 2, 3, 4 content**

Append to the end of `agents/install/claude-desktop.md`:

````markdown
---

## Phase 2 — Install `uv`

`uv` is the Python package manager this server uses. It's a single binary, no system Python changes required.

### Detection

```bash
command -v uv
```

If this returns a path, skip to Phase 3.

### Commands

If `uv` is missing, **ask the user to run the install command in their own terminal** rather than executing it on their behalf:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After the user reports it ran, re-run detection.

### User-facing template

> "I don't see `uv` installed yet. `uv` is a fast Python package manager — it's the tool that will install the server's command-line interface.
>
> Could you paste this into your terminal? It downloads `uv` and adds it to your shell:
>
> ```
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
>
> Let me know once it finishes — it usually takes 10-30 seconds."

### Failure

If detection still fails after the user confirms:

- Their current shell may not have the new PATH yet. Ask them to run `source ~/.zshrc` (or open a new terminal).
- If still not on PATH after a fresh shell, ask them to paste the install output — there may have been an error.

### Exit ramp

None — single-command phase.

---

## Phase 3 — Install the CLI

This installs `multi-google-mcp` (the server) and `multi-google-mcp-auth` (the account manager) as shell commands on the user's PATH.

### Detection

```bash
command -v multi-google-mcp && command -v multi-google-mcp-auth
```

If both return paths, skip to Phase 4.

### Commands

Run from the repo root:

```bash
cd "$(git rev-parse --show-toplevel)" && uv tool install .
```

After this completes, re-run detection.

### User-facing template

> "Now I'm going to install the server's CLI from this repository. It puts two commands on your PATH:
> - `multi-google-mcp` — the server itself (Claude Desktop will start it automatically)
> - `multi-google-mcp-auth` — for connecting your Google accounts
>
> Running it now…"

After the install:

> "Done. The two commands are now on your PATH. Next step is connecting your first Google account."

### Failure

- If `uv tool install .` errors with a Python version complaint: check `python3 --version` ≥ 3.11. If lower, install Python 3.11+ first.
- If it errors with a network/registry issue: ask the user to try again in a minute (transient PyPI hiccup).
- If errors persist, surface the full output to the user and stop — do not guess.

### Exit ramp

None.

---

## Phase 4 — Add the first Google account

This connects a Google account to the server. The user can add more accounts later by repeating this phase with a different label.

### Detection

```bash
ls ~/.config/multi-google-mcp/accounts/*.json 2>/dev/null | head -1
```

If any account file exists, skip to Phase 5.

### Commands

Ask the user for a label (suggest `personal`), then run:

```bash
multi-google-mcp-auth add <label>
```

This opens a browser for the OAuth consent flow.

### User-facing template

> "Time to connect your first Google account. Each connected account gets a short label so you can refer to it later (like 'personal' or 'work').
>
> What label would you like to use for the first account? (If you're not sure, `personal` is a fine default.)"

After the user picks a label, run `multi-google-mcp-auth add <label>` and:

> "A browser window should be opening in a moment. It'll ask you to sign in to Google — use the same account you added as a test user during the consent screen setup back in sub-phase 1f. After you sign in, Google will list the permissions this server needs (Gmail, Calendar, Drive). Click **Allow**.
>
> When the browser tab shows 'Authentication complete' (or similar), come back here and let me know."

### Verification

```bash
# Confirm the token file exists and contains a non-null refresh_token,
# without ever printing the secret. Both commands must succeed.
test -f ~/.config/multi-google-mcp/accounts/<label>.json
jq -e '.refresh_token != null' ~/.config/multi-google-mcp/accounts/<label>.json >/dev/null
```

Both must succeed. The boolean predicate `.refresh_token != null` plus
the `>/dev/null` redirect is load-bearing — `jq -e '.refresh_token' <path>`
without redirection prints the live OAuth refresh token to stdout.

### Failure

- **Browser hangs on `localhost:<port>` after consent:** A firewall, VPN, or proxy is intercepting localhost. Tell the user to temporarily disable their VPN and retry `multi-google-mcp-auth add <label>`.
- **`Error 403: access_denied`:** The signed-in Google account wasn't added as a test user in sub-phase 1f. Walk back to 1f, add the account, then retry.
- **`Error: scope ... not granted`:** The user unchecked one of the requested permissions. Retry and grant everything.

### Exit ramp

The user can defer this phase. If they say "I'll connect an account later":

1. Tell them: *"That's fine. The server will be wired into Claude Desktop in the next step, but it won't do anything useful until you add at least one account. When you're ready, just run `multi-google-mcp-auth add <label>` from any terminal."*
2. Skip to Phase 5. The harness wiring is still useful even without accounts.
````

- [ ] **Step 2: Verify the file structure**

```bash
grep -c '^## Phase' /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
```

Expected: `5` (Phases 0, 1, 2, 3, 4).

- [ ] **Step 3: Verify command correctness by running detections**

```bash
command -v uv
command -v multi-google-mcp && command -v multi-google-mcp-auth
ls ~/.config/multi-google-mcp/accounts/*.json 2>/dev/null | head -1
```

These should all return without shell parse errors (succeed or fail cleanly).

- [ ] **Step 4: Commit**

```bash
git add agents/install/claude-desktop.md
git commit -m "$(cat <<'EOF'
docs: add Phases 2-4 (uv, CLI install, account auth) to Claude Desktop runbook

Adds the uv install bootstrap, the `uv tool install .` step, and the
`multi-google-mcp-auth add <label>` browser-consent walkthrough. Each
phase has detection (idempotency), commands, user-facing templates,
failure handling, and where applicable, exit ramps.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add Phase 5 (Claude Desktop config wiring) and Phase 6 (verify) to Claude Desktop runbook

**Files:**
- Modify: `agents/install/claude-desktop.md` (append)

- [ ] **Step 1: Append Phase 5 and Phase 6 content**

Append to the end of `agents/install/claude-desktop.md`:

````markdown
---

## Phase 5 — Wire the server into Claude Desktop's config

Claude Desktop reads a JSON config file at startup to discover MCP servers. We add an entry for `multi-google` to that file. **Critically, we merge with whatever's already there — never clobber.**

### Detection

```bash
jq -e '.mcpServers["multi-google"]' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
  2>/dev/null
```

If this returns the expected entry, skip to Phase 6.

### Commands

**Path:** `$HOME/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

> **Windows/Linux note:** The equivalent paths are `%APPDATA%\Claude\claude_desktop_config.json` on Windows and `~/.config/Claude/claude_desktop_config.json` on Linux. This runbook is tested on macOS only — if the user is on another platform, walk them through the path substitution and proceed with the same JSON merge logic.

**Backup before write:**

```bash
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
test -f "$CFG" && cp "$CFG" "${CFG}.bak.$(date +%Y%m%d-%H%M%S)"
```

**Why an absolute path?** Claude Desktop is a GUI app. Launched from
Finder, Dock, or Spotlight it inherits `launchd`'s minimal PATH
(`/usr/bin:/bin:/usr/sbin:/sbin`) — not the shell PATH that contains
`~/.local/bin` where `uv tool install` puts the binary. A bare-name
`"command": "multi-google-mcp"` looks correct from a terminal but fails
silently when Claude Desktop launches normally. Phase 5 resolves the
absolute path via `command -v` at write time.

**Read-merge-write logic:**

1. Resolve `MGM_BIN="$(command -v multi-google-mcp)"`. Bail if empty.

2. If `$CFG` does not exist: create it with `{"mcpServers": {"multi-google": {"command": "<MGM_BIN>"}}}` (pretty-printed with 2-space indent).

3. If `$CFG` exists: read it, validate it parses as JSON. If parse fails, **stop and surface the error** — do not overwrite a malformed config. Tell the user where the backup is.

4. If parse succeeds: set `.mcpServers["multi-google"] = {"command": "$MGM_BIN"}`. Preserve all other top-level keys and all other entries inside `mcpServers`.

5. Write the merged JSON back to `$CFG` with 2-space indent.

The agent does this using whichever tool is most reliable for it — typically reading the file, parsing in memory, modifying the structure, and writing it back via its file-write tool. The `jq` one-liner below is a sanity-checkable shortcut when the agent doesn't have a JSON-aware edit tool:

```bash
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
MGM_BIN="$(command -v multi-google-mcp)"
[ -n "$MGM_BIN" ] || { echo "multi-google-mcp not on PATH — rerun Phase 3 first."; exit 1; }
mkdir -p "$(dirname "$CFG")"
test -f "$CFG" || echo '{}' > "$CFG"
cp "$CFG" "${CFG}.bak.$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp)"
jq --arg cmd "$MGM_BIN" '.mcpServers["multi-google"] = {"command": $cmd}' "$CFG" > "$TMP" && mv "$TMP" "$CFG"
```

### User-facing template

> "Now we tell Claude Desktop where to find this server. Claude Desktop has a config file at:
>
> `~/Library/Application Support/Claude/claude_desktop_config.json`
>
> I'm going to read what's already in it (so I don't overwrite any other servers you have configured), add an entry for `multi-google` with the absolute path to the server binary, and write it back. I'll make a backup first."

After the write:

> "Done. Your config now includes a `multi-google` entry under `mcpServers`, pointing at `<MGM_BIN>`. I backed up your previous config to `<backup-path>` just in case. Next we restart Claude Desktop and verify."

### Verification

```bash
STORED_CMD="$(jq -r '.mcpServers["multi-google"].command' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json")"
[ -n "$STORED_CMD" ] && [ -x "$STORED_CMD" ]
```

Both checks must succeed — the entry was written AND the stored path points at an executable file.

### Failure

- **Existing config is invalid JSON:** Surface the parse error to the user. Tell them the path to the file, ask them to either fix the JSON manually or delete the file (which forces a clean default Claude Desktop config on next launch). Do **not** auto-fix — the file may contain settings unrelated to MCP that the user values.

- **`jq` not installed:** Tell the user `brew install jq` (macOS). Retry after install.

- **Write permission denied:** Surface the error. This usually means a permissions issue with the Claude Desktop application directory; the user may need to check that file's ownership.

### Exit ramp

None — this is the final modifying phase. If the user wants to defer the verify step (Phase 6), the install is technically done; they just won't know it works until they restart Claude Desktop.

---

## Phase 6 — Verify and restart

The install is done on disk. Now we confirm Claude Desktop picks up the change.

### Detection

None — Phase 6 always runs.

### Commands

None on the shell side. This phase is conversational.

### User-facing template

> "We're done with the install. Two final steps to verify everything works.
>
> **Step 1: Fully quit Claude Desktop.** Cmd+Q (not just closing the window — Cmd+Q to fully quit). Then reopen Claude Desktop.
>
> **Step 2: Test a tool call.** Once Claude Desktop is open again, try a prompt like:
>
> *"Use multi-google to search my `<your-label>` Gmail for unread messages from this week."*
>
> If Claude calls a tool starting with `gmail_` (you'll see it in the conversation), the install worked. Let me know what happens."

### Failure modes — and how to diagnose with the user

**Tools don't appear / Claude doesn't call any `gmail_*` tool:**

1. Confirm Claude Desktop actually restarted (not just window-closed).
2. Run `multi-google-mcp` manually from a terminal:
   ```bash
   multi-google-mcp
   ```
   It should print nothing and wait on stdin. Ctrl-C to exit. If it errors at startup, surface the error — likely missing `client_secret.json` or some account-token issue.
3. Verify the config one more time:
   ```bash
   jq '.mcpServers["multi-google"]' \
     "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
   ```
   Should print the entry.
4. Check Claude Desktop's own logs (Help → View Logs in the menu) for an error starting `multi-google`.

**`Error: Account '<label>' not configured`:**

The label the user typed doesn't match any added account. Either ask the user to use the right label, or run `multi-google-mcp-auth add <label>` for the one they want.

### Exit ramp

None — this is the success terminus.

---

## You're done

When Phase 6 succeeds, tell the user:

> "All set. Your `multi-google-mcp` install is wired into Claude Desktop and working. A few useful follow-ups whenever you need them:
>
> - **Add another account:** `multi-google-mcp-auth add <new-label>`
> - **List configured accounts:** `multi-google-mcp-auth list`
> - **Remove an account:** `multi-google-mcp-auth remove <label>`
> - **Troubleshooting:** see the project README's Troubleshooting section.
>
> Happy to help if anything goes sideways later."
````

- [ ] **Step 2: Verify all 7 phases are present**

```bash
grep -c '^## Phase ' /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
```

Expected: `7` (Phases 0, 1, 2, 3, 4, 5, 6).

- [ ] **Step 3: Verify the file's `jq` operations are syntactically valid**

```bash
# Test the read-merge-write jq operation on a temp file, using the
# absolute-path pattern the runbook actually emits.
TMP=$(mktemp)
echo '{"mcpServers": {"existing": {"command": "foo"}}}' > "$TMP"
MGM_BIN="$(command -v multi-google-mcp || echo /scratch/fake-bin)"
jq --arg cmd "$MGM_BIN" '.mcpServers["multi-google"] = {"command": $cmd}' "$TMP"
```

Expected: prints a JSON object containing both `existing` and `multi-google` under `mcpServers`. Both keys preserved.

- [ ] **Step 4: Commit**

```bash
git add agents/install/claude-desktop.md
git commit -m "$(cat <<'EOF'
docs: add Phase 5 (config wiring) and Phase 6 (verify) to Claude Desktop runbook

Phase 5 walks the agent through the read-merge-write of
~/Library/Application Support/Claude/claude_desktop_config.json with
explicit backup before write, parse-failure guarding, and preservation
of pre-existing mcpServers entries. Phase 6 covers the restart and
smoke-test prompt.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Write the Codex runbook by adapting the Claude Desktop one

**Files:**
- Create: `agents/install/codex.md`

The Codex runbook is structurally identical to claude-desktop.md except (a) the title and intro reference Codex, (b) Phase 0's harness-check checks `~/.codex/config.toml` instead of the Claude Desktop JSON, (c) Phase 5 uses TOML append logic instead of JSON merge, and (d) Phase 6's user-facing template references restarting `codex` rather than Claude Desktop.

- [ ] **Step 1: Create the file by copying claude-desktop.md as a starting point**

```bash
cp /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md \
   /Users/bjunya/code/multi-google-mcp/agents/install/codex.md
```

- [ ] **Step 2: Replace the title and intro**

Replace the first heading and intro paragraph at the top of `agents/install/codex.md`:

**Old:**
```markdown
# Install `multi-google-mcp` into Claude Desktop — Agent Runbook

> **Audience:** You are an AI agent (Claude Desktop, Claude Code, Cursor, etc.) running locally inside a clone of the `multi-google-mcp` repo. The human in front of you has asked you to install this server. Follow this runbook end-to-end. The user may have little to no experience with the command line, GCP, or JSON — treat them with patience.
```

**New:**
```markdown
# Install `multi-google-mcp` into Codex CLI — Agent Runbook

> **Audience:** You are an AI agent (Codex CLI, Claude Code, Cursor, etc.) running locally inside a clone of the `multi-google-mcp` repo. The human in front of you has asked you to install this server. Follow this runbook end-to-end. The user may have little to no experience with the command line, GCP, or TOML — treat them with patience.
```

- [ ] **Step 3: Update Phase 0 detection check #5 and #6**

In `agents/install/codex.md`, in Phase 0's Detection block, replace checks 5 and 6:

**Old:**
```bash
# 5. Claude Desktop config file present
test -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# 6. multi-google server already wired into Claude Desktop config
jq -e '.mcpServers["multi-google"]' \
  "$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
  2>/dev/null
```

**New:**
```bash
# 5. Codex config file present
test -f "$HOME/.codex/config.toml"

# 6. multi-google server already wired into Codex config
grep -q '^\[mcp_servers\.multi-google\]' "$HOME/.codex/config.toml" 2>/dev/null
```

Also update the corresponding line in the User-facing template inside Phase 0:

**Old:**
> - [✓/✗] Claude Desktop config file present
> - [✓/✗] `multi-google` server already wired into Claude Desktop

**New:**
> - [✓/✗] Codex config file present at `~/.codex/config.toml`
> - [✓/✗] `multi-google` server already wired into Codex

- [ ] **Step 4: Replace Phase 5 entirely with the Codex TOML variant**

Find the `## Phase 5 — Wire the server into Claude Desktop's config` section and replace it (everything through `---` before `## Phase 6`) with:

````markdown
## Phase 5 — Wire the server into Codex's config

Codex reads MCP server definitions from `~/.codex/config.toml`. We append a `[mcp_servers.multi-google]` section to that file. **Critically, we preserve everything that's already there — never rewrite the whole file.**

### Detection

```bash
grep -q '^\[mcp_servers\.multi-google\]' "$HOME/.codex/config.toml" 2>/dev/null
```

If this matches, also extract the stored command and verify it points at an executable:

```bash
STORED_CMD="$(grep -A2 '^\[mcp_servers\.multi-google\]' "$HOME/.codex/config.toml" \
  | sed -n 's/^command = "\(.*\)"$/\1/p' | head -1)"
[ -n "$STORED_CMD" ] && [ -x "$STORED_CMD" ]
```

If both pass, skip to Phase 6. If the section exists but `STORED_CMD` isn't executable (typical with a bare-name install pre-this-runbook), continue with Phase 5 to overwrite with the absolute path.

### Commands

**Path:** `$HOME/.codex/config.toml`.

**Why an absolute path?** Codex inherits the shell PATH when launched from
a login terminal, but not under launchd, GUI wrappers, or non-login shells.
We resolve the absolute path via `command -v` at write time so the config
is robust across all launch contexts.

**Backup before write:**

```bash
CFG="$HOME/.codex/config.toml"
test -f "$CFG" && cp "$CFG" "${CFG}.bak.$(date +%Y%m%d-%H%M%S)"
```

**Append-or-replace logic:**

1. Resolve `MGM_BIN="$(command -v multi-google-mcp)"`. Bail if empty.
2. Ensure the parent directory exists: `mkdir -p ~/.codex`.
3. If `$CFG` does not exist: create it containing only the new section with the absolute path.
4. If `$CFG` exists AND the `[mcp_servers.multi-google]` section is already there: rewrite just that section in place (preserving other sections and blank lines) so the `command` line points at `$MGM_BIN`.
5. If `$CFG` exists AND the section is not present yet: append a leading blank line followed by the new section.

```bash
CFG="$HOME/.codex/config.toml"
MGM_BIN="$(command -v multi-google-mcp)"
[ -n "$MGM_BIN" ] || { echo "multi-google-mcp not on PATH — rerun Phase 3 first."; exit 1; }
mkdir -p "$(dirname "$CFG")"
test -f "$CFG" && cp "$CFG" "${CFG}.bak.$(date +%Y%m%d-%H%M%S)"

if [ -f "$CFG" ] && grep -q '^\[mcp_servers\.multi-google\]' "$CFG"; then
  TMP="$(mktemp)"
  awk -v cmd="$MGM_BIN" '
    BEGIN { in_sec = 0 }
    /^\[mcp_servers\.multi-google\][[:space:]]*$/ {
      in_sec = 1
      print "[mcp_servers.multi-google]"
      print "command = \"" cmd "\""
      next
    }
    in_sec && /^\[/ { in_sec = 0 }
    in_sec && /^$/ { in_sec = 0 }
    !in_sec { print }
  ' "$CFG" > "$TMP" && mv "$TMP" "$CFG"
else
  {
    test -f "$CFG" && cat "$CFG"
    test -f "$CFG" && echo ""
    echo "[mcp_servers.multi-google]"
    echo "command = \"$MGM_BIN\""
  } > "${CFG}.new"
  mv "${CFG}.new" "$CFG"
fi
```

### User-facing template

> "Now we tell Codex where to find this server. Codex has a config file at:
>
> `~/.codex/config.toml`
>
> I'm going to read what's already in it (so I don't disturb any other settings you have), add a `[mcp_servers.multi-google]` section with the absolute path to the server binary (`<MGM_BIN>`), and write it back. I'll make a backup first."

After the write:

> "Done. Your config now includes the `multi-google` server pointing at `<MGM_BIN>`. I backed up your previous config to `<backup-path>` just in case. Next we restart Codex and verify."

### Verification

```bash
grep -q '^\[mcp_servers\.multi-google\]' "$HOME/.codex/config.toml"
STORED_CMD="$(grep -A2 '^\[mcp_servers\.multi-google\]' "$HOME/.codex/config.toml" \
  | sed -n 's/^command = "\(.*\)"$/\1/p' | head -1)"
[ -n "$STORED_CMD" ] && [ -x "$STORED_CMD" ]
```

All three checks must succeed.

### Failure

- **Existing config has malformed TOML:** Codex would have errored on startup if so, but if the agent's append corrupts something, the user has a `.bak` to roll back. Surface the issue, point at the backup, and stop.

- **Write permission denied:** Tell the user; check `~/.codex/` ownership.

### Exit ramp

None — this is the final modifying phase.
````

- [ ] **Step 5: Update Phase 6 user-facing template**

In Phase 6, replace the user-facing template (the block under `### User-facing template`):

**Old:**
> "We're done with the install. Two final steps to verify everything works.
>
> **Step 1: Fully quit Claude Desktop.** Cmd+Q (not just closing the window — Cmd+Q to fully quit). Then reopen Claude Desktop.
>
> **Step 2: Test a tool call.** Once Claude Desktop is open again, try a prompt like:
>
> *"Use multi-google to search my `<your-label>` Gmail for unread messages from this week."*
>
> If Claude calls a tool starting with `gmail_` (you'll see it in the conversation), the install worked. Let me know what happens."

**New:**
> "We're done with the install. Two final steps to verify everything works.
>
> **Step 1: Start a new Codex session.** If you currently have a `codex` session open, exit it (Ctrl+C / `exit`) and run `codex` again from a fresh terminal — Codex reads the config once at startup.
>
> **Step 2: Test a tool call.** Once the new session is running, try a prompt like:
>
> *"Use multi-google to search my `<your-label>` Gmail for unread messages from this week."*
>
> If Codex calls a tool starting with `gmail_` (you'll see it in the conversation), the install worked. Let me know what happens."

Also update Phase 6's "Failure modes" section — replace the line about Claude Desktop's logs:

**Old:**
> 4. Check Claude Desktop's own logs (Help → View Logs in the menu) for an error starting `multi-google`.

**New:**
> 4. Check Codex's session log (`~/.codex/log/` or `codex --debug`) for an error starting the `multi-google` server.

- [ ] **Step 6: Update the closing "You're done" message**

In the very last section (`## You're done`), the closing template references Claude Desktop implicitly. Make sure the language is harness-agnostic — replace:

**Old:**
> "All set. Your `multi-google-mcp` install is wired into Claude Desktop and working. A few useful follow-ups whenever you need them:

**New:**
> "All set. Your `multi-google-mcp` install is wired into Codex and working. A few useful follow-ups whenever you need them:

- [ ] **Step 7: Verify structural parity with claude-desktop.md**

```bash
grep -c '^## Phase ' /Users/bjunya/code/multi-google-mcp/agents/install/codex.md
grep -c '^### Sub-phase 1' /Users/bjunya/code/multi-google-mcp/agents/install/codex.md
```

Expected: phases = `7`, sub-phases = `9`.

- [ ] **Step 8: Verify the TOML append logic with a sanity test**

```bash
# Simulate the append on an empty file
SCRATCH=$(mktemp -d)
CFG="$SCRATCH/config.toml"
echo '[some_other_section]
key = "value"' > "$CFG"

MGM_BIN="$(command -v multi-google-mcp || echo /scratch/fake-bin)"
{
  cat "$CFG"
  echo ""
  echo "[mcp_servers.multi-google]"
  echo "command = \"$MGM_BIN\""
} > "${CFG}.new"
mv "${CFG}.new" "$CFG"

cat "$CFG"
echo "---"
grep -q '^\[mcp_servers\.multi-google\]' "$CFG" && echo "section found"
grep -q '^\[some_other_section\]' "$CFG" && echo "original section preserved"
rm -rf "$SCRATCH"
```

Expected output: TOML containing both sections; "section found" and "original section preserved" both printed.

- [ ] **Step 9: Commit**

```bash
git add agents/install/codex.md
git commit -m "$(cat <<'EOF'
docs: add Codex CLI install runbook

Mirrors agents/install/claude-desktop.md except for the harness-specific
bits: Phase 0 check #5/#6 look at ~/.codex/config.toml; Phase 5 uses a
TOML append-with-backup pattern instead of JSON merge; Phase 6 references
restarting `codex` rather than Claude Desktop.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Update README — add "Quick install" pointer and demote existing install sections

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Insert the new "Quick install" section after Prerequisites**

In `/Users/bjunya/code/multi-google-mcp/README.md`, find the existing "## Prerequisites" section. After its bullet list and before the existing `## GCP setup (one-time)` heading, insert this block:

```markdown

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
```

- [ ] **Step 2: Demote the existing install subsections from `##` to `###`**

In `/Users/bjunya/code/multi-google-mcp/README.md`, change these four heading levels (they should now be subsections of "## Manual install"):

- `## GCP setup (one-time)` → `### GCP setup (one-time)`
- `## Install` → `### Install`
- `## Add your first account` → `### Add your first account`
- `## Wire into Claude Desktop` → `### Wire into Claude Desktop`

The remaining `##` headings stay unchanged (`## Verifying your setup`, `## Adding scopes or new accounts later`, `## Troubleshooting`, `## Project layout`).

- [ ] **Step 3: Verify heading structure**

```bash
grep -n '^##\? ' /Users/bjunya/code/multi-google-mcp/README.md
```

Expected output (in order):
- `## Prerequisites`
- `## Quick install (let an agent do it)`
- `## Manual install`
- `### GCP setup (one-time)`
- `### Install`
- `### Add your first account`
- `### Wire into Claude Desktop`
- `## Verifying your setup`
- `## Adding scopes or new accounts later`
- `## Troubleshooting`
- `## Project layout`

(Lines starting with `# ` for the H1 title also appear, plus any `# from a clone of this repo` shell comments inside code blocks — those are fine.)

- [ ] **Step 4: Verify links resolve to real files**

```bash
test -f /Users/bjunya/code/multi-google-mcp/agents/install/claude-desktop.md
test -f /Users/bjunya/code/multi-google-mcp/agents/install/codex.md
```

Both must succeed.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: README points users at agent-driven install runbooks

Adds a "Quick install (let an agent do it)" section above the existing
install content, which is now nested under a "Manual install" parent
heading. The new section links directly to agents/install/claude-desktop.md
and agents/install/codex.md so AI agents discover the runbooks naturally
from the README.

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Final end-to-end sanity sweep of both runbooks

**Files:**
- No file changes expected — this is a read-only review pass. Only modify if issues are found.

- [ ] **Step 1: Read claude-desktop.md top to bottom**

Read the full file. Verify:

- Every section uses the five-block structure (Detection, Commands, User-facing template, Failure, Exit ramp) where applicable.
- No `TBD`, `TODO`, `<placeholder>`, or undefined references.
- All shell commands have proper quoting around variables that contain spaces (e.g., `"$HOME/Library/Application Support/..."` — note the double quotes).
- All `console.cloud.google.com` URLs are listed in the spec's §8.1 (no fabricated URLs).

- [ ] **Step 2: Read codex.md top to bottom**

Same checks. Plus verify:

- Phase 5 uses TOML append logic only (no JSON merge text left over).
- Phase 6 references Codex (not Claude Desktop) throughout the user-facing template and failure modes.
- The closing "You're done" line says "Codex" not "Claude Desktop."

- [ ] **Step 3: Spot-check each deep-link URL by opening it**

```bash
open https://console.cloud.google.com/apis/library/gmail.googleapis.com
open https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
open https://console.cloud.google.com/apis/library/drive.googleapis.com
open https://console.cloud.google.com/apis/credentials/consent
open https://console.cloud.google.com/apis/credentials
```

Each should open the corresponding GCP page (not a 404 or redirect to dashboard).

- [ ] **Step 4: Verify the README's new structure renders correctly**

```bash
head -60 /Users/bjunya/code/multi-google-mcp/README.md
```

Visually confirm:
- Prerequisites section is intact.
- Quick install section follows.
- Manual install heading precedes the existing GCP/Install/Add account/Wire sections.
- No duplicate headings or orphaned blocks.

- [ ] **Step 5: Run repo-wide lint and test checks**

This repo has `pyproject.toml` with `ruff`, `pytest`, and `mypy` configured. Run them from the repo root:

```bash
cd /Users/bjunya/code/multi-google-mcp
ruff check .
mypy
pytest
```

Expected: ruff, mypy, pytest all pass (markdown changes shouldn't affect any of these). If any fail, the failure is unrelated to this PR — surface it and stop.

- [ ] **Step 6: If any issue found in steps 1-5, fix it as a separate commit**

If a fix is needed:

```bash
git add <files>
git commit -m "$(cat <<'EOF'
docs: <one-line description of the fix>

<short body explaining what was wrong and how the fix addresses it>

No test added — documentation-only change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If no fix is needed, this task ends without a commit.

---

## Self-review checklist

After completing all tasks, before pushing the branch:

- [ ] Both runbooks have 7 phases (0-6).
- [ ] Phase 1 in both runbooks has 9 sub-phases (1a-1i).
- [ ] Phase 1h's decision tree covers zero/one/many match cases.
- [ ] Phase 1i uses a literal path, not a glob, in its `mv` command.
- [ ] Phase 5 in claude-desktop.md uses `jq` JSON merge.
- [ ] Phase 5 in codex.md uses TOML append.
- [ ] Phase 5 (both) backs up the config before writing.
- [ ] Phase 5 (both) explicitly preserves existing entries.
- [ ] README has both new sections ("Quick install" and "Manual install" parent).
- [ ] README links to both runbook files resolve.
- [ ] Tone & pacing section appears once in each runbook header.
- [ ] No fabricated URLs anywhere — all GCP deep-links match the spec.
- [ ] All commit messages call out "No test added — documentation-only change."

---

## Out-of-band considerations for `/code-task`

- **Phase 3 (pre-push verification):** This repo has `pyproject.toml` with `ruff` and `pytest` configured. Both must pass before push. None of this PR's changes touch Python, so they should pass untouched.
- **Phase 4 (PR body):** Title = "Agent-driven install runbooks (Claude Desktop + Codex)". Summary bullets: (1) two new agent runbook files, (2) README pointer + reorganization, (3) zero/one/many safety in GCP sub-phase 1h.
- **Phase 5 (Aria review):** Aria's likely areas of feedback — completeness of failure cases in Phase 1h, JSON merge correctness in Phase 5 of claude-desktop.md, TOML append correctness in Phase 5 of codex.md. Be ready to add edge cases she catches.
- **Phase 6 (merge):** Per the `--merge` flag passed to `/code-task`, auto-merge after Aria approves.
- **Phase 7 (notify):** Uses ARIA_ACTIONS_URL and ARIA_ACTIONS_TOKEN from the environment (verified at session start).
