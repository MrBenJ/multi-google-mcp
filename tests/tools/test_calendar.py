from multi_google_mcp.tools.calendar import (
    calendar_create_event,
    calendar_delete_event,
    calendar_get_event,
    calendar_list_calendars,
    calendar_list_events,
    calendar_update_event,
)


def test_list_calendars_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.calendarList().list().execute.return_value = {
        "items": [
            {
                "id": "primary",
                "summary": "alice@example.com",
                "primary": True,
                "accessRole": "owner",
            }
        ]
    }
    out = calendar_list_calendars("work")
    assert out == [
        {
            "id": "primary",
            "summary": "alice@example.com",
            "primary": True,
            "access_role": "owner",
        }
    ]


def test_list_events_passes_time_window(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().list().execute.return_value = {"items": []}

    out = calendar_list_events(
        "work",
        calendar_id="primary",
        time_min="2026-05-18T00:00:00Z",
        time_max="2026-05-19T00:00:00Z",
        max_results=5,
    )
    assert out == []
    kw = svc.events().list.call_args.kwargs
    assert kw["calendarId"] == "primary"
    assert kw["timeMin"] == "2026-05-18T00:00:00Z"
    assert kw["timeMax"] == "2026-05-19T00:00:00Z"
    assert kw["maxResults"] == 5
    assert kw["singleEvents"] is True
    assert kw["orderBy"] == "startTime"


def test_get_event_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().get().execute.return_value = {
        "id": "ev",
        "summary": "Standup",
        "start": {"dateTime": "2026-05-19T09:00:00Z"},
        "end": {"dateTime": "2026-05-19T09:30:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    out = calendar_get_event("work", calendar_id="primary", event_id="ev")
    assert out["summary"] == "Standup"


def test_create_event_posts_correct_body(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().insert().execute.return_value = {
        "id": "ev-new",
        "summary": "X",
        "start": {"dateTime": "2026-06-01T10:00:00Z"},
        "end": {"dateTime": "2026-06-01T11:00:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    calendar_create_event(
        "work",
        calendar_id="primary",
        summary="X",
        start="2026-06-01T10:00:00Z",
        end="2026-06-01T11:00:00Z",
        attendees=["a@b.com"],
        location="HQ",
    )
    kw = svc.events().insert.call_args.kwargs
    assert kw["calendarId"] == "primary"
    body = kw["body"]
    assert body["summary"] == "X"
    assert body["start"] == {"dateTime": "2026-06-01T10:00:00Z"}
    assert body["end"] == {"dateTime": "2026-06-01T11:00:00Z"}
    assert body["attendees"] == [{"email": "a@b.com"}]
    assert body["location"] == "HQ"


def test_update_event_patches_only_supplied(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().patch().execute.return_value = {
        "id": "ev",
        "summary": "Updated",
        "start": {"dateTime": "2026-06-01T10:00:00Z"},
        "end": {"dateTime": "2026-06-01T11:00:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    calendar_update_event(
        "work", calendar_id="primary", event_id="ev", summary="Updated"
    )
    kw = svc.events().patch.call_args.kwargs
    assert kw["body"] == {"summary": "Updated"}


def test_delete_event_calls_delete(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().delete().execute.return_value = None
    out = calendar_delete_event("work", calendar_id="primary", event_id="ev")
    assert out == {"deleted": True, "id": "ev"}
    svc.events().delete.assert_called_with(calendarId="primary", eventId="ev")
