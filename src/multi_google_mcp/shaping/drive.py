"""Shape raw Drive API payloads + native-format export decisions."""

from __future__ import annotations

from typing import Any

_EXPORT_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def shape_file_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "mime": raw.get("mimeType", ""),
        "size": int(raw.get("size", 0) or 0),
        "parents": raw.get("parents", []),
        "modified_time": raw.get("modifiedTime", ""),
        "web_view_link": raw.get("webViewLink", ""),
    }


def export_mime_for(google_mime: str) -> str | None:
    """Return the export mime type for a Google-native file, or None for binary."""
    return _EXPORT_MAP.get(google_mime)
