from multi_google_mcp.shaping.calendar import shape_calendar, shape_event


def test_shape_calendar_picks_basic_fields():
    raw = {
        "id": "primary",
        "summary": "alice@example.com",
        "primary": True,
        "accessRole": "owner",
        "timeZone": "America/Los_Angeles",
    }
    assert shape_calendar(raw) == {
        "id": "primary",
        "summary": "alice@example.com",
        "primary": True,
        "access_role": "owner",
    }


def test_shape_event_with_datetime_start_end():
    raw = {
        "id": "ev-1",
        "summary": "Standup",
        "start": {"dateTime": "2026-05-19T09:00:00-07:00"},
        "end": {"dateTime": "2026-05-19T09:30:00-07:00"},
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/?eid=abc",
        "attendees": [
            {"email": "a@b.com", "responseStatus": "accepted"},
            {"email": "c@d.com", "responseStatus": "needsAction"},
        ],
        "location": "Zoom",
        "description": "Daily sync",
    }
    out = shape_event(raw)
    assert out["id"] == "ev-1"
    assert out["summary"] == "Standup"
    assert out["start"] == "2026-05-19T09:00:00-07:00"
    assert out["end"] == "2026-05-19T09:30:00-07:00"
    assert out["status"] == "confirmed"
    assert out["html_link"] == "https://calendar.google.com/?eid=abc"
    assert out["attendees"] == [
        {"email": "a@b.com", "response": "accepted"},
        {"email": "c@d.com", "response": "needsAction"},
    ]
    assert out["location"] == "Zoom"
    assert out["description"] == "Daily sync"


def test_shape_event_with_all_day_date_start_end():
    raw = {
        "id": "ev-2",
        "summary": "Holiday",
        "start": {"date": "2026-12-25"},
        "end": {"date": "2026-12-26"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    out = shape_event(raw)
    assert out["start"] == "2026-12-25"
    assert out["end"] == "2026-12-26"
