import json
from pathlib import Path

from multi_google_mcp.accounts import AccountInfo, AccountStore
from tests.conftest import write_account_file


def test_list_returns_empty_when_no_accounts(tmp_config_dir: Path):
    assert AccountStore().list() == []


def test_list_returns_label_and_email_for_each_account(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")
    write_account_file(tmp_config_dir / "accounts", "personal", "bob@example.com")

    result = sorted(AccountStore().list(), key=lambda a: a.label)
    assert result == [
        AccountInfo(label="personal", email="bob@example.com"),
        AccountInfo(label="work", email="alice@example.com"),
    ]


def test_save_writes_token_file_chmod_600(tmp_config_dir: Path):
    store = AccountStore()
    store.save(
        label="work",
        email="alice@example.com",
        refresh_token="r",
        access_token="a",
        token_expiry="2099-01-01T00:00:00Z",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )

    path = tmp_config_dir / "accounts" / "work.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["email"] == "alice@example.com"
    assert data["refresh_token"] == "r"
    assert (path.stat().st_mode & 0o777) == 0o600
