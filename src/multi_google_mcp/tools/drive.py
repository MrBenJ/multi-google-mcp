"""MCP tool implementations for Google Drive."""

from __future__ import annotations

import base64
import io
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.drive import export_mime_for, shape_file_metadata

_store = AccountStore()

_DEFAULT_FIELDS = "id,name,mimeType,size,parents,modifiedTime,webViewLink"


def _service(account: str) -> Any:
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def drive_search(
    account: str, query: str, max_results: int = 10
) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = (
        svc.files()
        .list(q=query, pageSize=max_results, fields=f"files({_DEFAULT_FIELDS})")
        .execute()
    )
    return [shape_file_metadata(f) for f in listing.get("files", [])]


def drive_get_file_metadata(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    raw = svc.files().get(fileId=file_id, fields=_DEFAULT_FIELDS).execute()
    return shape_file_metadata(raw)


def drive_read_file(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    meta = svc.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    export_mime = export_mime_for(meta["mimeType"])
    if export_mime:
        raw_bytes: bytes = (
            svc.files().export(fileId=file_id, mimeType=export_mime).execute()
        )
        return {
            "id": meta["id"],
            "name": meta["name"],
            "mime": export_mime,
            "encoding": "text",
            "content": raw_bytes.decode("utf-8", errors="replace"),
        }
    raw_bytes = svc.files().get_media(fileId=file_id).execute()
    return {
        "id": meta["id"],
        "name": meta["name"],
        "mime": meta["mimeType"],
        "encoding": "base64",
        "content": base64.b64encode(raw_bytes).decode("ascii"),
    }


def _media(content: str, mime_type: str) -> MediaIoBaseUpload:
    """Wrap string content (text or base64) into a MediaIoBaseUpload.

    Text-ish mime types are passed through as UTF-8 bytes; anything else
    is decoded from base64 so callers can ship arbitrary binary content.
    """
    if mime_type.startswith("text/") or mime_type in (
        "application/json",
        "application/xml",
    ):
        data = content.encode("utf-8")
    else:
        data = base64.b64decode(content)
    return MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)


def drive_upload_file(
    account: str,
    name: str,
    content: str,
    mime_type: str,
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {"name": name, "mimeType": mime_type}
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
    raw = (
        svc.files()
        .create(
            body=body, media_body=_media(content, mime_type), fields=_DEFAULT_FIELDS
        )
        .execute()
    )
    return shape_file_metadata(raw)


def drive_update_file(
    account: str,
    file_id: str,
    content: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    kwargs: dict[str, Any] = {
        "fileId": file_id,
        "body": body,
        "fields": _DEFAULT_FIELDS,
    }
    if content is not None:
        existing = svc.files().get(fileId=file_id, fields="mimeType").execute()
        kwargs["media_body"] = _media(content, existing["mimeType"])
    raw = svc.files().update(**kwargs).execute()
    return shape_file_metadata(raw)


def drive_delete_file(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    svc.files().delete(fileId=file_id).execute()
    return {"deleted": True, "id": file_id}
