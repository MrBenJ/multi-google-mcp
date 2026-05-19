"""multi-google-mcp-auth: manage local OAuth tokens for the MCP server."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from multi_google_mcp import config
from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import (
    AccountNotConfigured,
    OAuthClientNotConfigured,
)


def _fetch_email(creds: Any) -> str:
    """Look up the authenticated user's email via the userinfo endpoint."""
    service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
    info = service.userinfo().get().execute()
    return str(info["email"])


def _cmd_add(label: str) -> int:
    if not config.CLIENT_SECRET_PATH.exists():
        print(
            f"error: client_secret.json missing at {config.CLIENT_SECRET_PATH}",
            file=sys.stderr,
        )
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.CLIENT_SECRET_PATH), config.SCOPES
    )
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    email = _fetch_email(creds)
    expiry = (
        creds.expiry.replace(microsecond=0).isoformat() + "Z" if creds.expiry else ""
    )
    AccountStore().save(
        label=label,
        email=email,
        refresh_token=creds.refresh_token,
        access_token=creds.token,
        token_expiry=expiry,
        scopes=list(creds.scopes or config.SCOPES),
    )
    print(f"Saved account '{label}' (email: {email})")
    return 0


def _cmd_list() -> int:
    accounts = AccountStore().list()
    if not accounts:
        print("(no accounts configured)")
        return 0
    width = max(len(a.label) for a in accounts)
    for a in accounts:
        print(f"  {a.label.ljust(width)}  {a.email}")
    return 0


def _cmd_remove(label: str) -> int:
    try:
        AccountStore().remove(label)
    except AccountNotConfigured as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Removed account '{label}'")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="multi-google-mcp-auth")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Authenticate and add a new account")
    p_add.add_argument("label", help="Local label, e.g. 'work' or 'personal'")

    sub.add_parser("list", help="List configured accounts")

    p_rm = sub.add_parser("remove", help="Remove a configured account")
    p_rm.add_argument("label", help="Account label to remove")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "add":
            return _cmd_add(args.label)
        if args.cmd == "list":
            return _cmd_list()
        if args.cmd == "remove":
            return _cmd_remove(args.label)
    except OAuthClientNotConfigured as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
