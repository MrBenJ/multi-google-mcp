# Add `openid` to OAuth SCOPES Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append `"openid"` to `SCOPES` in `src/multi_google_mcp/config.py` so `oauthlib` stops aborting `multi-google-mcp-auth add` when Google implicitly grants the `openid` scope.

**Architecture:** One-line edit to a config list. No new tests (the OAuth flow is not exercised in the test suite; verification happens against live Google APIs). After editing, the locally installed `multi-google-mcp-auth` console script is reinstalled with `uv tool install --reinstall .` so it picks up the new code, then the auth flow is driven manually against the `personal` account to confirm the fix.

**Tech Stack:** Python 3.11+, `uv`, `google-auth-oauthlib`, `oauthlib`, `mcp` SDK.

---

## File Structure

- Modify: `src/multi_google_mcp/config.py:9-14` — add `"openid"` to the existing `SCOPES` list.

That's all. No new files, no other modifications.

---

### Task 1: Add `openid` to SCOPES and verify static checks

**Files:**
- Modify: `src/multi_google_mcp/config.py:9-14`

- [ ] **Step 1: Make the edit**

Open `src/multi_google_mcp/config.py` and change the `SCOPES` list from:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
]
```

to:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
```

- [ ] **Step 2: Run the existing test suite**

Run: `uv run pytest`
Expected: PASS — all existing tests still pass. The added scope is consumed only by the auth CLI's `InstalledAppFlow` and is not exercised in tests (`accounts.py` references `config.SCOPES` but the test fixtures stub out the OAuth flow entirely).

- [ ] **Step 3: Run the linter**

Run: `uv run ruff check .`
Expected: PASS — `All checks passed!`.

- [ ] **Step 4: Run the type-checker**

Run: `uv run mypy`
Expected: PASS — no new errors.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/config.py
git commit -m "$(cat <<'EOF'
fix: add openid to OAuth SCOPES to unblock auth flow

Google implicitly grants the openid scope whenever userinfo.email (or
any identity-bearing scope) is requested. oauthlib raises the scope
mismatch as an exception via its Warning-to-error path, aborting
multi-google-mcp-auth add before any token is written.

Adding "openid" to the requested set keeps the granted set aligned and
silences oauthlib without changing actual API access.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Reinstall the console scripts so the installed CLI picks up the new code

**Files:** None modified.

- [ ] **Step 1: Reinstall**

Run: `uv tool install --reinstall .`
Expected: output ends with something like `Installed 2 executables: multi-google-mcp, multi-google-mcp-auth`. No errors.

- [ ] **Step 2: Sanity-check the installed binary picks up the new scope list**

Run:
```bash
which multi-google-mcp-auth
uv tool run --from . python -c "from multi_google_mcp.config import SCOPES; print('openid' in SCOPES, len(SCOPES))"
```
Expected: path is printed; second line prints `True 5`.

- [ ] **Step 3: No commit**

Reinstall produces no repo changes — nothing to commit.

---

### Task 3: Verify the fix end-to-end against the `personal` account

**Files:** None modified.

- [ ] **Step 1: Run the auth flow**

Run: `multi-google-mcp-auth add personal`
Expected behavior:
- Prints a `Please visit this URL` line and opens a browser tab to Google's consent screen.
- User completes consent in the browser.
- Process prints something like `Saved account 'personal' to ~/.config/multi-google-mcp/accounts/personal.json` (or whatever success line `auth_cli.py` emits) and exits 0.
- The previous failure mode — an `oauthlib` exception about scope mismatch / Warning before the token file is written — does NOT occur.

Note: this step is interactive (browser OAuth consent). If running in a non-interactive context, hand off to the user with a clear "please complete the OAuth consent in your browser" prompt.

- [ ] **Step 2: Confirm the token file was (re)written**

Run: `ls -la ~/.config/multi-google-mcp/accounts/personal.json && stat -f '%Sm' ~/.config/multi-google-mcp/accounts/personal.json`
Expected: file exists, permissions are `-rw-------` (mode 0o600 per `accounts._atomic_write_json`), modification timestamp is from the last few seconds.

- [ ] **Step 3: Confirm the new scope set is in the saved token**

Run: `python -c "import json; d=json.load(open('${HOME}/.config/multi-google-mcp/accounts/personal.json')); print(sorted(d.get('scopes', [])))"`
Expected: list includes `"openid"` alongside the other four scopes.

- [ ] **Step 4: No commit**

Verification produces no repo changes — nothing to commit.

---

## Notes on what is *not* in this plan

- No new unit test. The `SCOPES` list is data, not behavior; the OAuth flow it feeds is not under test in this repo (test fixtures mock `googleapiclient.discovery.build` and never construct an `InstalledAppFlow`). Per the test-driven-development skill's config-only exception, no test is added.
- No update to CLAUDE.md's commentary about the SCOPES list — out of scope for this fix.
- No revisit of other OAuth-flow ergonomics (token rotation, scope subset upgrades, etc.).
