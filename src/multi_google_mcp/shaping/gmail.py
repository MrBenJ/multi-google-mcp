"""Shape raw Gmail API payloads into compact dicts."""

from __future__ import annotations

import base64
import re
from typing import Any


def _b64url_decode(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode(errors="replace")


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}


def _strip_html(html: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", " ", no_tags).strip()


def extract_body_text(payload: dict[str, Any]) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    if mime == "text/plain" and body.get("data"):
        return _b64url_decode(body["data"])
    if mime == "text/html" and body.get("data"):
        return _strip_html(_b64url_decode(body["data"]))
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])
    for part in payload.get("parts", []):
        text = extract_body_text(part)
        if text:
            return text
    return ""


def _extract_attachments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for part in payload.get("parts", []):
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            out.append(
                {
                    "filename": part["filename"],
                    "mime": part.get("mimeType", "application/octet-stream"),
                    "size": part["body"].get("size", 0),
                    "attachment_id": part["body"]["attachmentId"],
                }
            )
        out.extend(_extract_attachments(part))
    return out


def shape_message_summary(msg: dict[str, Any]) -> dict[str, Any]:
    headers = _headers_to_dict(msg.get("payload", {}).get("headers", []))
    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "snippet": msg.get("snippet", ""),
        "date": headers.get("date", ""),
        "labels": msg.get("labelIds", []),
    }


def shape_message_full(msg: dict[str, Any]) -> dict[str, Any]:
    summary = shape_message_summary(msg)
    payload = msg.get("payload", {})
    return {
        **summary,
        "body_text": extract_body_text(payload),
        "attachments": _extract_attachments(payload),
    }
