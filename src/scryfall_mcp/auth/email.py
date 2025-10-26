"""Email-based authentication helpers for Scryfall MCP Server.

This module provides utilities for email-based authentication as a simpler
alternative to OAuth 2.1 + JWT for personal/development deployments.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def parse_basic_auth_header(authorization: str) -> tuple[str, str] | None:
    """Parse HTTP Basic authentication header.

    Parameters
    ----------
    authorization : str
        Authorization header value (e.g., "Basic dXNlckBleGFtcGxlLmNvbTpzZWNyZXQ=")

    Returns
    -------
    tuple[str, str] | None
        (email, secret) if valid Basic auth, None otherwise

    Examples
    --------
    >>> header = "Basic " + base64.b64encode(b"user@example.com:secret123").decode()
    >>> parse_basic_auth_header(header)
    ('user@example.com', 'secret123')
    >>> parse_basic_auth_header("Bearer token123")
    None
    """
    if not authorization.startswith("Basic "):
        return None

    try:
        # Extract base64-encoded credentials
        encoded = authorization[6:]  # Remove "Basic " prefix
        decoded = base64.b64decode(encoded).decode("utf-8")

        # Split into email:secret
        if ":" not in decoded:
            return None

        email, secret = decoded.split(":", 1)
        return email.strip(), secret

    except (ValueError, UnicodeDecodeError):
        return None


def hash_secret(secret: str) -> str:
    """Hash a secret using SHA-256.

    Parameters
    ----------
    secret : str
        Plain-text secret to hash

    Returns
    -------
    str
        Hex-encoded SHA-256 hash

    Examples
    --------
    >>> hash_secret("my-secret-key")
    '...'  # 64-character hex string
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_secret(provided: str, expected_hash: str) -> bool:
    """Verify a secret against its hash using constant-time comparison.

    Parameters
    ----------
    provided : str
        Plain-text secret provided by user
    expected_hash : str
        Hex-encoded SHA-256 hash to compare against

    Returns
    -------
    bool
        True if secret matches hash

    Examples
    --------
    >>> hashed = hash_secret("correct-secret")
    >>> verify_secret("correct-secret", hashed)
    True
    >>> verify_secret("wrong-secret", hashed)
    False
    """
    provided_hash = hash_secret(provided)
    return hmac.compare_digest(provided_hash, expected_hash)


def is_email_blocked(email: str, blocklist_patterns: list[str]) -> bool:
    """Check if email matches any blocklist pattern.

    Parameters
    ----------
    email : str
        Email address to check
    blocklist_patterns : list[str]
        List of patterns (supports * wildcards)

    Returns
    -------
    bool
        True if email matches any pattern

    Examples
    --------
    >>> is_email_blocked("test@example.com", ["*@example.com"])
    True
    >>> is_email_blocked("user@real-domain.com", ["*@example.com", "test@*"])
    False
    >>> is_email_blocked("test@any-domain.com", ["test@*"])
    True
    """
    import fnmatch

    return any(fnmatch.fnmatch(email, pattern) for pattern in blocklist_patterns)


def validate_email_credentials(
    email: str, secret: str, credentials: Mapping[str, str], blocklist: list[str]
) -> bool:
    """Validate email and secret against allowed credentials.

    Parameters
    ----------
    email : str
        Email address to validate
    secret : str
        Plain-text secret to verify
    credentials : Mapping[str, str]
        Email to hashed secret mapping
    blocklist : list[str]
        Email patterns to block

    Returns
    -------
    bool
        True if email is allowed and secret is correct

    Examples
    --------
    >>> creds = {"user@example.com": hash_secret("secret123")}
    >>> validate_email_credentials("user@example.com", "secret123", creds, [])
    True
    >>> validate_email_credentials("user@example.com", "wrong", creds, [])
    False
    >>> validate_email_credentials("test@example.com", "any", creds, ["test@*"])
    False
    """
    # Check blocklist first
    if is_email_blocked(email, blocklist):
        return False

    # Check if email exists in credentials
    if email not in credentials:
        return False

    # Verify secret
    expected_hash = credentials[email]
    return verify_secret(secret, expected_hash)
