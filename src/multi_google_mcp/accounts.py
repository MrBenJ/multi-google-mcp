"""Per-account credential storage and refresh."""

from __future__ import annotations

import builtins
import contextlib
import datetime as dt
import fcntl
import json
import os
import re
import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

from multi_google_mcp import config
from multi_google_mcp.exceptions import (
    AccountNeedsReauth,
    AccountNotConfigured,
    InvalidAccountLabel,
    OAuthClientNotConfigured,
)

# Slug pattern: alphanumerics, hyphen, underscore. 1-64 chars. Anything else
# risks path traversal into ACCOUNTS_DIR via labels like "../../etc/passwd".
_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_label(label: str) -> None:
    if not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
        raise InvalidAccountLabel(label)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON to path atomically with mode 0o600 from the start.

    The temp file is opened via os.open with O_CREAT|O_EXCL|O_WRONLY and
    mode 0o600 so the refresh tokens are never momentarily readable by
    other local users under a permissive umask (e.g. 0o022 would otherwise
    leave them at 0o644). os.replace is atomic on POSIX, so a partial
    write can't corrupt the live token file. A leftover .tmp.* file in
    the unlikely failure window is harmless.
    """
    tmp_path = path.with_name(f"{path.name}.tmp.{secrets.token_hex(8)}")
    try:
        fd = os.open(tmp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump(payload, fh)
            fh.flush()
            os.fsync(fh.fileno())
        # Belt-and-braces in case the platform ignored the open mode.
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise


@contextlib.contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Advisory exclusive lock on a sidecar .lock file.

    Guards the read-modify-write cycle in _on_refresh against another
    instance of the server (or the auth CLI) refreshing the same account
    concurrently. fcntl.flock is process-scoped on POSIX, which is what we
    want for the single-user local deployment.
    """
    lock_path = path.with_name(f"{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


@dataclass(frozen=True)
class AccountInfo:
    label: str
    email: str


class AccountStore:
    """Reads, writes, and refreshes per-account token files."""

    def _path(self, label: str) -> Path:
        _validate_label(label)
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
        with _file_lock(path):
            _atomic_write_json(
                path,
                {
                    "label": label,
                    "email": email,
                    "refresh_token": refresh_token,
                    "access_token": access_token,
                    "token_expiry": token_expiry,
                    "scopes": scopes,
                },
            )

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
        with _file_lock(path):
            data = json.loads(path.read_text())
            data["access_token"] = creds.token
            if creds.expiry is not None:
                data["token_expiry"] = (
                    creds.expiry.replace(microsecond=0).isoformat() + "Z"
                )
            _atomic_write_json(path, data)
