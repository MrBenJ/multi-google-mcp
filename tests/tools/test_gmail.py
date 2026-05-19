import base64
from unittest.mock import MagicMock

from multi_google_mcp.tools.gmail import gmail_get_message, gmail_search


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def test_gmail_search_returns_shaped_summaries(saved_account, mock_build):
    service = mock_build["service"]

    service.users().messages().list().execute.return_value = {
        "messages": [
            {"id": "m1", "threadId": "t1"},
            {"id": "m2", "threadId": "t2"},
        ]
    }

    def get_execute(userId, id, format):  # noqa: A002
        return {
            "id": id,
            "threadId": f"thr-{id}",
            "labelIds": ["INBOX"],
            "snippet": f"snippet for {id}",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <a@b.com>"},
                    {"name": "Subject", "value": f"Subj {id}"},
                    {"name": "Date", "value": "Sat, 18 May 2026"},
                ]
            },
        }

    service.users().messages().get.side_effect = lambda **kw: MagicMock(
        execute=lambda: get_execute(**kw)
    )

    out = gmail_search("work", query="is:unread", max_results=2)
    assert len(out) == 2
    assert out[0]["id"] == "m1"
    assert out[0]["from"] == "Alice <a@b.com>"
    assert out[1]["subject"] == "Subj m2"


def test_gmail_get_message_returns_full_with_body(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().get().execute.return_value = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "snippet",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "a@b.com"},
                {"name": "Subject", "value": "Hi"},
            ],
            "body": {"data": _b64url("hello world")},
        },
    }

    out = gmail_get_message("work", message_id="m1")
    assert out["id"] == "m1"
    assert out["body_text"] == "hello world"
