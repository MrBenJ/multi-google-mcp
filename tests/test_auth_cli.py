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
