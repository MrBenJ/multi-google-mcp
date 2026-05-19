"""MCP tool implementations for Google Drive."""

from __future__ import annotations

import base64
import io
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from multi_google_mcp import config
from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import DriveFileTooLarge
from multi_google_mcp.shaping.drive import export_mime_for, shape_file_metadata

_store = AccountStore()

_DEFAULT_FIELDS = "id,name,mimeType,size,parents,modifiedTime,webViewLink"

# 1 MiB chunks for streaming reads. Small enough that an oversized native
# export aborts within ~10 chunks of the 10 MiB cap; large enough that the
# common case of a 50 KiB doc takes one round trip.
_DOWNLOAD_CHUNK = 1024 * 1024


def _check_size(size: int) -> None:
    if size > config.MAX_DRIVE_BYTES:
        raise DriveFileTooLarge(size, config.MAX_DRIVE_BYTES)


def _download_chunked(request: Any) -> bytes:
    """Stream a Drive request into memory, aborting if it exceeds the cap.

    Native files (Docs/Sheets/Slides) report size=0 in metadata, so we
    cannot pre-check. MediaIoBaseDownload lets us watch the cumulative
    buffer size between chunks and raise before the entire export is
    materialised.
    """
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request, chunksize=_DOWNLOAD_CHUNK)
    done = False
    while not done:
        _, done = downloader.next_chunk()
        if buf.tell() > config.MAX_DRIVE_BYTES:
            raise DriveFileTooLarge(buf.tell(), config.MAX_DRIVE_BYTES)
    return buf.getvalue()


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
    meta = svc.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
    export_mime = export_mime_for(meta["mimeType"])
    if export_mime:
        # Native files (Docs/Sheets/Slides) report size=0, so we stream and
        # abort if the buffer grows past MAX_DRIVE_BYTES.
        request = svc.files().export(fileId=file_id, mimeType=export_mime)
        raw_bytes = _download_chunked(request)
        return {
            "id": meta["id"],
            "name": meta["name"],
            "mime": export_mime,
            "encoding": "text",
            "content": raw_bytes.decode("utf-8", errors="replace"),
        }
    # Binary file: pre-check from metadata so we never download the body.
    _check_size(int(meta.get("size", 0) or 0))
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
    Raises DriveFileTooLarge if the decoded payload exceeds MAX_DRIVE_BYTES.
    """
    if mime_type.startswith("text/") or mime_type in (
        "application/json",
        "application/xml",
    ):
        data = content.encode("utf-8")
    else:
        data = base64.b64decode(content)
    _check_size(len(data))
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
