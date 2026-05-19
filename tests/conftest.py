import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect config.CONFIG_DIR (and derived paths) to a tmp dir."""
    from multi_google_mcp import config

    tmp_cfg = tmp_path / "multi-google-mcp"
    tmp_accounts = tmp_cfg / "accounts"
    tmp_client_secret = tmp_cfg / "client_secret.json"
    tmp_cfg.mkdir()
    tmp_accounts.mkdir()

    monkeypatch.setattr(config, "CONFIG_DIR", tmp_cfg)
    monkeypatch.setattr(config, "ACCOUNTS_DIR", tmp_accounts)
    monkeypatch.setattr(config, "CLIENT_SECRET_PATH", tmp_client_secret)
    return tmp_cfg


def write_account_file(accounts_dir: Path, label: str, email: str) -> Path:
    """Helper for tests to drop a token file on disk."""
    path = accounts_dir / f"{label}.json"
    path.write_text(
        json.dumps(
            {
                "label": label,
                "email": email,
                "refresh_token": "refresh-xyz",
                "access_token": "access-xyz",
                "token_expiry": "2099-01-01T00:00:00Z",
                "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
            }
        )
    )
    return path
