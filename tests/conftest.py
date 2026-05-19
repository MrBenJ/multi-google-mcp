import json
from pathlib import Path
from unittest.mock import MagicMock

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


@pytest.fixture
def saved_account(tmp_config_dir: Path) -> str:
    """A fully-saved 'work' account on disk + a fake client_secret.json."""
    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")
    (tmp_config_dir / "client_secret.json").write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "fake.apps.googleusercontent.com",
                    "client_secret": "fakesecret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        )
    )
    return "work"


@pytest.fixture
def mock_build(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch googleapiclient.discovery.build inside tool modules.

    Returns {"service": MagicMock, "builds": [(api, version), ...]} so tests
    can configure the mocked service and assert what was built. Only patches
    tool modules that already import successfully — earlier tasks in the
    plan only have tools.gmail, later tasks add the others.
    """
    import importlib

    service = MagicMock()
    builds: list[tuple[str, str]] = []

    def fake_build(api: str, version: str, **kwargs):
        builds.append((api, version))
        return service

    for mod_path in (
        "multi_google_mcp.tools.gmail",
        "multi_google_mcp.tools.calendar",
        "multi_google_mcp.tools.drive",
    ):
        try:
            mod = importlib.import_module(mod_path)
        except ImportError:
            continue
        monkeypatch.setattr(mod, "build", fake_build)
    return {"service": service, "builds": builds}
