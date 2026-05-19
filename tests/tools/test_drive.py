import base64

import pytest

from multi_google_mcp import config
from multi_google_mcp.exceptions import DriveFileTooLarge
from multi_google_mcp.tools.drive import (
    drive_delete_file,
    drive_get_file_metadata,
    drive_read_file,
    drive_search,
    drive_update_file,
    drive_upload_file,
)


def test_drive_search_returns_shaped_metadata(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().list().execute.return_value = {
        "files": [
            {
                "id": "f1",
                "name": "n",
                "mimeType": "text/plain",
                "size": "100",
                "modifiedTime": "2026-05-18T00:00:00Z",
                "webViewLink": "https://...",
            }
        ]
    }
    out = drive_search("work", query="name contains 'n'", max_results=5)
    assert len(out) == 1
    assert out[0]["id"] == "f1"
    kw = svc.files().list.call_args.kwargs
    assert kw["q"] == "name contains 'n'"
    assert kw["pageSize"] == 5
    assert "fields" in kw


def test_drive_get_file_metadata_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "n",
        "mimeType": "text/plain",
    }
    out = drive_get_file_metadata("work", file_id="f1")
    assert out["id"] == "f1"


def test_drive_read_file_exports_google_doc_as_text(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "doc",
        "mimeType": "application/vnd.google-apps.document",
    }
    svc.files().export().execute.return_value = b"document body"

    out = drive_read_file("work", file_id="f1")
    assert out["mime"] == "text/plain"
    assert out["content"] == "document body"
    assert out["encoding"] == "text"
    svc.files().export.assert_called_with(fileId="f1", mimeType="text/plain")


def test_drive_read_file_returns_base64_for_binary(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "img.png",
        "mimeType": "image/png",
    }
    svc.files().get_media().execute.return_value = b"\x89PNG\x0d\x0a"

    out = drive_read_file("work", file_id="f1")
    assert out["mime"] == "image/png"
    assert out["encoding"] == "base64"
    assert base64.b64decode(out["content"]) == b"\x89PNG\x0d\x0a"


def test_drive_upload_file_text(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().create().execute.return_value = {
        "id": "new",
        "name": "n.txt",
        "mimeType": "text/plain",
    }
    out = drive_upload_file("work", name="n.txt", content="hello", mime_type="text/plain")
    assert out["id"] == "new"
    kw = svc.files().create.call_args.kwargs
    assert kw["body"]["name"] == "n.txt"
    assert kw["body"].get("parents") is None or kw["body"].get("parents") == []
    assert kw["media_body"] is not None


def test_drive_update_file_renames_only(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().update().execute.return_value = {
        "id": "f1",
        "name": "new-name.txt",
        "mimeType": "text/plain",
    }
    out = drive_update_file("work", file_id="f1", name="new-name.txt")
    kw = svc.files().update.call_args.kwargs
    assert kw["body"] == {"name": "new-name.txt"}
    assert "media_body" not in kw or kw["media_body"] is None
    assert out["name"] == "new-name.txt"


def test_drive_delete_file_calls_delete(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().delete().execute.return_value = None
    out = drive_delete_file("work", file_id="f1")
    assert out == {"deleted": True, "id": "f1"}
    svc.files().delete.assert_called_with(fileId="f1")


def test_drive_read_file_rejects_oversized_binary_before_download(
    saved_account, mock_build
):
    svc = mock_build["service"]
    too_big = config.MAX_DRIVE_BYTES + 1
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "huge.bin",
        "mimeType": "application/octet-stream",
        "size": str(too_big),
    }

    with pytest.raises(DriveFileTooLarge) as excinfo:
        drive_read_file("work", file_id="f1")
    assert excinfo.value.size == too_big
    # Crucially: we never downloaded the body.
    svc.files().get_media.assert_not_called()


def test_drive_read_file_rejects_oversized_export_after_fetch(
    saved_account, mock_build
):
    """Native files report size=0 in metadata, so we can only check after export."""
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "huge.gdoc",
        "mimeType": "application/vnd.google-apps.document",
    }
    svc.files().export().execute.return_value = b"x" * (config.MAX_DRIVE_BYTES + 1)

    with pytest.raises(DriveFileTooLarge):
        drive_read_file("work", file_id="f1")


def test_drive_upload_file_rejects_oversized_text(saved_account, mock_build):
    big = "x" * (config.MAX_DRIVE_BYTES + 1)
    with pytest.raises(DriveFileTooLarge):
        drive_upload_file(
            "work", name="big.txt", content=big, mime_type="text/plain"
        )


def test_drive_upload_file_rejects_oversized_binary(saved_account, mock_build):
    big = base64.b64encode(b"x" * (config.MAX_DRIVE_BYTES + 1)).decode()
    with pytest.raises(DriveFileTooLarge):
        drive_upload_file(
            "work",
            name="big.bin",
            content=big,
            mime_type="application/octet-stream",
        )
