"""Per-account credential storage and refresh."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from multi_google_mcp import config


@dataclass(frozen=True)
class AccountInfo:
    label: str
    email: str


class AccountStore:
    """Reads and writes per-account token files under config.ACCOUNTS_DIR."""

    def _path(self, label: str) -> Path:
        return config.ACCOUNTS_DIR / f"{label}.json"

    def list(self) -> list[AccountInfo]:
        if not config.ACCOUNTS_DIR.exists():
            return []
        out: list[AccountInfo] = []
        for path in sorted(config.ACCOUNTS_DIR.glob("*.json")):
            data = json.loads(path.read_text())
            out.append(AccountInfo(label=data["label"], email=data["email"]))
        return out

    def save(
        self,
        *,
        label: str,
        email: str,
        refresh_token: str,
        access_token: str,
        token_expiry: str,
        scopes: list[str],
    ) -> None:
        config.ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        path = self._path(label)
        path.write_text(
            json.dumps(
                {
                    "label": label,
                    "email": email,
                    "refresh_token": refresh_token,
                    "access_token": access_token,
                    "token_expiry": token_expiry,
                    "scopes": scopes,
                }
            )
        )
        os.chmod(path, 0o600)
