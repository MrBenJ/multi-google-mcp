import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from multi_google_mcp.auth_cli import main as auth_main


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


def test_add_runs_oauth_flow_and_writes_account_file(tmp_config_dir: Path, capsys):
    _write_fake_client_secret(tmp_config_dir)

    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh-from-flow"
    fake_creds.token = "access-from-flow"
    fake_creds.expiry = None
    fake_creds.scopes = ["https://www.googleapis.com/auth/gmail.modify"]

    with patch("multi_google_mcp.auth_cli.InstalledAppFlow") as flow_cls, patch(
        "multi_google_mcp.auth_cli._fetch_email", return_value="alice@example.com"
    ):
        flow_cls.from_client_secrets_file.return_value.run_local_server.return_value = (
            fake_creds
        )
        exit_code = auth_main(["add", "work"])

    assert exit_code == 0
    saved = json.loads((tmp_config_dir / "accounts" / "work.json").read_text())
    assert saved["label"] == "work"
    assert saved["email"] == "alice@example.com"
    assert saved["refresh_token"] == "refresh-from-flow"


def test_add_errors_when_client_secret_missing(tmp_config_dir: Path, capsys):
    exit_code = auth_main(["add", "work"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "client_secret.json" in err


def test_list_prints_empty_message_when_no_accounts(tmp_config_dir: Path, capsys):
    exit_code = auth_main(["list"])
    assert exit_code == 0
    assert "no accounts" in capsys.readouterr().out.lower()


def test_list_prints_label_and_email(tmp_config_dir: Path, capsys):
    from tests.conftest import write_account_file

    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")
    write_account_file(tmp_config_dir / "accounts", "personal", "bob@example.com")

    exit_code = auth_main(["list"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "work" in out and "alice@example.com" in out
    assert "personal" in out and "bob@example.com" in out


def test_remove_deletes_account_file(tmp_config_dir: Path, capsys):
    from tests.conftest import write_account_file

    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")

    exit_code = auth_main(["remove", "work"])
    assert exit_code == 0
    assert not (tmp_config_dir / "accounts" / "work.json").exists()


def test_remove_errors_when_account_unknown(tmp_config_dir: Path, capsys):
    exit_code = auth_main(["remove", "ghost"])
    assert exit_code == 1
    assert "ghost" in capsys.readouterr().err
