"""Errors surfaced to MCP tool callers."""


class MultiGoogleMcpError(Exception):
    """Base class for all multi-google-mcp errors."""


class AccountNotConfigured(MultiGoogleMcpError):
    def __init__(self, label: str) -> None:
        super().__init__(
            f"Account '{label}' not configured. Run: multi-google-mcp-auth add {label}"
        )
        self.label = label


class AccountNeedsReauth(MultiGoogleMcpError):
    def __init__(self, label: str) -> None:
        super().__init__(
            f"Account '{label}' needs reauthentication. "
            f"Run: multi-google-mcp-auth add {label}"
        )
        self.label = label


class OAuthClientNotConfigured(MultiGoogleMcpError):
    def __init__(self) -> None:
        super().__init__(
            "OAuth client not configured: client_secret.json missing. See README §Setup."
        )


class InvalidAccountLabel(MultiGoogleMcpError):
    """Raised when an account label fails the slug validation.

    Labels must match a strict slug pattern; anything else risks path
    traversal into the account-token directory.
    """

    def __init__(self, label: str) -> None:
        super().__init__(
            f"Invalid account label {label!r}. Labels must be 1-64 chars "
            "from [a-zA-Z0-9_-] only."
        )
        self.label = label


class DriveFileTooLarge(MultiGoogleMcpError):
    """Raised when a Drive read/upload payload exceeds the configured cap."""

    def __init__(self, size: int, cap: int) -> None:
        super().__init__(
            f"Drive payload too large: {size} bytes exceeds cap of {cap} bytes. "
            "Use the Drive web UI for files this size."
        )
        self.size = size
        self.cap = cap
