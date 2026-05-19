from multi_google_mcp.shaping.drive import export_mime_for, shape_file_metadata


def test_shape_file_metadata_picks_key_fields():
    raw = {
        "id": "f-1",
        "name": "Notes",
        "mimeType": "application/vnd.google-apps.document",
        "size": "0",
        "parents": ["folder-1"],
        "modifiedTime": "2026-05-18T20:00:00Z",
        "webViewLink": "https://docs.google.com/document/d/f-1/edit",
    }
    assert shape_file_metadata(raw) == {
        "id": "f-1",
        "name": "Notes",
        "mime": "application/vnd.google-apps.document",
        "size": 0,
        "parents": ["folder-1"],
        "modified_time": "2026-05-18T20:00:00Z",
        "web_view_link": "https://docs.google.com/document/d/f-1/edit",
    }


def test_shape_file_metadata_handles_missing_optional_fields():
    raw = {"id": "f-1", "name": "Untitled", "mimeType": "text/plain"}
    out = shape_file_metadata(raw)
    assert out["size"] == 0
    assert out["parents"] == []


def test_export_mime_for_google_doc_returns_text_plain():
    assert export_mime_for("application/vnd.google-apps.document") == "text/plain"


def test_export_mime_for_google_sheet_returns_csv():
    assert export_mime_for("application/vnd.google-apps.spreadsheet") == "text/csv"


def test_export_mime_for_google_slides_returns_text_plain():
    assert export_mime_for("application/vnd.google-apps.presentation") == "text/plain"


def test_export_mime_for_non_google_returns_none():
    assert export_mime_for("application/pdf") is None
