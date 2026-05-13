"""Domain-specific exceptions."""


class AstrologyMcpError(Exception):
    """Base exception for application-specific failures."""


class AuthorizationError(AstrologyMcpError):
    """Raised when an API key is missing or invalid."""
