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
