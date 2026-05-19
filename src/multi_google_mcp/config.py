"""Paths and OAuth scopes for the multi-google-mcp server."""

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "multi-google-mcp"
ACCOUNTS_DIR = CONFIG_DIR / "accounts"
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Cap on Drive payload size (read or upload) so a 1 GB PDF can't hang the MCP
# transport or flood the model context. 10 MiB is enough for normal docs but
# small enough that a stray request to a huge file fails fast.
MAX_DRIVE_BYTES = 10 * 1024 * 1024
