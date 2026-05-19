"""MCP tool implementations for Gmail."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

from googleapiclient.discovery import build

from multi_google_mcp import config
from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.gmail import shape_message_full, shape_message_summary

_store = AccountStore()


def _truncate_body(body: str) -> str:
    """Return body unchanged if under cap; otherwise truncate with a marker.

    The marker exposes the real original size so the agent knows the body
    was clipped and can decide whether to widen the search or skip the
    message rather than silently working from a partial view.
    """
    raw = body.encode("utf-8")
    if len(raw) <= config.MAX_GMAIL_BODY_BYTES:
        return body
    cut = raw[: config.MAX_GMAIL_BODY_BYTES].decode("utf-8", errors="replace")
    return (
        f"{cut}\n\n[...truncated: {len(raw)} bytes total, "
        f"showing first {config.MAX_GMAIL_BODY_BYTES}]"
    )


def _service(account: str) -> Any:
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def gmail_search(
    account: str, query: str, max_results: int = 10
) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = (
        svc.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    summaries: list[dict[str, Any]] = []
    for ref in listing.get("messages", []):
        msg = (
            svc.users()
            .messages()
            .get(userId="me", id=ref["id"], format="metadata")
            .execute()
        )
        summaries.append(shape_message_summary(msg))
    return summaries


def gmail_get_message(account: str, message_id: str) -> dict[str, Any]:
    svc = _service(account)
    msg = (
        svc.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    shaped = shape_message_full(msg)
    shaped["body_text"] = _truncate_body(shaped["body_text"])
    return shaped


def _build_raw_message(
    *,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    html: bool = False,
    in_reply_to: str | None = None,
) -> str:
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    if html:
        msg.set_content("", subtype="plain")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def gmail_send(
    account: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    html: bool = False,
    in_reply_to: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    raw = _build_raw_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=html,
        in_reply_to=in_reply_to,
    )
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": sent["id"]}


def gmail_modify_labels(
    account: str,
    message_id: str,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    trash: bool = False,
) -> dict[str, Any]:
    svc = _service(account)
    if trash:
        result = svc.users().messages().trash(userId="me", id=message_id).execute()
    else:
        result = (
            svc.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add or [],
                    "removeLabelIds": remove or [],
                },
            )
            .execute()
        )
    return {"id": result["id"], "labels": result.get("labelIds", [])}
