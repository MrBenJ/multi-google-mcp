from pathlib import Path

from multi_google_mcp import config


def test_config_dir_uses_home():
    assert config.CONFIG_DIR == Path.home() / ".config" / "multi-google-mcp"


def test_accounts_dir_lives_under_config_dir():
    assert config.ACCOUNTS_DIR == config.CONFIG_DIR / "accounts"


def test_client_secret_path():
    assert config.CLIENT_SECRET_PATH == config.CONFIG_DIR / "client_secret.json"


def test_scopes_include_all_three_apis():
    assert "https://www.googleapis.com/auth/gmail.modify" in config.SCOPES
    assert "https://www.googleapis.com/auth/calendar" in config.SCOPES
    assert "https://www.googleapis.com/auth/drive" in config.SCOPES
    assert "https://www.googleapis.com/auth/userinfo.email" in config.SCOPES
