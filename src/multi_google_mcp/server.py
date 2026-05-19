"""MCP server entrypoint: register tools, run over stdio."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from googleapiclient.errors import HttpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import MultiGoogleMcpError
from multi_google_mcp.tools import calendar as calendar_tools
from multi_google_mcp.tools import drive as drive_tools
from multi_google_mcp.tools import gmail as gmail_tools


def _list_accounts() -> list[dict[str, str]]:
    return [asdict(a) for a in AccountStore().list()]


# Each entry: {name, description, schema, handler}
TOOL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "list_accounts",
        "description": "List configured Google accounts (label + email).",
        "schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "handler": lambda args: _list_accounts(),
    },
    # Gmail
    {
        "name": "gmail_search",
        "description": "Search Gmail with Gmail query syntax; returns message summaries.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account", "query"],
        },
        "handler": lambda args: gmail_tools.gmail_search(**args),
    },
    {
        "name": "gmail_get_message",
        "description": "Fetch a Gmail message in full (headers, body, attachments).",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "message_id": {"type": "string"},
            },
            "required": ["account", "message_id"],
        },
        "handler": lambda args: gmail_tools.gmail_get_message(**args),
    },
    {
        "name": "gmail_send",
        "description": "Send a Gmail message. Optional html flag and in_reply_to for threading.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "string"},
                "bcc": {"type": "string"},
                "html": {"type": "boolean", "default": False},
                "in_reply_to": {"type": "string"},
            },
            "required": ["account", "to", "subject", "body"],
        },
        "handler": lambda args: gmail_tools.gmail_send(**args),
    },
    {
        "name": "gmail_modify_labels",
        "description": "Add/remove labels on a Gmail message; trash=true moves to trash.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "message_id": {"type": "string"},
                "add": {"type": "array", "items": {"type": "string"}},
                "remove": {"type": "array", "items": {"type": "string"}},
                "trash": {"type": "boolean", "default": False},
            },
            "required": ["account", "message_id"],
        },
        "handler": lambda args: gmail_tools.gmail_modify_labels(**args),
    },
    # Calendar
    {
        "name": "calendar_list_calendars",
        "description": "List calendars the account has access to.",
        "schema": {
            "type": "object",
            "properties": {"account": {"type": "string"}},
            "required": ["account"],
        },
        "handler": lambda args: calendar_tools.calendar_list_calendars(**args),
    },
    {
        "name": "calendar_list_events",
        "description": (
            "List events in a calendar; RFC3339 time_min/time_max bound the window."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string", "default": "primary"},
                "time_min": {"type": "string"},
                "time_max": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account"],
        },
        "handler": lambda args: calendar_tools.calendar_list_events(**args),
    },
    {
        "name": "calendar_get_event",
        "description": "Fetch a single event by id.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_get_event(**args),
    },
    {
        "name": "calendar_create_event",
        "description": (
            "Create a calendar event. start/end accept RFC3339 datetime or "
            "YYYY-MM-DD (all-day)."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "description": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"},
            },
            "required": ["account", "calendar_id", "summary", "start", "end"],
        },
        "handler": lambda args: calendar_tools.calendar_create_event(**args),
    },
    {
        "name": "calendar_update_event",
        "description": "Patch an event; only fields supplied are changed.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "location": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_update_event(**args),
    },
    {
        "name": "calendar_delete_event",
        "description": "Delete an event by id.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_delete_event(**args),
    },
    # Drive
    {
        "name": "drive_search",
        "description": (
            "Search Drive with Drive query syntax (e.g. \"name contains 'foo'\")."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account", "query"],
        },
        "handler": lambda args: drive_tools.drive_search(**args),
    },
    {
        "name": "drive_get_file_metadata",
        "description": (
            "Get file metadata (id, name, mime, size, parents, modified_time, link)."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_get_file_metadata(**args),
    },
    {
        "name": "drive_read_file",
        "description": (
            "Read file content. Google Docs->text, Sheets->CSV (first sheet), "
            "Slides->text; binary returned as base64."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_read_file(**args),
    },
    {
        "name": "drive_upload_file",
        "description": "Upload a new file. content is text or base64 depending on mime_type.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "name": {"type": "string"},
                "content": {"type": "string"},
                "mime_type": {"type": "string"},
                "parent_folder_id": {"type": "string"},
            },
            "required": ["account", "name", "content", "mime_type"],
        },
        "handler": lambda args: drive_tools.drive_upload_file(**args),
    },
    {
        "name": "drive_update_file",
        "description": "Update an existing file's content and/or name.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
                "content": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_update_file(**args),
    },
    {
        "name": "drive_delete_file",
        "description": "Permanently delete a Drive file.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_delete_file(**args),
    },
]


def _invoke_tool(name: str, arguments: dict[str, Any]) -> str:
    """Run a tool by name and return either JSON output or an error: text.

    Every plausible operational failure is converted to a stable "error: ..."
    string so the MCP transport never has to surface a Python exception.
    Categories handled:

    - MultiGoogleMcpError: account/oauth/drive-size errors, surfaced verbatim.
    - HttpError: Google API errors (auth, quota, 4xx, 5xx).
    - ValueError/TypeError/KeyError: malformed arguments (bad base64, wrong
      kwarg names, missing required fields).
    - Anything else: rendered with class name + message so a bug is at least
      diagnosable from the client side without a full traceback.
    """
    entry = next((t for t in TOOL_REGISTRY if t["name"] == name), None)
    if entry is None:
        return f"error: unknown tool {name!r}"
    try:
        result = entry["handler"](arguments or {})
    except MultiGoogleMcpError as e:
        return f"error: {e}"
    except HttpError as e:
        return f"error: Google API error ({e.resp.status}): {e.reason}"
    except (ValueError, TypeError, KeyError) as e:
        return f"error: invalid arguments: {type(e).__name__}: {e}"
    except Exception as e:
        return f"error: internal error: {type(e).__name__}: {e}"
    return json.dumps(result, default=str)


def build_app() -> Server:
    app: Server = Server("multi-google-mcp")

    @app.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["schema"],
            )
            for t in TOOL_REGISTRY
        ]

    @app.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return [TextContent(type="text", text=_invoke_tool(name, arguments))]

    return app


def main() -> None:
    async def runner() -> None:
        async with stdio_server() as (read, write):
            app = build_app()
            await app.run(read, write, app.create_initialization_options())

    asyncio.run(runner())


if __name__ == "__main__":
    main()
