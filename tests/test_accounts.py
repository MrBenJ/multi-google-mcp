import datetime as dt
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from multi_google_mcp.accounts import AccountInfo, AccountStore
from multi_google_mcp.exceptions import (
    AccountNeedsReauth,
    AccountNotConfigured,
    InvalidAccountLabel,
    OAuthClientNotConfigured,
)
from tests.conftest import write_account_file


def _write_fake_client_secret(tmp_config_dir: Path) -> None:
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


def test_credentials_raises_when_label_unknown(tmp_config_dir: Path):
    with pytest.raises(AccountNotConfigured) as excinfo:
        AccountStore().credentials("nope")
    assert "nope" in str(excinfo.value)


def test_credentials_raises_when_client_secret_missing(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    with pytest.raises(OAuthClientNotConfigured):
        AccountStore().credentials("work")


def test_credentials_returns_google_credentials_from_disk(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)

    creds = AccountStore().credentials("work")
    assert creds.refresh_token == "refresh-xyz"
    assert creds.token == "access-xyz"
    assert creds.client_id == "fake.apps.googleusercontent.com"


def test_credentials_refresh_writes_back_new_access_token(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()

    creds = store.credentials("work")
    creds.token = "NEW-access-token"  # type: ignore[misc]
    creds.expiry = dt.datetime(2099, 12, 31, 0, 0, 0)  # type: ignore[misc]
    store._on_refresh("work", creds)

    data = json.loads((tmp_config_dir / "accounts" / "work.json").read_text())
    assert data["access_token"] == "NEW-access-token"


@pytest.mark.parametrize(
    "evil_label",
    [
        "../escape",
        "../../etc/passwd",
        "subdir/leak",
        "back\\slash",
        ".hidden",
        "..",
        "",
        "has space",
        "a" * 65,  # over length cap
    ],
)
def test_save_rejects_malicious_labels(tmp_config_dir: Path, evil_label: str):
    store = AccountStore()
    with pytest.raises(InvalidAccountLabel):
        store.save(
            label=evil_label,
            email="x@y.com",
            refresh_token="r",
            access_token="a",
            token_expiry="2099-01-01T00:00:00Z",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )


@pytest.mark.parametrize("evil_label", ["../escape", "subdir/leak", ".hidden", ".."])
def test_credentials_rejects_malicious_labels(tmp_config_dir: Path, evil_label: str):
    with pytest.raises(InvalidAccountLabel):
        AccountStore().credentials(evil_label)


@pytest.mark.parametrize("evil_label", ["../escape", "subdir/leak", ".hidden", ".."])
def test_remove_rejects_malicious_labels(tmp_config_dir: Path, evil_label: str):
    with pytest.raises(InvalidAccountLabel):
        AccountStore().remove(evil_label)


def test_save_does_not_create_files_outside_accounts_dir(tmp_config_dir: Path):
    """Even if validation were bypassed, the resolved path stays in ACCOUNTS_DIR.

    This is a belt-and-braces test against future regressions.
    """
    store = AccountStore()
    with pytest.raises(InvalidAccountLabel):
        store.save(
            label="../../../tmp/leaked",
            email="x@y.com",
            refresh_token="r",
            access_token="a",
            token_expiry="2099-01-01T00:00:00Z",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )
    assert not (tmp_config_dir.parent / "tmp" / "leaked.json").exists()


def test_save_leaves_no_temp_files_behind(tmp_config_dir: Path):
    store = AccountStore()
    store.save(
        label="work",
        email="a@b.com",
        refresh_token="r",
        access_token="a",
        token_expiry="2099-01-01T00:00:00Z",
        scopes=["s"],
    )
    leftovers = list((tmp_config_dir / "accounts").glob("*.tmp.*"))
    assert leftovers == []


def test_on_refresh_leaves_no_temp_files_behind(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()
    creds = store.credentials("work")
    creds.token = "NEW"  # type: ignore[misc]
    creds.expiry = dt.datetime(2099, 12, 31)  # type: ignore[misc]
    store._on_refresh("work", creds)
    leftovers = list((tmp_config_dir / "accounts").glob("*.tmp.*"))
    assert leftovers == []


def test_atomic_write_creates_temp_file_with_mode_0600_under_permissive_umask(
    tmp_config_dir: Path,
):
    """Temp file must be created with restrictive perms from the START.

    Forces umask 022 (the common default) and patches os.chmod to a no-op,
    so the only way the final mode can be 0o600 is if the file was opened
    with that mode in the first place. If the implementation falls back to
    plain open() then chmod 600, this test will see 0o644 and fail —
    catching the secret-exposure window Aria flagged.
    """
    captured_modes: list[int] = []
    real_replace = os.replace

    def probe_replace(src, dst):
        captured_modes.append(os.stat(src).st_mode & 0o777)
        return real_replace(src, dst)

    old_umask = os.umask(0o022)
    try:
        with patch("multi_google_mcp.accounts.os.chmod"), patch(
            "multi_google_mcp.accounts.os.replace", side_effect=probe_replace
        ):
            AccountStore().save(
                label="work",
                email="a@b.com",
                refresh_token="r",
                access_token="a",
                token_expiry="2099-01-01T00:00:00Z",
                scopes=["s"],
            )
    finally:
        os.umask(old_umask)

    assert captured_modes == [0o600], (
        f"temp file was created with mode {captured_modes!r} — "
        "secrets exposed during the open->chmod window"
    )


def test_on_refresh_preserves_original_on_replace_error(tmp_config_dir: Path):
    """If the atomic replace fails mid-way, the original token must survive.

    We monkey-patch os.replace to blow up after the tmp file has been written
    and assert the original file is untouched. The .tmp.* file may linger
    (that's the expected failure mode for transient I/O issues) — what
    matters is that the live token is not corrupted.
    """
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()
    creds = store.credentials("work")
    creds.token = "NEW"  # type: ignore[misc]
    creds.expiry = dt.datetime(2099, 12, 31)  # type: ignore[misc]

    original_data = (tmp_config_dir / "accounts" / "work.json").read_text()
    with patch(
        "multi_google_mcp.accounts.os.replace",
        side_effect=OSError("simulated"),
    ), pytest.raises(OSError):
        store._on_refresh("work", creds)
    assert (
        tmp_config_dir / "accounts" / "work.json"
    ).read_text() == original_data


def test_credentials_raises_account_needs_reauth_on_invalid_grant(tmp_config_dir: Path):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()
    creds = store.credentials("work")

    with patch.object(creds, "refresh", side_effect=Exception("invalid_grant")):
        with pytest.raises(AccountNeedsReauth) as excinfo:
            store.refresh_if_needed("work", creds, force=True)
        assert "work" in str(excinfo.value)
