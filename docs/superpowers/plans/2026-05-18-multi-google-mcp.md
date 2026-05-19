# Multi-Google MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local stdio MCP server that lets Claude Desktop operate across multiple Gmail accounts with read+write access to Gmail, Calendar, and Drive, with tokens stored in `~/.config/multi-google-mcp/`.

**Architecture:** Python 3.11+ project packaged with `uv`. One process exposes 17 MCP tools over stdio (1 discovery + 4 Gmail + 6 Calendar + 6 Drive). Every operational tool takes an explicit `account: str` arg routing to a per-label OAuth credential on disk. A standalone CLI handles the OAuth flow outside the MCP server.

**Tech Stack:** Python 3.11+, `uv`, `mcp` Python SDK (stdio), `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `pytest`, `ruff`, `mypy`.

**Spec:** `docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md`

---

## File Structure

```
multi-google-mcp/
├── pyproject.toml
├── README.md
├── .gitignore
├── docs/superpowers/
│   ├── specs/2026-05-18-multi-google-mcp-design.md   (already exists)
│   └── plans/2026-05-18-multi-google-mcp.md          (this file)
├── src/multi_google_mcp/
│   ├── __init__.py
│   ├── config.py                  # paths, scopes constants
│   ├── exceptions.py              # AccountNotConfigured, AccountNeedsReauth, OAuthClientNotConfigured
│   ├── accounts.py                # AccountStore
│   ├── auth_cli.py                # multi-google-mcp-auth CLI
│   ├── server.py                  # MCP entrypoint + tool registration
│   ├── shaping/
│   │   ├── __init__.py
│   │   ├── gmail.py
│   │   ├── calendar.py
│   │   └── drive.py
│   └── tools/
│       ├── __init__.py
│       ├── gmail.py
│       ├── calendar.py
│       └── drive.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # shared fixtures (tmp config dir, mock service builders)
│   ├── test_config.py
│   ├── test_accounts.py
│   ├── test_auth_cli.py
│   ├── shaping/
│   │   ├── test_gmail.py
│   │   ├── test_calendar.py
│   │   └── test_drive.py
│   ├── tools/
│   │   ├── test_gmail.py
│   │   ├── test_calendar.py
│   │   └── test_drive.py
│   └── test_server.py
└── scripts/
    └── e2e_smoke.py
```

---

## Phase A — Foundations

### Task 1: Initialize repository and commit the spec

**Files:**
- Create: `/Users/bjunya/code/multi-google-mcp/.gitignore`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/bjunya/code/multi-google-mcp
git init
```

Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Write .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
dist/
build/

# Project
client_secret.json
accounts/
*.local
.env
```

- [ ] **Step 3: Commit spec + gitignore as initial commit**

```bash
git add .gitignore docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md docs/superpowers/plans/2026-05-18-multi-google-mcp.md
git commit -m "docs: initial spec and implementation plan for multi-google-mcp"
```

Expected: a single commit containing the spec, plan, and gitignore.

---

### Task 2: Scaffold the Python project

**Files:**
- Create: `pyproject.toml`
- Create: `src/multi_google_mcp/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "multi-google-mcp"
version = "0.1.0"
description = "Local MCP server for multiple Google accounts (Gmail, Calendar, Drive)"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "google-api-python-client>=2.0.0",
    "google-auth>=2.0.0",
    "google-auth-oauthlib>=1.0.0",
]

[project.scripts]
multi-google-mcp = "multi_google_mcp.server:main"
multi-google-mcp-auth = "multi_google_mcp.auth_cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/multi_google_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]

[tool.mypy]
strict = true
python_version = "3.11"
mypy_path = "src"
packages = ["multi_google_mcp"]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "types-google-cloud-ndb",
]
```

- [ ] **Step 2: Create empty package + tests init files**

```python
# src/multi_google_mcp/__init__.py
"""Multi-Google MCP server."""
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

- [ ] **Step 3: Create the virtual environment and install**

```bash
uv sync
```

Expected: `.venv/` created, dependencies installed, no errors.

- [ ] **Step 4: Verify the package imports**

```bash
uv run python -c "import multi_google_mcp; print(multi_google_mcp.__version__)"
```

Expected: `0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/multi_google_mcp/__init__.py tests/__init__.py
git commit -m "chore: scaffold python package and tooling"
```

---

### Task 3: Config module (paths + scopes)

**Files:**
- Create: `src/multi_google_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from multi_google_mcp import config


def test_config_dir_uses_home():
    assert config.CONFIG_DIR == Path.home() / ".config" / "multi-google-mcp"


def test_accounts_dir_lives_under_config_dir():
    assert config.ACCOUNTS_DIR == config.CONFIG_DIR / "accounts"


def test_client_secret_path():
    assert config.CLIENT_SECRET_PATH == config.CONFIG_DIR / "client_secret.json"


def test_scopes_include_all_three_apis():
    assert "https://www.googleapis.com/auth/gmail.modify" in config.SCOPES
    assert "https://www.googleapis.com/auth/calendar" in config.SCOPES
    assert "https://www.googleapis.com/auth/drive" in config.SCOPES
    assert "https://www.googleapis.com/auth/userinfo.email" in config.SCOPES
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```

Expected: ImportError (no `config` module yet).

- [ ] **Step 3: Implement `config.py`**

```python
# src/multi_google_mcp/config.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/config.py tests/test_config.py
git commit -m "feat(config): paths and oauth scopes"
```

---

### Task 4: Exceptions module

**Files:**
- Create: `src/multi_google_mcp/exceptions.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_config.py (or create tests/test_exceptions.py)
# tests/test_exceptions.py
import pytest
from multi_google_mcp.exceptions import (
    AccountNotConfigured,
    AccountNeedsReauth,
    OAuthClientNotConfigured,
)


def test_account_not_configured_message_includes_label():
    err = AccountNotConfigured("work")
    assert "work" in str(err)
    assert "multi-google-mcp-auth add work" in str(err)


def test_account_needs_reauth_message_includes_label():
    err = AccountNeedsReauth("personal")
    assert "personal" in str(err)
    assert "multi-google-mcp-auth add personal" in str(err)


def test_oauth_client_not_configured_message_references_readme():
    err = OAuthClientNotConfigured()
    assert "client_secret.json" in str(err) or "OAuth client" in str(err)
    assert "README" in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_exceptions.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `exceptions.py`**

```python
# src/multi_google_mcp/exceptions.py
"""Errors surfaced to MCP tool callers."""


class MultiGoogleMcpError(Exception):
    """Base class."""


class AccountNotConfigured(MultiGoogleMcpError):
    def __init__(self, label: str) -> None:
        super().__init__(
            f"Account '{label}' not configured. Run: multi-google-mcp-auth add {label}"
        )
        self.label = label


class AccountNeedsReauth(MultiGoogleMcpError):
    def __init__(self, label: str) -> None:
        super().__init__(
            f"Account '{label}' needs reauthentication. Run: multi-google-mcp-auth add {label}"
        )
        self.label = label


class OAuthClientNotConfigured(MultiGoogleMcpError):
    def __init__(self) -> None:
        super().__init__(
            "OAuth client not configured: client_secret.json missing. See README §Setup."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_exceptions.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/exceptions.py tests/test_exceptions.py
git commit -m "feat(exceptions): typed errors for account and oauth misconfig"
```

---

### Task 5: AccountStore — list and save

**Files:**
- Create: `src/multi_google_mcp/accounts.py`
- Test: `tests/test_accounts.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write a conftest fixture for an isolated config dir**

```python
# tests/conftest.py
import json
import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path: Path, monkeypatch) -> Path:
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
```

- [ ] **Step 2: Write failing tests for `list()` and `save()`**

```python
# tests/test_accounts.py
import json
from pathlib import Path
from tests.conftest import write_account_file
from multi_google_mcp.accounts import AccountStore, AccountInfo


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
    # chmod 600 = octal 0o600
    assert (path.stat().st_mode & 0o777) == 0o600
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_accounts.py -v
```

Expected: ImportError on `accounts`.

- [ ] **Step 4: Implement `AccountStore.list` and `AccountStore.save`**

```python
# src/multi_google_mcp/accounts.py
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_accounts.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/multi_google_mcp/accounts.py tests/conftest.py tests/test_accounts.py
git commit -m "feat(accounts): AccountStore.list and .save with chmod 600"
```

---

### Task 6: AccountStore — credentials() with auto-refresh

**Files:**
- Modify: `src/multi_google_mcp/accounts.py`
- Modify: `tests/test_accounts.py`

- [ ] **Step 1: Write failing tests for `credentials()`**

```python
# Append to tests/test_accounts.py
import datetime as dt
from unittest.mock import patch, MagicMock

import pytest
from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import (
    AccountNotConfigured,
    AccountNeedsReauth,
    OAuthClientNotConfigured,
)


def test_credentials_raises_when_label_unknown(tmp_config_dir):
    with pytest.raises(AccountNotConfigured) as excinfo:
        AccountStore().credentials("nope")
    assert "nope" in str(excinfo.value)


def test_credentials_raises_when_client_secret_missing(tmp_config_dir):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    # no client_secret.json on disk
    with pytest.raises(OAuthClientNotConfigured):
        AccountStore().credentials("work")


def _write_fake_client_secret(tmp_config_dir):
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


def test_credentials_returns_google_credentials_from_disk(tmp_config_dir):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)

    creds = AccountStore().credentials("work")
    assert creds.refresh_token == "refresh-xyz"
    assert creds.token == "access-xyz"
    assert creds.client_id == "fake.apps.googleusercontent.com"


def test_credentials_refresh_writes_back_new_access_token(tmp_config_dir):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()

    creds = store.credentials("work")
    # Simulate Google's library refreshing the token.
    creds.token = "NEW-access-token"
    creds.expiry = dt.datetime(2099, 12, 31, 0, 0, 0)
    # The library calls our on-refresh callback after a successful refresh.
    # We expose a public method `_on_refresh` for that purpose.
    store._on_refresh("work", creds)

    data = json.loads((tmp_config_dir / "accounts" / "work.json").read_text())
    assert data["access_token"] == "NEW-access-token"


def test_credentials_raises_account_needs_reauth_on_invalid_grant(tmp_config_dir):
    write_account_file(tmp_config_dir / "accounts", "work", "a@b.com")
    _write_fake_client_secret(tmp_config_dir)
    store = AccountStore()
    creds = store.credentials("work")

    with patch.object(creds, "refresh", side_effect=Exception("invalid_grant")):
        with pytest.raises(AccountNeedsReauth) as excinfo:
            store.refresh_if_needed("work", creds, force=True)
        assert "work" in str(excinfo.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_accounts.py -v
```

Expected: AttributeError on `AccountStore.credentials`.

- [ ] **Step 3: Extend `accounts.py` with credentials + refresh logic**

Replace the file's contents with:

```python
# src/multi_google_mcp/accounts.py
"""Per-account credential storage and refresh."""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

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

    def _load_client_config(self) -> dict[str, str]:
        if not config.CLIENT_SECRET_PATH.exists():
            raise OAuthClientNotConfigured()
        raw = json.loads(config.CLIENT_SECRET_PATH.read_text())
        # Google's downloaded file wraps under "installed" for Desktop apps.
        installed = raw.get("installed") or raw.get("web") or raw
        return installed

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

    def remove(self, label: str) -> None:
        path = self._path(label)
        if not path.exists():
            raise AccountNotConfigured(label)
        path.unlink()

    def credentials(self, label: str) -> Credentials:
        """Return a Google Credentials object for the given account label.

        Caller should pass to googleapiclient.discovery.build. If the access
        token has expired the library will refresh transparently; call
        refresh_if_needed afterwards to persist the new token.
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

        creds = Credentials(
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
            creds.refresh(GoogleRequest())
        except Exception as e:  # google.auth raises a variety of types
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
            data["token_expiry"] = creds.expiry.replace(microsecond=0).isoformat() + "Z"
        path.write_text(json.dumps(data))
        os.chmod(path, 0o600)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_accounts.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/accounts.py tests/test_accounts.py
git commit -m "feat(accounts): credentials loader + refresh-write-back"
```

---

### Task 7: Auth CLI — `add` subcommand

**Files:**
- Create: `src/multi_google_mcp/auth_cli.py`
- Test: `tests/test_auth_cli.py`

- [ ] **Step 1: Write failing tests for the CLI parser**

```python
# tests/test_auth_cli.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from multi_google_mcp.auth_cli import main as auth_main


def _write_fake_client_secret(tmp_config_dir: Path):
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


def test_add_runs_oauth_flow_and_writes_account_file(tmp_config_dir, capsys):
    _write_fake_client_secret(tmp_config_dir)

    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh-from-flow"
    fake_creds.token = "access-from-flow"
    fake_creds.expiry = None
    fake_creds.scopes = ["https://www.googleapis.com/auth/gmail.modify"]

    with patch(
        "multi_google_mcp.auth_cli.InstalledAppFlow"
    ) as flow_cls, patch(
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


def test_add_errors_when_client_secret_missing(tmp_config_dir, capsys):
    # no client_secret.json on disk
    exit_code = auth_main(["add", "work"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "client_secret.json" in err
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_auth_cli.py -v
```

Expected: ImportError on `auth_cli`.

- [ ] **Step 3: Implement the `add` path of the CLI**

```python
# src/multi_google_mcp/auth_cli.py
"""multi-google-mcp-auth: manage local OAuth tokens for the MCP server."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from multi_google_mcp import config
from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import OAuthClientNotConfigured


def _fetch_email(creds) -> str:
    """Look up the authenticated user's email via the userinfo endpoint."""
    service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
    info = service.userinfo().get().execute()
    return info["email"]


def _cmd_add(label: str) -> int:
    if not config.CLIENT_SECRET_PATH.exists():
        print(
            f"error: client_secret.json missing at {config.CLIENT_SECRET_PATH}",
            file=sys.stderr,
        )
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.CLIENT_SECRET_PATH), config.SCOPES
    )
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    email = _fetch_email(creds)
    expiry = (
        creds.expiry.replace(microsecond=0).isoformat() + "Z" if creds.expiry else ""
    )
    AccountStore().save(
        label=label,
        email=email,
        refresh_token=creds.refresh_token,
        access_token=creds.token,
        token_expiry=expiry,
        scopes=list(creds.scopes or config.SCOPES),
    )
    print(f"Saved account '{label}' (email: {email})")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="multi-google-mcp-auth")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Authenticate and add a new account")
    p_add.add_argument("label", help="Local label, e.g. 'work' or 'personal'")

    sub.add_parser("list", help="List configured accounts")

    p_rm = sub.add_parser("remove", help="Remove a configured account")
    p_rm.add_argument("label", help="Account label to remove")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "add":
            return _cmd_add(args.label)
        if args.cmd == "list":
            return _cmd_list()
        if args.cmd == "remove":
            return _cmd_remove(args.label)
    except OAuthClientNotConfigured as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 2


def _cmd_list() -> int:
    accounts = AccountStore().list()
    if not accounts:
        print("(no accounts configured)")
        return 0
    width = max(len(a.label) for a in accounts)
    for a in accounts:
        print(f"  {a.label.ljust(width)}  {a.email}")
    return 0


def _cmd_remove(label: str) -> int:
    try:
        AccountStore().remove(label)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Removed account '{label}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_auth_cli.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/auth_cli.py tests/test_auth_cli.py
git commit -m "feat(auth_cli): add subcommand wires InstalledAppFlow to AccountStore"
```

---

### Task 8: Auth CLI — `list` and `remove`

**Files:**
- Modify: `tests/test_auth_cli.py`

The implementation already exists from Task 7 (`_cmd_list`, `_cmd_remove`). This task adds the tests.

- [ ] **Step 1: Write failing tests**

```python
# Append to tests/test_auth_cli.py
def test_list_prints_empty_message_when_no_accounts(tmp_config_dir, capsys):
    exit_code = auth_main(["list"])
    assert exit_code == 0
    assert "no accounts" in capsys.readouterr().out.lower()


def test_list_prints_label_and_email(tmp_config_dir, capsys):
    from tests.conftest import write_account_file
    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")
    write_account_file(tmp_config_dir / "accounts", "personal", "bob@example.com")

    exit_code = auth_main(["list"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "work" in out and "alice@example.com" in out
    assert "personal" in out and "bob@example.com" in out


def test_remove_deletes_account_file(tmp_config_dir, capsys):
    from tests.conftest import write_account_file
    write_account_file(tmp_config_dir / "accounts", "work", "alice@example.com")

    exit_code = auth_main(["remove", "work"])
    assert exit_code == 0
    assert not (tmp_config_dir / "accounts" / "work.json").exists()


def test_remove_errors_when_account_unknown(tmp_config_dir, capsys):
    exit_code = auth_main(["remove", "ghost"])
    assert exit_code == 1
    assert "ghost" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_auth_cli.py -v
```

Expected: 6 passed (2 from Task 7 + 4 here).

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_cli.py
git commit -m "test(auth_cli): cover list and remove"
```

---

## Phase B — Response shaping helpers

Each shaping helper takes a raw Google API payload and returns a compact dict.
This phase lives entirely outside the Google client — pure data transforms,
easy to test.

### Task 9: Gmail shaping helpers

**Files:**
- Create: `src/multi_google_mcp/shaping/__init__.py`
- Create: `src/multi_google_mcp/shaping/gmail.py`
- Test: `tests/shaping/__init__.py`
- Test: `tests/shaping/test_gmail.py`

- [ ] **Step 1: Create empty shaping package init files**

```python
# src/multi_google_mcp/shaping/__init__.py
```

```python
# tests/shaping/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/shaping/test_gmail.py
import base64
from multi_google_mcp.shaping.gmail import (
    shape_message_summary,
    shape_message_full,
    extract_body_text,
)


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


SAMPLE_MESSAGE = {
    "id": "msg-1",
    "threadId": "thr-1",
    "labelIds": ["INBOX", "UNREAD"],
    "snippet": "Hello there",
    "internalDate": "1715990400000",
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [
            {"name": "From", "value": "Alice <a@b.com>"},
            {"name": "To", "value": "bob@c.com"},
            {"name": "Subject", "value": "Hi"},
            {"name": "Date", "value": "Sat, 18 May 2026 00:00:00 +0000"},
        ],
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64url("plain body")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": _b64url("<p>html body</p>")},
            },
        ],
    },
}


def test_shape_message_summary_picks_key_fields():
    out = shape_message_summary(SAMPLE_MESSAGE)
    assert out == {
        "id": "msg-1",
        "thread_id": "thr-1",
        "from": "Alice <a@b.com>",
        "to": "bob@c.com",
        "subject": "Hi",
        "snippet": "Hello there",
        "date": "Sat, 18 May 2026 00:00:00 +0000",
        "labels": ["INBOX", "UNREAD"],
    }


def test_extract_body_text_prefers_text_plain():
    assert extract_body_text(SAMPLE_MESSAGE["payload"]) == "plain body"


def test_extract_body_text_falls_back_to_html_stripped():
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64url("<p>only html</p>")},
    }
    assert "only html" in extract_body_text(payload)
    assert "<" not in extract_body_text(payload)


def test_shape_message_full_includes_body_and_attachments():
    msg = {
        **SAMPLE_MESSAGE,
        "payload": {
            **SAMPLE_MESSAGE["payload"],
            "parts": [
                *SAMPLE_MESSAGE["payload"]["parts"],
                {
                    "mimeType": "application/pdf",
                    "filename": "report.pdf",
                    "body": {"size": 12345, "attachmentId": "att-1"},
                },
            ],
        },
    }
    out = shape_message_full(msg)
    assert out["body_text"] == "plain body"
    assert out["attachments"] == [
        {
            "filename": "report.pdf",
            "mime": "application/pdf",
            "size": 12345,
            "attachment_id": "att-1",
        }
    ]
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/shaping/test_gmail.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement Gmail shaping**

```python
# src/multi_google_mcp/shaping/gmail.py
"""Shape raw Gmail API payloads into compact dicts."""
from __future__ import annotations

import base64
import re
from typing import Any


def _b64url_decode(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode(errors="replace")


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}


def _strip_html(html: str) -> str:
    # Minimal HTML→text. We're not trying to render HTML; just remove tags.
    no_tags = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", " ", no_tags).strip()


def extract_body_text(payload: dict[str, Any]) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    if mime == "text/plain" and body.get("data"):
        return _b64url_decode(body["data"])
    if mime == "text/html" and body.get("data"):
        return _strip_html(_b64url_decode(body["data"]))
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])
    for part in payload.get("parts", []):
        text = extract_body_text(part)
        if text:
            return text
    return ""


def _extract_attachments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for part in payload.get("parts", []):
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            out.append(
                {
                    "filename": part["filename"],
                    "mime": part.get("mimeType", "application/octet-stream"),
                    "size": part["body"].get("size", 0),
                    "attachment_id": part["body"]["attachmentId"],
                }
            )
        out.extend(_extract_attachments(part))
    return out


def shape_message_summary(msg: dict[str, Any]) -> dict[str, Any]:
    headers = _headers_to_dict(msg.get("payload", {}).get("headers", []))
    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "snippet": msg.get("snippet", ""),
        "date": headers.get("date", ""),
        "labels": msg.get("labelIds", []),
    }


def shape_message_full(msg: dict[str, Any]) -> dict[str, Any]:
    summary = shape_message_summary(msg)
    payload = msg.get("payload", {})
    return {
        **summary,
        "body_text": extract_body_text(payload),
        "attachments": _extract_attachments(payload),
    }
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/shaping/test_gmail.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/multi_google_mcp/shaping/ tests/shaping/__init__.py tests/shaping/test_gmail.py
git commit -m "feat(shaping): gmail message summary/full and body extraction"
```

---

### Task 10: Calendar shaping helpers

**Files:**
- Create: `src/multi_google_mcp/shaping/calendar.py`
- Test: `tests/shaping/test_calendar.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/shaping/test_calendar.py
from multi_google_mcp.shaping.calendar import shape_calendar, shape_event


def test_shape_calendar_picks_basic_fields():
    raw = {
        "id": "primary",
        "summary": "alice@example.com",
        "primary": True,
        "accessRole": "owner",
        "timeZone": "America/Los_Angeles",
    }
    assert shape_calendar(raw) == {
        "id": "primary",
        "summary": "alice@example.com",
        "primary": True,
        "access_role": "owner",
    }


def test_shape_event_with_datetime_start_end():
    raw = {
        "id": "ev-1",
        "summary": "Standup",
        "start": {"dateTime": "2026-05-19T09:00:00-07:00"},
        "end": {"dateTime": "2026-05-19T09:30:00-07:00"},
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/?eid=abc",
        "attendees": [
            {"email": "a@b.com", "responseStatus": "accepted"},
            {"email": "c@d.com", "responseStatus": "needsAction"},
        ],
        "location": "Zoom",
        "description": "Daily sync",
    }
    out = shape_event(raw)
    assert out["id"] == "ev-1"
    assert out["summary"] == "Standup"
    assert out["start"] == "2026-05-19T09:00:00-07:00"
    assert out["end"] == "2026-05-19T09:30:00-07:00"
    assert out["status"] == "confirmed"
    assert out["html_link"] == "https://calendar.google.com/?eid=abc"
    assert out["attendees"] == [
        {"email": "a@b.com", "response": "accepted"},
        {"email": "c@d.com", "response": "needsAction"},
    ]
    assert out["location"] == "Zoom"
    assert out["description"] == "Daily sync"


def test_shape_event_with_all_day_date_start_end():
    raw = {
        "id": "ev-2",
        "summary": "Holiday",
        "start": {"date": "2026-12-25"},
        "end": {"date": "2026-12-26"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    out = shape_event(raw)
    assert out["start"] == "2026-12-25"
    assert out["end"] == "2026-12-26"
```

- [ ] **Step 2: Run tests** — expect ImportError.

- [ ] **Step 3: Implement**

```python
# src/multi_google_mcp/shaping/calendar.py
"""Shape raw Calendar API payloads."""
from __future__ import annotations

from typing import Any


def shape_calendar(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "summary": raw.get("summary", ""),
        "primary": raw.get("primary", False),
        "access_role": raw.get("accessRole", ""),
    }


def _shape_time(node: dict[str, Any]) -> str:
    return node.get("dateTime") or node.get("date") or ""


def shape_event(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": raw["id"],
        "summary": raw.get("summary", ""),
        "start": _shape_time(raw.get("start", {})),
        "end": _shape_time(raw.get("end", {})),
        "status": raw.get("status", ""),
        "html_link": raw.get("htmlLink", ""),
    }
    if "location" in raw:
        out["location"] = raw["location"]
    if "description" in raw:
        out["description"] = raw["description"]
    if "attendees" in raw:
        out["attendees"] = [
            {"email": a["email"], "response": a.get("responseStatus", "")}
            for a in raw["attendees"]
        ]
    return out
```

- [ ] **Step 4: Run tests** — expect 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/shaping/calendar.py tests/shaping/test_calendar.py
git commit -m "feat(shaping): calendar event and calendar summary"
```

---

### Task 11: Drive shaping helpers

**Files:**
- Create: `src/multi_google_mcp/shaping/drive.py`
- Test: `tests/shaping/test_drive.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/shaping/test_drive.py
from multi_google_mcp.shaping.drive import shape_file_metadata, export_mime_for


def test_shape_file_metadata_picks_key_fields():
    raw = {
        "id": "f-1",
        "name": "Notes",
        "mimeType": "application/vnd.google-apps.document",
        "size": "0",
        "parents": ["folder-1"],
        "modifiedTime": "2026-05-18T20:00:00Z",
        "webViewLink": "https://docs.google.com/document/d/f-1/edit",
    }
    assert shape_file_metadata(raw) == {
        "id": "f-1",
        "name": "Notes",
        "mime": "application/vnd.google-apps.document",
        "size": 0,
        "parents": ["folder-1"],
        "modified_time": "2026-05-18T20:00:00Z",
        "web_view_link": "https://docs.google.com/document/d/f-1/edit",
    }


def test_shape_file_metadata_handles_missing_optional_fields():
    raw = {"id": "f-1", "name": "Untitled", "mimeType": "text/plain"}
    out = shape_file_metadata(raw)
    assert out["size"] == 0
    assert out["parents"] == []


def test_export_mime_for_google_doc_returns_text_plain():
    assert export_mime_for("application/vnd.google-apps.document") == "text/plain"


def test_export_mime_for_google_sheet_returns_csv():
    assert export_mime_for("application/vnd.google-apps.spreadsheet") == "text/csv"


def test_export_mime_for_google_slides_returns_text_plain():
    assert export_mime_for("application/vnd.google-apps.presentation") == "text/plain"


def test_export_mime_for_non_google_returns_none():
    assert export_mime_for("application/pdf") is None
```

- [ ] **Step 2: Run tests** — expect ImportError.

- [ ] **Step 3: Implement**

```python
# src/multi_google_mcp/shaping/drive.py
"""Shape raw Drive API payloads + native-format export decisions."""
from __future__ import annotations

from typing import Any

_EXPORT_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def shape_file_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "mime": raw.get("mimeType", ""),
        "size": int(raw.get("size", 0) or 0),
        "parents": raw.get("parents", []),
        "modified_time": raw.get("modifiedTime", ""),
        "web_view_link": raw.get("webViewLink", ""),
    }


def export_mime_for(google_mime: str) -> str | None:
    """Return the export mime type for a Google-native file, or None for binary."""
    return _EXPORT_MAP.get(google_mime)
```

- [ ] **Step 4: Run tests** — expect 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/shaping/drive.py tests/shaping/test_drive.py
git commit -m "feat(shaping): drive file metadata and native export mime map"
```

---

## Phase C — Tools

Every tool function in this phase has the signature
`(account: str, ...) -> dict | list[dict]`. Each one resolves the account
through `AccountStore`, builds a Google service, makes the API call, and
returns a shaped result.

Tests use a `_mock_service` fixture (added below) to mock the Google
`build()` call so no network or real credentials are needed.

### Task 12: Tool test fixtures

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/tools/__init__.py`

- [ ] **Step 1: Add fixtures for mocked Google services**

Append to `tests/conftest.py`:

```python
from unittest.mock import MagicMock


@pytest.fixture
def saved_account(tmp_config_dir):
    """A fully-saved 'work' account on disk + fake client_secret."""
    from tests.conftest import write_account_file
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
def mock_build(monkeypatch):
    """Patch googleapiclient.discovery.build to return a MagicMock service.

    Returns a dict {"service": MagicMock} the caller can configure per-test.

    Only patches tool modules that have already been imported successfully —
    earlier tasks in the plan only have `tools.gmail`, later tasks add the
    others. This avoids ImportError when running tests mid-plan.
    """
    import importlib

    service = MagicMock()
    builds: list[tuple[str, str]] = []

    def fake_build(api, version, **kwargs):
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
```

```python
# tests/tools/__init__.py
```

- [ ] **Step 2: Verify the fixture file still parses**

```bash
uv run pytest --collect-only tests/ -q
```

Expected: tests collected without errors.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/tools/__init__.py
git commit -m "test(tools): shared fixtures for saved account + mocked google build"
```

---

### Task 13: Gmail tools — `gmail_search` and `gmail_get_message`

**Files:**
- Create: `src/multi_google_mcp/tools/__init__.py`
- Create: `src/multi_google_mcp/tools/gmail.py`
- Test: `tests/tools/test_gmail.py`

- [ ] **Step 1: Empty package init**

```python
# src/multi_google_mcp/tools/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/tools/test_gmail.py
import base64
from unittest.mock import MagicMock
from multi_google_mcp.tools.gmail import gmail_search, gmail_get_message


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def test_gmail_search_returns_shaped_summaries(saved_account, mock_build):
    service = mock_build["service"]

    # list() returns IDs; then get() per message returns metadata
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t2"}]
    }

    def get_execute(userId, id, format):  # noqa: A002
        return {
            "id": id,
            "threadId": f"thr-{id}",
            "labelIds": ["INBOX"],
            "snippet": f"snippet for {id}",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <a@b.com>"},
                    {"name": "Subject", "value": f"Subj {id}"},
                    {"name": "Date", "value": "Sat, 18 May 2026"},
                ]
            },
        }

    service.users().messages().get.side_effect = lambda **kw: MagicMock(
        execute=lambda: get_execute(**kw)
    )

    out = gmail_search("work", query="is:unread", max_results=2)
    assert len(out) == 2
    assert out[0]["id"] == "m1"
    assert out[0]["from"] == "Alice <a@b.com>"
    assert out[1]["subject"] == "Subj m2"


def test_gmail_get_message_returns_full_with_body(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().get().execute.return_value = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "snippet",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "a@b.com"},
                {"name": "Subject", "value": "Hi"},
            ],
            "body": {"data": _b64url("hello world")},
        },
    }

    out = gmail_get_message("work", message_id="m1")
    assert out["id"] == "m1"
    assert out["body_text"] == "hello world"
```

- [ ] **Step 3: Run tests** — expect ImportError.

- [ ] **Step 4: Implement**

```python
# src/multi_google_mcp/tools/gmail.py
"""MCP tool implementations for Gmail."""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.gmail import shape_message_full, shape_message_summary

_store = AccountStore()


def _service(account: str):
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def gmail_search(account: str, query: str, max_results: int = 10) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = (
        svc.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    summaries: list[dict[str, Any]] = []
    for ref in listing.get("messages", []):
        msg = (
            svc.users()
            .messages()
            .get(userId="me", id=ref["id"], format="metadata")
            .execute()
        )
        summaries.append(shape_message_summary(msg))
    return summaries


def gmail_get_message(account: str, message_id: str) -> dict[str, Any]:
    svc = _service(account)
    msg = (
        svc.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    return shape_message_full(msg)
```

- [ ] **Step 5: Run tests** — expect 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/multi_google_mcp/tools/__init__.py src/multi_google_mcp/tools/gmail.py tests/tools/test_gmail.py
git commit -m "feat(tools/gmail): search and get_message"
```

---

### Task 14: Gmail tools — `gmail_send` and `gmail_modify_labels`

**Files:**
- Modify: `src/multi_google_mcp/tools/gmail.py`
- Modify: `tests/tools/test_gmail.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/tools/test_gmail.py`:

```python
def test_gmail_send_builds_rfc822_and_calls_send(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().send().execute.return_value = {"id": "sent-1"}

    from multi_google_mcp.tools.gmail import gmail_send
    out = gmail_send(
        "work",
        to="bob@example.com",
        subject="Hi Bob",
        body="hello",
    )
    assert out == {"id": "sent-1"}
    # Verify a base64url body was posted under "raw"
    call_kwargs = service.users().messages().send.call_args.kwargs
    assert call_kwargs["userId"] == "me"
    assert "raw" in call_kwargs["body"]


def test_gmail_modify_labels_add_and_remove(saved_account, mock_build):
    service = mock_build["service"]
    service.users().messages().modify().execute.return_value = {
        "id": "m1",
        "labelIds": ["INBOX", "Label_1"],
    }

    from multi_google_mcp.tools.gmail import gmail_modify_labels
    out = gmail_modify_labels(
        "work", message_id="m1", add=["Label_1"], remove=["UNREAD"]
    )
    assert "Label_1" in out["labels"]
    call_kwargs = service.users().messages().modify.call_args.kwargs
    assert call_kwargs["body"] == {
        "addLabelIds": ["Label_1"],
        "removeLabelIds": ["UNREAD"],
    }


def test_gmail_modify_labels_trash_flag_routes_to_trash_endpoint(
    saved_account, mock_build
):
    service = mock_build["service"]
    service.users().messages().trash().execute.return_value = {
        "id": "m1",
        "labelIds": ["TRASH"],
    }

    from multi_google_mcp.tools.gmail import gmail_modify_labels
    out = gmail_modify_labels("work", message_id="m1", trash=True)
    assert "TRASH" in out["labels"]
    service.users().messages().trash.assert_called_with(userId="me", id="m1")
```

- [ ] **Step 2: Run tests** — expect failures.

- [ ] **Step 3: Add implementations**

Append to `src/multi_google_mcp/tools/gmail.py`:

```python
import base64
from email.message import EmailMessage


def _build_raw_message(
    *,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    html: bool = False,
    in_reply_to: str | None = None,
) -> str:
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    if html:
        msg.set_content("", subtype="plain")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def gmail_send(
    account: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    html: bool = False,
    in_reply_to: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    raw = _build_raw_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=html,
        in_reply_to=in_reply_to,
    )
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": sent["id"]}


def gmail_modify_labels(
    account: str,
    message_id: str,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    trash: bool = False,
) -> dict[str, Any]:
    svc = _service(account)
    if trash:
        result = svc.users().messages().trash(userId="me", id=message_id).execute()
    else:
        result = (
            svc.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add or [],
                    "removeLabelIds": remove or [],
                },
            )
            .execute()
        )
    return {"id": result["id"], "labels": result.get("labelIds", [])}
```

- [ ] **Step 4: Run tests** — expect all gmail tool tests passing.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/tools/gmail.py tests/tools/test_gmail.py
git commit -m "feat(tools/gmail): send and modify_labels (with trash flag)"
```

---

### Task 15: Calendar tools

**Files:**
- Create: `src/multi_google_mcp/tools/calendar.py`
- Test: `tests/tools/test_calendar.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/tools/test_calendar.py
from multi_google_mcp.tools.calendar import (
    calendar_list_calendars,
    calendar_list_events,
    calendar_get_event,
    calendar_create_event,
    calendar_update_event,
    calendar_delete_event,
)


def test_list_calendars_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.calendarList().list().execute.return_value = {
        "items": [
            {
                "id": "primary",
                "summary": "alice@example.com",
                "primary": True,
                "accessRole": "owner",
            }
        ]
    }
    out = calendar_list_calendars("work")
    assert out == [
        {
            "id": "primary",
            "summary": "alice@example.com",
            "primary": True,
            "access_role": "owner",
        }
    ]


def test_list_events_passes_time_window(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().list().execute.return_value = {"items": []}

    out = calendar_list_events(
        "work",
        calendar_id="primary",
        time_min="2026-05-18T00:00:00Z",
        time_max="2026-05-19T00:00:00Z",
        max_results=5,
    )
    assert out == []
    kw = svc.events().list.call_args.kwargs
    assert kw["calendarId"] == "primary"
    assert kw["timeMin"] == "2026-05-18T00:00:00Z"
    assert kw["timeMax"] == "2026-05-19T00:00:00Z"
    assert kw["maxResults"] == 5
    assert kw["singleEvents"] is True
    assert kw["orderBy"] == "startTime"


def test_get_event_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().get().execute.return_value = {
        "id": "ev",
        "summary": "Standup",
        "start": {"dateTime": "2026-05-19T09:00:00Z"},
        "end": {"dateTime": "2026-05-19T09:30:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    out = calendar_get_event("work", calendar_id="primary", event_id="ev")
    assert out["summary"] == "Standup"


def test_create_event_posts_correct_body(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().insert().execute.return_value = {
        "id": "ev-new",
        "summary": "X",
        "start": {"dateTime": "2026-06-01T10:00:00Z"},
        "end": {"dateTime": "2026-06-01T11:00:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    calendar_create_event(
        "work",
        calendar_id="primary",
        summary="X",
        start="2026-06-01T10:00:00Z",
        end="2026-06-01T11:00:00Z",
        attendees=["a@b.com"],
        location="HQ",
    )
    kw = svc.events().insert.call_args.kwargs
    assert kw["calendarId"] == "primary"
    body = kw["body"]
    assert body["summary"] == "X"
    assert body["start"] == {"dateTime": "2026-06-01T10:00:00Z"}
    assert body["end"] == {"dateTime": "2026-06-01T11:00:00Z"}
    assert body["attendees"] == [{"email": "a@b.com"}]
    assert body["location"] == "HQ"


def test_update_event_patches_only_supplied(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().patch().execute.return_value = {
        "id": "ev",
        "summary": "Updated",
        "start": {"dateTime": "2026-06-01T10:00:00Z"},
        "end": {"dateTime": "2026-06-01T11:00:00Z"},
        "status": "confirmed",
        "htmlLink": "https://...",
    }
    calendar_update_event(
        "work", calendar_id="primary", event_id="ev", summary="Updated"
    )
    kw = svc.events().patch.call_args.kwargs
    assert kw["body"] == {"summary": "Updated"}


def test_delete_event_calls_delete(saved_account, mock_build):
    svc = mock_build["service"]
    svc.events().delete().execute.return_value = None
    out = calendar_delete_event("work", calendar_id="primary", event_id="ev")
    assert out == {"deleted": True, "id": "ev"}
    svc.events().delete.assert_called_with(calendarId="primary", eventId="ev")
```

- [ ] **Step 2: Run tests** — expect ImportError.

- [ ] **Step 3: Implement**

```python
# src/multi_google_mcp/tools/calendar.py
"""MCP tool implementations for Google Calendar."""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.calendar import shape_calendar, shape_event

_store = AccountStore()


def _service(account: str):
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def calendar_list_calendars(account: str) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = svc.calendarList().list().execute()
    return [shape_calendar(c) for c in listing.get("items", [])]


def calendar_list_events(
    account: str,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    svc = _service(account)
    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        kwargs["timeMin"] = time_min
    if time_max:
        kwargs["timeMax"] = time_max
    if query:
        kwargs["q"] = query
    listing = svc.events().list(**kwargs).execute()
    return [shape_event(e) for e in listing.get("items", [])]


def calendar_get_event(
    account: str, calendar_id: str, event_id: str
) -> dict[str, Any]:
    svc = _service(account)
    ev = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return shape_event(ev)


def _time_node(value: str) -> dict[str, str]:
    """Allow either 'YYYY-MM-DD' (all-day) or full RFC3339 datetime."""
    if "T" in value:
        return {"dateTime": value}
    return {"date": value}


def calendar_create_event(
    account: str,
    calendar_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    attendees: list[str] | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {
        "summary": summary,
        "start": _time_node(start),
        "end": _time_node(end),
    }
    if description:
        body["description"] = description
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    if location:
        body["location"] = location
    ev = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return shape_event(ev)


def calendar_update_event(
    account: str,
    calendar_id: str,
    event_id: str,
    summary: str | None = None,
    description: str | None = None,
    start: str | None = None,
    end: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if start is not None:
        body["start"] = _time_node(start)
    if end is not None:
        body["end"] = _time_node(end)
    if location is not None:
        body["location"] = location
    if attendees is not None:
        body["attendees"] = [{"email": e} for e in attendees]
    ev = (
        svc.events()
        .patch(calendarId=calendar_id, eventId=event_id, body=body)
        .execute()
    )
    return shape_event(ev)


def calendar_delete_event(
    account: str, calendar_id: str, event_id: str
) -> dict[str, Any]:
    svc = _service(account)
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"deleted": True, "id": event_id}
```

- [ ] **Step 4: Run tests** — expect 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/tools/calendar.py tests/tools/test_calendar.py
git commit -m "feat(tools/calendar): list/get/create/update/delete events + list calendars"
```

---

### Task 16: Drive tools

**Files:**
- Create: `src/multi_google_mcp/tools/drive.py`
- Test: `tests/tools/test_drive.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/tools/test_drive.py
import base64
from unittest.mock import MagicMock

from multi_google_mcp.tools.drive import (
    drive_search,
    drive_get_file_metadata,
    drive_read_file,
    drive_upload_file,
    drive_update_file,
    drive_delete_file,
)


def test_drive_search_returns_shaped_metadata(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().list().execute.return_value = {
        "files": [
            {
                "id": "f1",
                "name": "n",
                "mimeType": "text/plain",
                "size": "100",
                "modifiedTime": "2026-05-18T00:00:00Z",
                "webViewLink": "https://...",
            }
        ]
    }
    out = drive_search("work", query="name contains 'n'", max_results=5)
    assert len(out) == 1
    assert out[0]["id"] == "f1"
    kw = svc.files().list.call_args.kwargs
    assert kw["q"] == "name contains 'n'"
    assert kw["pageSize"] == 5
    assert "fields" in kw


def test_drive_get_file_metadata_returns_shaped(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "n",
        "mimeType": "text/plain",
    }
    out = drive_get_file_metadata("work", file_id="f1")
    assert out["id"] == "f1"


def test_drive_read_file_exports_google_doc_as_text(
    saved_account, mock_build, monkeypatch
):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "doc",
        "mimeType": "application/vnd.google-apps.document",
    }
    svc.files().export().execute.return_value = b"document body"

    out = drive_read_file("work", file_id="f1")
    assert out["mime"] == "text/plain"
    assert out["content"] == "document body"
    assert out["encoding"] == "text"
    svc.files().export.assert_called_with(fileId="f1", mimeType="text/plain")


def test_drive_read_file_returns_base64_for_binary(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().get().execute.return_value = {
        "id": "f1",
        "name": "img.png",
        "mimeType": "image/png",
    }
    svc.files().get_media().execute.return_value = b"\x89PNG\x0d\x0a"

    out = drive_read_file("work", file_id="f1")
    assert out["mime"] == "image/png"
    assert out["encoding"] == "base64"
    assert base64.b64decode(out["content"]) == b"\x89PNG\x0d\x0a"


def test_drive_upload_file_text(saved_account, mock_build, monkeypatch):
    svc = mock_build["service"]
    svc.files().create().execute.return_value = {
        "id": "new",
        "name": "n.txt",
        "mimeType": "text/plain",
    }
    out = drive_upload_file("work", name="n.txt", content="hello", mime_type="text/plain")
    assert out["id"] == "new"
    kw = svc.files().create.call_args.kwargs
    assert kw["body"]["name"] == "n.txt"
    assert kw["body"].get("parents") is None or kw["body"].get("parents") == []
    assert kw["media_body"] is not None


def test_drive_update_file_renames_only(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().update().execute.return_value = {
        "id": "f1",
        "name": "new-name.txt",
        "mimeType": "text/plain",
    }
    out = drive_update_file("work", file_id="f1", name="new-name.txt")
    kw = svc.files().update.call_args.kwargs
    assert kw["body"] == {"name": "new-name.txt"}
    assert "media_body" not in kw or kw["media_body"] is None
    assert out["name"] == "new-name.txt"


def test_drive_delete_file_calls_delete(saved_account, mock_build):
    svc = mock_build["service"]
    svc.files().delete().execute.return_value = None
    out = drive_delete_file("work", file_id="f1")
    assert out == {"deleted": True, "id": "f1"}
    svc.files().delete.assert_called_with(fileId="f1")
```

- [ ] **Step 2: Run tests** — expect ImportError.

- [ ] **Step 3: Implement**

```python
# src/multi_google_mcp/tools/drive.py
"""MCP tool implementations for Google Drive."""
from __future__ import annotations

import base64
import io
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.shaping.drive import export_mime_for, shape_file_metadata

_store = AccountStore()

_DEFAULT_FIELDS = "id,name,mimeType,size,parents,modifiedTime,webViewLink"


def _service(account: str):
    creds = _store.credentials(account)
    creds = _store.refresh_if_needed(account, creds)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def drive_search(
    account: str, query: str, max_results: int = 10
) -> list[dict[str, Any]]:
    svc = _service(account)
    listing = (
        svc.files()
        .list(q=query, pageSize=max_results, fields=f"files({_DEFAULT_FIELDS})")
        .execute()
    )
    return [shape_file_metadata(f) for f in listing.get("files", [])]


def drive_get_file_metadata(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    raw = svc.files().get(fileId=file_id, fields=_DEFAULT_FIELDS).execute()
    return shape_file_metadata(raw)


def drive_read_file(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    meta = svc.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    export_mime = export_mime_for(meta["mimeType"])
    if export_mime:
        raw_bytes: bytes = svc.files().export(fileId=file_id, mimeType=export_mime).execute()
        return {
            "id": meta["id"],
            "name": meta["name"],
            "mime": export_mime,
            "encoding": "text",
            "content": raw_bytes.decode("utf-8", errors="replace"),
        }
    raw_bytes = svc.files().get_media(fileId=file_id).execute()
    return {
        "id": meta["id"],
        "name": meta["name"],
        "mime": meta["mimeType"],
        "encoding": "base64",
        "content": base64.b64encode(raw_bytes).decode("ascii"),
    }


def _media(content: str, mime_type: str) -> MediaIoBaseUpload:
    """Wrap string content (text or base64) into a MediaIoBaseUpload."""
    if mime_type.startswith("text/") or mime_type in (
        "application/json",
        "application/xml",
    ):
        data = content.encode("utf-8")
    else:
        data = base64.b64decode(content)
    return MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)


def drive_upload_file(
    account: str,
    name: str,
    content: str,
    mime_type: str,
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {"name": name, "mimeType": mime_type}
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
    raw = (
        svc.files()
        .create(body=body, media_body=_media(content, mime_type), fields=_DEFAULT_FIELDS)
        .execute()
    )
    return shape_file_metadata(raw)


def drive_update_file(
    account: str,
    file_id: str,
    content: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    svc = _service(account)
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    kwargs: dict[str, Any] = {"fileId": file_id, "body": body, "fields": _DEFAULT_FIELDS}
    if content is not None:
        existing = svc.files().get(fileId=file_id, fields="mimeType").execute()
        kwargs["media_body"] = _media(content, existing["mimeType"])
    raw = svc.files().update(**kwargs).execute()
    return shape_file_metadata(raw)


def drive_delete_file(account: str, file_id: str) -> dict[str, Any]:
    svc = _service(account)
    svc.files().delete(fileId=file_id).execute()
    return {"deleted": True, "id": file_id}
```

- [ ] **Step 4: Run tests** — expect 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/multi_google_mcp/tools/drive.py tests/tools/test_drive.py
git commit -m "feat(tools/drive): search, read/upload/update/delete, metadata"
```

---

## Phase D — MCP server wiring

### Task 17: MCP server entrypoint + tool registration

**Files:**
- Create: `src/multi_google_mcp/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_server.py
from multi_google_mcp.server import build_app, TOOL_REGISTRY


def test_tool_registry_has_17_tools():
    assert len(TOOL_REGISTRY) == 17


def test_tool_registry_includes_all_expected_names():
    expected = {
        "list_accounts",
        "gmail_search",
        "gmail_get_message",
        "gmail_send",
        "gmail_modify_labels",
        "calendar_list_calendars",
        "calendar_list_events",
        "calendar_get_event",
        "calendar_create_event",
        "calendar_update_event",
        "calendar_delete_event",
        "drive_search",
        "drive_get_file_metadata",
        "drive_read_file",
        "drive_upload_file",
        "drive_update_file",
        "drive_delete_file",
    }
    assert {t["name"] for t in TOOL_REGISTRY} == expected


def test_build_app_returns_a_server_instance():
    app = build_app()
    assert app is not None
```

- [ ] **Step 2: Run tests** — expect ImportError.

- [ ] **Step 3: Implement the server**

```python
# src/multi_google_mcp/server.py
"""MCP server entrypoint: register tools, run over stdio."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, Callable

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from multi_google_mcp.accounts import AccountStore
from multi_google_mcp.exceptions import MultiGoogleMcpError
from multi_google_mcp.tools import gmail as gmail_tools
from multi_google_mcp.tools import calendar as calendar_tools
from multi_google_mcp.tools import drive as drive_tools


def _list_accounts() -> list[dict[str, str]]:
    return [asdict(a) for a in AccountStore().list()]


# Each entry: {name, description, schema, handler}
TOOL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "list_accounts",
        "description": "List configured Google accounts (label + email).",
        "schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": lambda args: _list_accounts(),
    },
    # Gmail
    {
        "name": "gmail_search",
        "description": "Search Gmail with Gmail query syntax; returns message summaries.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account", "query"],
        },
        "handler": lambda args: gmail_tools.gmail_search(**args),
    },
    {
        "name": "gmail_get_message",
        "description": "Fetch a Gmail message in full (headers, body, attachments).",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "message_id": {"type": "string"},
            },
            "required": ["account", "message_id"],
        },
        "handler": lambda args: gmail_tools.gmail_get_message(**args),
    },
    {
        "name": "gmail_send",
        "description": "Send a Gmail message. Optional html flag and in_reply_to for threading.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "string"},
                "bcc": {"type": "string"},
                "html": {"type": "boolean", "default": False},
                "in_reply_to": {"type": "string"},
            },
            "required": ["account", "to", "subject", "body"],
        },
        "handler": lambda args: gmail_tools.gmail_send(**args),
    },
    {
        "name": "gmail_modify_labels",
        "description": "Add/remove labels on a Gmail message; trash=true moves to trash.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "message_id": {"type": "string"},
                "add": {"type": "array", "items": {"type": "string"}},
                "remove": {"type": "array", "items": {"type": "string"}},
                "trash": {"type": "boolean", "default": False},
            },
            "required": ["account", "message_id"],
        },
        "handler": lambda args: gmail_tools.gmail_modify_labels(**args),
    },
    # Calendar
    {
        "name": "calendar_list_calendars",
        "description": "List calendars the account has access to.",
        "schema": {
            "type": "object",
            "properties": {"account": {"type": "string"}},
            "required": ["account"],
        },
        "handler": lambda args: calendar_tools.calendar_list_calendars(**args),
    },
    {
        "name": "calendar_list_events",
        "description": "List events in a calendar; RFC3339 time_min/time_max bound the window.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string", "default": "primary"},
                "time_min": {"type": "string"},
                "time_max": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account"],
        },
        "handler": lambda args: calendar_tools.calendar_list_events(**args),
    },
    {
        "name": "calendar_get_event",
        "description": "Fetch a single event by id.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_get_event(**args),
    },
    {
        "name": "calendar_create_event",
        "description": "Create a calendar event. start/end accept RFC3339 datetime or YYYY-MM-DD (all-day).",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "description": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"},
            },
            "required": ["account", "calendar_id", "summary", "start", "end"],
        },
        "handler": lambda args: calendar_tools.calendar_create_event(**args),
    },
    {
        "name": "calendar_update_event",
        "description": "Patch an event; only fields supplied are changed.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "location": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_update_event(**args),
    },
    {
        "name": "calendar_delete_event",
        "description": "Delete an event by id.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string"},
            },
            "required": ["account", "calendar_id", "event_id"],
        },
        "handler": lambda args: calendar_tools.calendar_delete_event(**args),
    },
    # Drive
    {
        "name": "drive_search",
        "description": "Search Drive with Drive query syntax (e.g. \"name contains 'foo'\").",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["account", "query"],
        },
        "handler": lambda args: drive_tools.drive_search(**args),
    },
    {
        "name": "drive_get_file_metadata",
        "description": "Get file metadata (id, name, mime, size, parents, modified_time, link).",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_get_file_metadata(**args),
    },
    {
        "name": "drive_read_file",
        "description": "Read file content. Google Docs→text, Sheets→CSV (first sheet), Slides→text; binary returned as base64.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_read_file(**args),
    },
    {
        "name": "drive_upload_file",
        "description": "Upload a new file. content is text or base64 depending on mime_type.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "name": {"type": "string"},
                "content": {"type": "string"},
                "mime_type": {"type": "string"},
                "parent_folder_id": {"type": "string"},
            },
            "required": ["account", "name", "content", "mime_type"],
        },
        "handler": lambda args: drive_tools.drive_upload_file(**args),
    },
    {
        "name": "drive_update_file",
        "description": "Update an existing file's content and/or name.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
                "content": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_update_file(**args),
    },
    {
        "name": "drive_delete_file",
        "description": "Permanently delete a Drive file.",
        "schema": {
            "type": "object",
            "properties": {
                "account": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["account", "file_id"],
        },
        "handler": lambda args: drive_tools.drive_delete_file(**args),
    },
]


def build_app() -> Server:
    app: Server = Server("multi-google-mcp")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["schema"])
            for t in TOOL_REGISTRY
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        entry = next((t for t in TOOL_REGISTRY if t["name"] == name), None)
        if entry is None:
            raise ValueError(f"unknown tool: {name}")
        try:
            result = entry["handler"](arguments or {})
        except MultiGoogleMcpError as e:
            return [TextContent(type="text", text=f"error: {e}")]
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    return app


def main() -> None:
    async def runner() -> None:
        async with stdio_server() as (read, write):
            app = build_app()
            await app.run(read, write, app.create_initialization_options())

    asyncio.run(runner())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests** — expect 3 passed.

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass (~45 total).

- [ ] **Step 6: Run lint + type checks**

```bash
uv run ruff check .
uv run mypy
```

Expected: no errors. Fix anything that's flagged.

- [ ] **Step 7: Commit**

```bash
git add src/multi_google_mcp/server.py tests/test_server.py
git commit -m "feat(server): MCP stdio entrypoint and 17-tool registry"
```

---

## Phase E — End-to-end verification

### Task 18: E2E smoke script (Levels 1 + 2)

**Files:**
- Create: `scripts/e2e_smoke.py`

This script is **not** part of the unit test suite. It runs against a real
Google test account, opt-in via env var. It also boots the actual MCP
server as a subprocess and drives it over stdio to verify the MCP transport
end-to-end (Level 2), then performs the round-trips against real Google
APIs (Level 1).

- [ ] **Step 1: Write the smoke script**

```python
# scripts/e2e_smoke.py
"""
End-to-end smoke test: spawn the MCP server, drive every tool surface
against a real Google account, clean up after itself.

Usage:
    MCP_E2E_ACCOUNT=test-account uv run python scripts/e2e_smoke.py

The named account must already be configured via:
    multi-google-mcp-auth add test-account
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ACCOUNT_ENV = "MCP_E2E_ACCOUNT"


def _now_tag() -> str:
    return f"mcp-e2e-{uuid.uuid4().hex[:8]}"


async def _call(session: ClientSession, name: str, args: dict) -> dict | list:
    result = await session.call_tool(name, args)
    payload = result.content[0].text
    if payload.startswith("error:"):
        raise RuntimeError(payload)
    return json.loads(payload)


async def _gmail_flow(session: ClientSession, account: str) -> None:
    tag = _now_tag()
    # Find the account's own email so we can send to ourselves.
    accounts = await _call(session, "list_accounts", {})
    self_email = next(a["email"] for a in accounts if a["label"] == account)

    print(f"  gmail: sending self-email with tag {tag}")
    sent = await _call(
        session,
        "gmail_send",
        {"account": account, "to": self_email, "subject": tag, "body": "smoke test"},
    )

    print("  gmail: searching for the message")
    # Allow a moment for the send to land in the inbox.
    await asyncio.sleep(2)
    hits = await _call(
        session, "gmail_search", {"account": account, "query": tag, "max_results": 5}
    )
    if not hits:
        raise RuntimeError(f"sent message with tag {tag} not searchable")

    print("  gmail: trashing the sent message")
    await _call(
        session,
        "gmail_modify_labels",
        {"account": account, "message_id": sent["id"], "trash": True},
    )


async def _calendar_flow(session: ClientSession, account: str) -> None:
    start = dt.datetime.utcnow() + dt.timedelta(days=365)
    end = start + dt.timedelta(hours=1)
    start_str = start.strftime("%Y-%m-%dT%H:%M:00Z")
    end_str = end.strftime("%Y-%m-%dT%H:%M:00Z")
    summary = _now_tag()

    print(f"  calendar: creating event {summary}")
    created = await _call(
        session,
        "calendar_create_event",
        {
            "account": account,
            "calendar_id": "primary",
            "summary": summary,
            "start": start_str,
            "end": end_str,
        },
    )

    print("  calendar: fetching event")
    fetched = await _call(
        session,
        "calendar_get_event",
        {"account": account, "calendar_id": "primary", "event_id": created["id"]},
    )
    if fetched["summary"] != summary:
        raise RuntimeError("calendar round-trip mismatch")

    print("  calendar: deleting event")
    await _call(
        session,
        "calendar_delete_event",
        {"account": account, "calendar_id": "primary", "event_id": created["id"]},
    )


async def _drive_flow(session: ClientSession, account: str) -> None:
    name = f"{_now_tag()}.txt"
    print(f"  drive: uploading {name}")
    uploaded = await _call(
        session,
        "drive_upload_file",
        {
            "account": account,
            "name": name,
            "content": "smoke test content",
            "mime_type": "text/plain",
        },
    )

    print("  drive: reading it back")
    read_back = await _call(
        session, "drive_read_file", {"account": account, "file_id": uploaded["id"]}
    )
    if read_back["content"] != "smoke test content":
        raise RuntimeError("drive round-trip content mismatch")

    print("  drive: deleting it")
    await _call(
        session, "drive_delete_file", {"account": account, "file_id": uploaded["id"]}
    )


async def main() -> int:
    account = os.environ.get(ACCOUNT_ENV)
    if not account:
        print(f"set {ACCOUNT_ENV} to the account label to run against.", file=sys.stderr)
        return 1

    params = StdioServerParameters(command="multi-google-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"discovered {len(tools.tools)} tools over stdio")

            print("gmail flow:")
            await _gmail_flow(session, account)
            print("calendar flow:")
            await _calendar_flow(session, account)
            print("drive flow:")
            await _drive_flow(session, account)

    print("smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 2: Smoke-check the script syntax**

```bash
uv run python -c "import ast; ast.parse(open('scripts/e2e_smoke.py').read())"
```

Expected: no output (parse OK).

- [ ] **Step 3: Document that this is opt-in only — no automated run**

The script needs a real account. Skip executing it in this plan; the README
(Task 19) explains how to run it.

- [ ] **Step 4: Commit**

```bash
git add scripts/e2e_smoke.py
git commit -m "test(e2e): smoke script driving real server over MCP stdio"
```

---

## Phase F — Documentation

### Task 19: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

````markdown
# multi-google-mcp

A local **Model Context Protocol** server that gives Claude Desktop (or any
stdio MCP client) access to multiple Google accounts. Each tool call takes
an explicit `account` label so the agent can operate across accounts in the
same conversation.

**Scope:**
- Gmail: search, read, send, modify labels (incl. trash)
- Google Calendar: list, read, create, update, delete events
- Google Drive: search, read, upload, update, delete files

**Designed for personal local use** on a single machine. Tokens live under
`~/.config/multi-google-mcp/`. Not for hosting or sharing.

---

## Prerequisites

- macOS, Linux, or WSL
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pipx`
- A Google account with admin access to a GCP project (free tier is fine)

## GCP setup (one-time)

Hand these steps to anyone using this server for the first time.

### 1. Create a GCP project

1. Open https://console.cloud.google.com
2. Project picker → **New Project** → name it (e.g. "multi-google-mcp")
3. Wait for the project to be created and select it

### 2. Enable the three APIs

In the project, go to **APIs & Services → Library** and search/enable each:

- **Gmail API**
- **Google Calendar API**
- **Google Drive API**

### 3. Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen**
2. User type: **External**, then **Create**
3. App information:
   - App name: `multi-google-mcp` (anything is fine)
   - User support email: your email
   - Developer contact: your email
4. **Save and continue**
5. Scopes screen: click **Save and continue** (we'll request scopes from the app, not here)
6. Test users: **Add users** — add every Gmail address you intend to connect.
   In **Testing** publishing status, only these emails can authenticate.
7. **Save and continue → Back to dashboard**

> Keep publishing status as **Testing**. For personal use this is fine.
> One quirk: in Testing mode Google sometimes expires refresh tokens
> after 7 days unless the consenting account is also a test user — which
> we just added, so you're covered.

### 4. Create the OAuth client

1. **APIs & Services → Credentials**
2. **Create credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `multi-google-mcp` (anything is fine)
5. **Create**
6. **Download JSON** (the small download icon next to your client)
7. Move that file to:
   ```
   ~/.config/multi-google-mcp/client_secret.json
   ```
   Create the directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/multi-google-mcp
   ```

---

## Install

```bash
# from a clone of this repo
uv tool install .
```

This puts two commands on your `PATH`:

- `multi-google-mcp` — the MCP server (started by Claude Desktop)
- `multi-google-mcp-auth` — manage local OAuth tokens

## Add your first account

```bash
multi-google-mcp-auth add personal
```

A browser window opens. Sign in, accept the scopes. The CLI writes
`~/.config/multi-google-mcp/accounts/personal.json`.

To add another account use a different label:

```bash
multi-google-mcp-auth add work
```

List configured accounts:

```bash
multi-google-mcp-auth list
```

Remove an account:

```bash
multi-google-mcp-auth remove personal
```

## Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and
add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "multi-google": {
      "command": "multi-google-mcp"
    }
  }
}
```

Restart Claude Desktop. You should see the tools listed; ask Claude
something like:

> "Search my work Gmail for unread mail from yesterday."

Claude will call `gmail_search` with `account="work"`.

## Verifying your setup

Add a dedicated test account (e.g. a throwaway Gmail) and run the
end-to-end smoke script. It boots the actual MCP server as a subprocess,
drives every tool surface over stdio against real Google APIs, and cleans
up after itself.

```bash
multi-google-mcp-auth add test-account
MCP_E2E_ACCOUNT=test-account uv run python scripts/e2e_smoke.py
```

Takes ~30 seconds. If everything passes, your local setup is good.

## Adding scopes or new accounts later

- **New account:** rerun `multi-google-mcp-auth add <label>`.
- **Changed scopes:** edit `SCOPES` in `src/multi_google_mcp/config.py`,
  rerun `multi-google-mcp-auth add <label>` for each account — Google
  requires re-consent when scopes change.

## Troubleshooting

| Error | What it means | Fix |
|---|---|---|
| `Account 'work' not configured` | No token file for that label | `multi-google-mcp-auth add work` |
| `Account 'work' needs reauthentication` | Refresh token rejected (revoked, scope changed, or 7d test-mode expiry) | `multi-google-mcp-auth add work` |
| `OAuth client not configured` | `~/.config/multi-google-mcp/client_secret.json` missing | Re-download from GCP Credentials |
| Google `403: insufficient permissions` | Scope wasn't requested or wasn't granted | Add the scope in `config.py`, re-auth |
| Browser hangs on `localhost:<port>` after consent | Local callback failed | Re-run `add`; firewall/VPN may be intercepting localhost |

## Project layout

See [`docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md`](docs/superpowers/specs/2026-05-18-multi-google-mcp-design.md)
and [`docs/superpowers/plans/2026-05-18-multi-google-mcp.md`](docs/superpowers/plans/2026-05-18-multi-google-mcp.md)
for the design and step-by-step implementation history.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: setup, install, claude desktop wiring, verification"
```

---

## Final verification

### Task 20: Whole-suite green

- [ ] **Step 1: Run all tests once more**

```bash
uv run pytest -v
```

Expected: all unit tests pass.

- [ ] **Step 2: Run lint and type checks**

```bash
uv run ruff check .
uv run mypy
```

Expected: clean.

- [ ] **Step 3: Manually run the auth CLI once to verify install layout**

```bash
uv tool install --reinstall .
multi-google-mcp-auth --help
```

Expected: argparse help printed; `add`, `list`, `remove` subcommands listed.

- [ ] **Step 4: (Optional, requires GCP setup) Run the E2E smoke**

```bash
MCP_E2E_ACCOUNT=<your-test-label> uv run python scripts/e2e_smoke.py
```

Expected: `smoke test passed.`

- [ ] **Step 5: Final commit of any lint fixups**

```bash
git status
# If anything outstanding:
git add -p
git commit -m "chore: lint and type-check cleanup"
```

---

## Done criteria

- All 20 tasks checked off.
- `uv run pytest` passes (~45 tests).
- `uv run ruff check .` and `uv run mypy` clean.
- README walks an outside human end-to-end from "no GCP project" to "Claude
  Desktop using my Gmail" in well-defined steps.
- The E2E smoke script passes against a real test account, exercising
  every tool surface over the real MCP stdio transport.
