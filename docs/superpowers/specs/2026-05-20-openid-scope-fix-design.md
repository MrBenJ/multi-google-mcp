# Add `openid` to OAuth SCOPES to unblock auth flow

## Goal

Fix `multi-google-mcp-auth add <label>` aborting when Google returns `openid` in
the granted scope set. Add `"openid"` to `config.SCOPES` so the requested set
matches what Google returns, and `oauthlib`'s scope-change check stops firing.

## Background

Google's OAuth implementation implicitly grants `openid` whenever
`userinfo.email` (or other identity-bearing scopes) is requested. `oauthlib`'s
`InstalledAppFlow` treats any divergence between requested and granted scopes as
a `Warning`, which `oauthlib` raises as an exception, aborting the flow before
the token is persisted. The repro is `multi-google-mcp-auth add personal`
against a fresh OAuth client — it fails consistently.

## Change

Single-line edit to `src/multi_google_mcp/config.py`: append `"openid"` to the
`SCOPES` list.

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
```

No code changes elsewhere. `accounts.py` consumes `SCOPES` directly from
`config`; nothing else cares about the list contents.

## Why not a test

The OAuth flow only runs against live Google APIs — `auth_cli.py` calls
`google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(...)` and
drives a local browser callback. The existing test suite mocks
`googleapiclient.discovery.build` and never exercises the auth flow. There is no
seam for a unit test to catch this regression, and the scope-list contents are
trivially inspectable. Per the `superpowers:test-driven-development` config-only
exception, no new test is added.

## Verification

1. `uv tool install --reinstall .` — reinstall the console script so the
   already-installed `multi-google-mcp-auth` picks up the updated `SCOPES`.
2. `multi-google-mcp-auth add personal` — completes without `oauthlib` raising
   on scope mismatch, prints success, writes
   `~/.config/multi-google-mcp/accounts/personal.json`.

## Caveats

- CLAUDE.md notes: changing `SCOPES` requires every existing account to be
  re-added. The `personal` account is re-added as the verify step. No other
  accounts exist locally (confirmed by user), so nothing else to handle.
- This is a one-way fix — `openid` is a stable, standardized OIDC scope and is
  effectively always granted alongside `userinfo.email`. No regression risk for
  callers that don't care about identity tokens (we don't use the ID token; the
  scope is purely there to keep `oauthlib` quiet).

## Non-goals

- No update to CLAUDE.md's scope-list commentary in this change.
- No revisit of the broader OAuth flow or scope set.
- No swap to a different OAuth library or relaxed `oauthlib` warning policy.
