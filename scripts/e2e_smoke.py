"""End-to-end smoke test for multi-google-mcp.

Spawns the actual MCP server as a subprocess, drives every tool surface
against a real Google account over stdio, and cleans up after itself.

Usage:
    MCP_E2E_ACCOUNT=test-account uv run python scripts/e2e_smoke.py

The named account must already be configured via:
    multi-google-mcp-auth add test-account
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ACCOUNT_ENV = "MCP_E2E_ACCOUNT"


def _now_tag() -> str:
    return f"mcp-e2e-{uuid.uuid4().hex[:8]}"


async def _call(session: ClientSession, name: str, args: dict) -> dict | list:
    result = await session.call_tool(name, args)
    payload = result.content[0].text
    if payload.startswith("error:"):
        raise RuntimeError(payload)
    return json.loads(payload)


async def _gmail_flow(session: ClientSession, account: str) -> None:
    tag = _now_tag()
    accounts = await _call(session, "list_accounts", {})
    self_email = next(a["email"] for a in accounts if a["label"] == account)

    print(f"  gmail: sending self-email with tag {tag}")
    sent = await _call(
        session,
        "gmail_send",
        {
            "account": account,
            "to": self_email,
            "subject": tag,
            "body": "smoke test",
        },
    )

    print("  gmail: searching for the message")
    await asyncio.sleep(2)
    hits = await _call(
        session,
        "gmail_search",
        {"account": account, "query": tag, "max_results": 5},
    )
    if not hits:
        raise RuntimeError(f"sent message with tag {tag} not searchable")

    print("  gmail: trashing the sent message")
    await _call(
        session,
        "gmail_modify_labels",
        {"account": account, "message_id": sent["id"], "trash": True},
    )


async def _calendar_flow(session: ClientSession, account: str) -> None:
    start = dt.datetime.utcnow() + dt.timedelta(days=365)
    end = start + dt.timedelta(hours=1)
    start_str = start.strftime("%Y-%m-%dT%H:%M:00Z")
    end_str = end.strftime("%Y-%m-%dT%H:%M:00Z")
    summary = _now_tag()

    print(f"  calendar: creating event {summary}")
    created = await _call(
        session,
        "calendar_create_event",
        {
            "account": account,
            "calendar_id": "primary",
            "summary": summary,
            "start": start_str,
            "end": end_str,
        },
    )

    print("  calendar: fetching event")
    fetched = await _call(
        session,
        "calendar_get_event",
        {"account": account, "calendar_id": "primary", "event_id": created["id"]},
    )
    if fetched["summary"] != summary:
        raise RuntimeError("calendar round-trip mismatch")

    print("  calendar: deleting event")
    await _call(
        session,
        "calendar_delete_event",
        {"account": account, "calendar_id": "primary", "event_id": created["id"]},
    )


async def _drive_flow(session: ClientSession, account: str) -> None:
    name = f"{_now_tag()}.txt"
    print(f"  drive: uploading {name}")
    uploaded = await _call(
        session,
        "drive_upload_file",
        {
            "account": account,
            "name": name,
            "content": "smoke test content",
            "mime_type": "text/plain",
        },
    )

    print("  drive: reading it back")
    read_back = await _call(
        session,
        "drive_read_file",
        {"account": account, "file_id": uploaded["id"]},
    )
    if read_back["content"] != "smoke test content":
        raise RuntimeError("drive round-trip content mismatch")

    print("  drive: deleting it")
    await _call(
        session,
        "drive_delete_file",
        {"account": account, "file_id": uploaded["id"]},
    )


async def main() -> int:
    account = os.environ.get(ACCOUNT_ENV)
    if not account:
        print(
            f"set {ACCOUNT_ENV} to the account label to run against.",
            file=sys.stderr,
        )
        return 1

    params = StdioServerParameters(command="multi-google-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"discovered {len(tools.tools)} tools over stdio")

            print("gmail flow:")
            await _gmail_flow(session, account)
            print("calendar flow:")
            await _calendar_flow(session, account)
            print("drive flow:")
            await _drive_flow(session, account)

    print("smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
