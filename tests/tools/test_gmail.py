import base64
from unittest.mock import MagicMock

from multi_google_mcp.tools.gmail import (
    gmail_get_message,
    gmail_modify_labels,
    gmail_search,
    gmail_send,
)


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


def test_gmail_send_builds_rfc822_and_calls_send(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().send().execute.return_value = {"id": "sent-1"}

    out = gmail_send(
        "work",
        to="bob@example.com",
        subject="Hi Bob",
        body="hello",
    )
    assert out == {"id": "sent-1"}
    call_kwargs = service.users().messages().send.call_args.kwargs
    assert call_kwargs["userId"] == "me"
    assert "raw" in call_kwargs["body"]


def test_gmail_modify_labels_add_and_remove(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().modify().execute.return_value = {
        "id": "m1",
        "labelIds": ["INBOX", "Label_1"],
    }

    out = gmail_modify_labels(
        "work", message_id="m1", add=["Label_1"], remove=["UNREAD"]
    )
    assert "Label_1" in out["labels"]
    call_kwargs = service.users().messages().modify.call_args.kwargs
    assert call_kwargs["body"] == {
        "addLabelIds": ["Label_1"],
        "removeLabelIds": ["UNREAD"],
    }


def test_gmail_modify_labels_trash_flag_routes_to_trash_endpoint(
    saved_account, mock_build
):
    service = mock_build["service"]
    service.users().messages().trash().execute.return_value = {
        "id": "m1",
        "labelIds": ["TRASH"],
    }

    out = gmail_modify_labels("work", message_id="m1", trash=True)
    assert "TRASH" in out["labels"]
    service.users().messages().trash.assert_called_with(userId="me", id="m1")
