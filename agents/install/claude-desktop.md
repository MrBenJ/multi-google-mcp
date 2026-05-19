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

# 4. At least one account configured (use `find` to stay portable across bash/zsh —
#    a bare `ls foo/*.json` errors under zsh's NOMATCH when the glob matches nothing)
find ~/.config/multi-google-mcp/accounts -maxdepth 1 -name '*.json' 2>/dev/null | head -1

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
# Enumerate candidates, newest first. `find` is used here (rather than
# `ls ~/Downloads/client_secret_*.json`) because a bare glob errors out
# under zsh's NOMATCH option when there are zero matches.
find ~/Downloads -maxdepth 1 -name 'client_secret_*.json' -print0 2>/dev/null \
  | xargs -0 ls -lt 2>/dev/null
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
find ~/.config/multi-google-mcp/accounts -maxdepth 1 -name '*.json' 2>/dev/null | head -1
```

If any account file is printed, skip to Phase 5.

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
test -f ~/.config/multi-google-mcp/accounts/<label>.json
jq -e '.refresh_token' ~/.config/multi-google-mcp/accounts/<label>.json
```

Both must succeed.

### Failure

- **Browser hangs on `localhost:<port>` after consent:** A firewall, VPN, or proxy is intercepting localhost. Tell the user to temporarily disable their VPN and retry `multi-google-mcp-auth add <label>`.
- **`Error 403: access_denied`:** The signed-in Google account wasn't added as a test user in sub-phase 1f. Walk back to 1f, add the account, then retry.
- **`Error: scope ... not granted`:** The user unchecked one of the requested permissions. Retry and grant everything.

### Exit ramp

The user can defer this phase. If they say "I'll connect an account later":

1. Tell them: *"That's fine. The server will be wired into Claude Desktop in the next step, but it won't do anything useful until you add at least one account. When you're ready, just run `multi-google-mcp-auth add <label>` from any terminal."*
2. Skip to Phase 5. The harness wiring is still useful even without accounts.
