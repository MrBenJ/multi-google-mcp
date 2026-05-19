"""Shape raw Calendar API payloads."""

from __future__ import annotations

from typing import Any


def shape_calendar(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "summary": raw.get("summary", ""),
        "primary": raw.get("primary", False),
        "access_role": raw.get("accessRole", ""),
    }


def _shape_time(node: dict[str, Any]) -> str:
    return node.get("dateTime") or node.get("date") or ""


def shape_event(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": raw["id"],
        "summary": raw.get("summary", ""),
        "start": _shape_time(raw.get("start", {})),
        "end": _shape_time(raw.get("end", {})),
        "status": raw.get("status", ""),
        "html_link": raw.get("htmlLink", ""),
    }
    if "location" in raw:
        out["location"] = raw["location"]
    if "description" in raw:
        out["description"] = raw["description"]
    if "attendees" in raw:
        out["attendees"] = [
            {"email": a["email"], "response": a.get("responseStatus", "")}
            for a in raw["attendees"]
        ]
    return out
