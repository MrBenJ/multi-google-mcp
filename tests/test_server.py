from multi_google_mcp.server import TOOL_REGISTRY, build_app


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
