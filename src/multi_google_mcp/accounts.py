"""Per-account credential storage and refresh."""

from __future__ import annotations

import builtins
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

from multi_google_mcp import config
from multi_google_mcp.exceptions import (
    AccountNeedsReauth,
    AccountNotConfigured,
    OAuthClientNotConfigured,
)


@dataclass(frozen=True)
class AccountInfo:
    label: str
    email: str


class AccountStore:
    """Reads, writes, and refreshes per-account token files."""

    def _path(self, label: str) -> Path:
        return config.ACCOUNTS_DIR / f"{label}.json"

    def _load_client_config(self) -> dict[str, Any]:
        if not config.CLIENT_SECRET_PATH.exists():
            raise OAuthClientNotConfigured()
        raw = json.loads(config.CLIENT_SECRET_PATH.read_text())
        installed = raw.get("installed") or raw.get("web") or raw
        return cast(dict[str, Any], installed)

    def list(self) -> builtins.list[AccountInfo]:
        if not config.ACCOUNTS_DIR.exists():
            return []
        out: builtins.list[AccountInfo] = []
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
        scopes: builtins.list[str],
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

    def remove(self, label: str) -> None:
        path = self._path(label)
        if not path.exists():
            raise AccountNotConfigured(label)
        path.unlink()

    def credentials(self, label: str) -> Credentials:
        """Return a Google Credentials object for the given account label.

        Caller passes this to googleapiclient.discovery.build. If the access
        token is expired, call refresh_if_needed afterwards to persist the
        refreshed token back to disk.
        """
        path = self._path(label)
        if not path.exists():
            raise AccountNotConfigured(label)
        data = json.loads(path.read_text())
        client = self._load_client_config()

        expiry: dt.datetime | None = None
        if data.get("token_expiry"):
            expiry = dt.datetime.fromisoformat(
                data["token_expiry"].replace("Z", "+00:00")
            ).replace(tzinfo=None)

        creds = Credentials(  # type: ignore[no-untyped-call]
            token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_uri=client["token_uri"],
            client_id=client["client_id"],
            client_secret=client["client_secret"],
            scopes=data["scopes"],
        )
        if expiry is not None:
            creds.expiry = expiry
        return creds

    def refresh_if_needed(
        self, label: str, creds: Credentials, *, force: bool = False
    ) -> Credentials:
        """Refresh the credentials if expired (or if force=True) and persist."""
        if not (force or (creds.expired and creds.refresh_token)):
            return creds
        try:
            creds.refresh(GoogleRequest())  # type: ignore[no-untyped-call]
        except Exception as e:
            # invalid_grant means the refresh token is gone (revoked, expired,
            # or scopes changed). Caller needs to rerun `auth_cli add <label>`.
            if "invalid_grant" in str(e):
                raise AccountNeedsReauth(label) from e
            raise
        self._on_refresh(label, creds)
        return creds

    def _on_refresh(self, label: str, creds: Credentials) -> None:
        """Persist refreshed access token + expiry back to disk."""
        path = self._path(label)
        data = json.loads(path.read_text())
        data["access_token"] = creds.token
        if creds.expiry is not None:
            data["token_expiry"] = (
                creds.expiry.replace(microsecond=0).isoformat() + "Z"
            )
        path.write_text(json.dumps(data))
        os.chmod(path, 0o600)
