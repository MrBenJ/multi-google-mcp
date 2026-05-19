"""MCP tool implementations for Google Calendar."""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.calendar import shape_calendar, shape_event

_store = AccountStore()


def _service(account: str) -> Any:
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def calendar_list_calendars(account: str) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = svc.calendarList().list().execute()
    return [shape_calendar(c) for c in listing.get("items", [])]


def calendar_list_events(
    account: str,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    svc = _service(account)
    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        kwargs["timeMin"] = time_min
    if time_max:
        kwargs["timeMax"] = time_max
    if query:
        kwargs["q"] = query
    listing = svc.events().list(**kwargs).execute()
    return [shape_event(e) for e in listing.get("items", [])]


def calendar_get_event(
    account: str, calendar_id: str, event_id: str
) -> dict[str, Any]:
    svc = _service(account)
    ev = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return shape_event(ev)


def _time_node(value: str) -> dict[str, str]:
    """Allow either 'YYYY-MM-DD' (all-day) or full RFC3339 datetime."""
    if "T" in value:
        return {"dateTime": value}
    return {"date": value}


def calendar_create_event(
    account: str,
    calendar_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    attendees: list[str] | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {
        "summary": summary,
        "start": _time_node(start),
        "end": _time_node(end),
    }
    if description:
        body["description"] = description
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    if location:
        body["location"] = location
    ev = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return shape_event(ev)


def calendar_update_event(
    account: str,
    calendar_id: str,
    event_id: str,
    summary: str | None = None,
    description: str | None = None,
    start: str | None = None,
    end: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if start is not None:
        body["start"] = _time_node(start)
    if end is not None:
        body["end"] = _time_node(end)
    if location is not None:
        body["location"] = location
    if attendees is not None:
        body["attendees"] = [{"email": e} for e in attendees]
    ev = (
        svc.events()
        .patch(calendarId=calendar_id, eventId=event_id, body=body)
        .execute()
    )
    return shape_event(ev)


def calendar_delete_event(
    account: str, calendar_id: str, event_id: str
) -> dict[str, Any]:
    svc = _service(account)
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"deleted": True, "id": event_id}
