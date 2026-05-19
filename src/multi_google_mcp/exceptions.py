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
