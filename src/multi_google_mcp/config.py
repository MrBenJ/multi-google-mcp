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
