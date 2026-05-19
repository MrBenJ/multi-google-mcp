from unittest.mock import patch

from multi_google_mcp.server import TOOL_REGISTRY, _invoke_tool, build_app


def test_tool_registry_has_17_tools():
    assert len(TOOL_REGISTRY) == 17


def test_tool_registry_includes_all_expected_names():
    expected = {
        "list_accounts",
        "gmail_search",
        "gmail_get_message",
        "gmail_send",
        "gmail_modify_labels",
        "calendar_list_calendars",
        "calendar_list_events",
        "calendar_get_event",
        "calendar_create_event",
        "calendar_update_event",
        "calendar_delete_event",
        "drive_search",
        "drive_get_file_metadata",
        "drive_read_file",
        "drive_upload_file",
        "drive_update_file",
        "drive_delete_file",
    }
    assert {t["name"] for t in TOOL_REGISTRY} == expected


def test_build_app_returns_a_server_instance():
    app = build_app()
    assert app is not None


def test_invoke_tool_returns_error_for_unknown_tool():
    out = _invoke_tool("does_not_exist", {})
    assert out.startswith("error:")
    assert "does_not_exist" in out


def test_invoke_tool_converts_multi_google_mcp_error_to_text():
    """Existing behaviour: typed account/oauth errors surface cleanly."""
    from multi_google_mcp.exceptions import AccountNotConfigured

    with patch(
        "multi_google_mcp.tools.gmail.gmail_search",
        side_effect=AccountNotConfigured("missing"),
    ):
        out = _invoke_tool(
            "gmail_search", {"account": "missing", "query": "x"}
        )
    assert out.startswith("error:")
    assert "missing" in out


def test_invoke_tool_converts_google_http_error_to_text():
    """Google API errors must not escape as MCP transport failures."""
    from googleapiclient.errors import HttpError

    fake_resp = type("R", (), {"status": 403, "reason": "Forbidden"})()
    http_err = HttpError(fake_resp, b'{"error": "insufficient"}')

    with patch(
        "multi_google_mcp.tools.gmail.gmail_search", side_effect=http_err
    ):
        out = _invoke_tool(
            "gmail_search", {"account": "work", "query": "x"}
        )
    assert out.startswith("error:")
    assert "Google" in out or "HttpError" in out or "403" in out


def test_invoke_tool_converts_value_error_to_text():
    """Invalid base64 (or any ValueError) must not escape."""
    with patch(
        "multi_google_mcp.tools.drive.drive_upload_file",
        side_effect=ValueError("Invalid base64-encoded string"),
    ):
        out = _invoke_tool(
            "drive_upload_file",
            {
                "account": "work",
                "name": "f.bin",
                "content": "$$$not-base64$$$",
                "mime_type": "application/octet-stream",
            },
        )
    assert out.startswith("error:")


def test_invoke_tool_converts_type_error_for_unexpected_kwarg():
    """An extra/unknown argument in the call dict must surface as error text."""
    out = _invoke_tool(
        "gmail_search",
        {"account": "work", "query": "x", "no_such_kwarg": 42},
    )
    assert out.startswith("error:")
