import base64

from multi_google_mcp.shaping.gmail import (
    extract_body_text,
    shape_message_full,
    shape_message_summary,
)


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


SAMPLE_MESSAGE = {
    "id": "msg-1",
    "threadId": "thr-1",
    "labelIds": ["INBOX", "UNREAD"],
    "snippet": "Hello there",
    "internalDate": "1715990400000",
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [
            {"name": "From", "value": "Alice <a@b.com>"},
            {"name": "To", "value": "bob@c.com"},
            {"name": "Subject", "value": "Hi"},
            {"name": "Date", "value": "Sat, 18 May 2026 00:00:00 +0000"},
        ],
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64url("plain body")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": _b64url("<p>html body</p>")},
            },
        ],
    },
}


def test_shape_message_summary_picks_key_fields():
    out = shape_message_summary(SAMPLE_MESSAGE)
    assert out == {
        "id": "msg-1",
        "thread_id": "thr-1",
        "from": "Alice <a@b.com>",
        "to": "bob@c.com",
        "subject": "Hi",
        "snippet": "Hello there",
        "date": "Sat, 18 May 2026 00:00:00 +0000",
        "labels": ["INBOX", "UNREAD"],
    }


def test_extract_body_text_prefers_text_plain():
    assert extract_body_text(SAMPLE_MESSAGE["payload"]) == "plain body"


def test_extract_body_text_falls_back_to_html_stripped():
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64url("<p>only html</p>")},
    }
    assert "only html" in extract_body_text(payload)
    assert "<" not in extract_body_text(payload)


def test_shape_message_full_includes_body_and_attachments():
    msg = {
        **SAMPLE_MESSAGE,
        "payload": {
            **SAMPLE_MESSAGE["payload"],
            "parts": [
                *SAMPLE_MESSAGE["payload"]["parts"],
                {
                    "mimeType": "application/pdf",
                    "filename": "report.pdf",
                    "body": {"size": 12345, "attachmentId": "att-1"},
                },
            ],
        },
    }
    out = shape_message_full(msg)
    assert out["body_text"] == "plain body"
    assert out["attachments"] == [
        {
            "filename": "report.pdf",
            "mime": "application/pdf",
            "size": 12345,
            "attachment_id": "att-1",
        }
    ]
