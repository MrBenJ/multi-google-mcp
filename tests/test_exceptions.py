from multi_google_mcp.exceptions import (
    AccountNeedsReauth,
    AccountNotConfigured,
    OAuthClientNotConfigured,
)


def test_account_not_configured_message_includes_label():
    err = AccountNotConfigured("work")
    assert "work" in str(err)
    assert "multi-google-mcp-auth add work" in str(err)


def test_account_needs_reauth_message_includes_label():
    err = AccountNeedsReauth("personal")
    assert "personal" in str(err)
    assert "multi-google-mcp-auth add personal" in str(err)


def test_oauth_client_not_configured_message_references_readme():
    err = OAuthClientNotConfigured()
    assert "client_secret.json" in str(err) or "OAuth client" in str(err)
    assert "README" in str(err)
