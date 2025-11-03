"""Email-based authentication helpers for Scryfall MCP Server.

This module provides utilities for email-based authentication as a simpler
alternative to OAuth 2.1 + JWT for personal/development deployments.

Security: Uses bcrypt for password hashing with automatic salt generation.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import bcrypt

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
    """Hash a secret using bcrypt with automatic salt generation.

    Uses bcrypt algorithm with cost factor 12 (2^12 iterations) for
    resistance against brute-force attacks. Each hash includes a unique
    random salt, preventing rainbow table attacks.

    Parameters
    ----------
    secret : str
        Plain-text secret to hash

    Returns
    -------
    str
        bcrypt hash string (includes algorithm, cost, salt, and hash)

    Examples
    --------
    >>> hashed = hash_secret("my-secret-key")
    >>> hashed.startswith("$2b$")  # bcrypt format
    True
    >>> len(hashed)
    60

    Notes
    -----
    bcrypt hashes are 60 characters in format: $2b$12$<22-char-salt><31-char-hash>
    Cost factor 12 provides good security/performance balance (~300ms/hash).
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_secret(provided: str, expected_hash: str) -> bool:
    """Verify a secret against its bcrypt hash using constant-time comparison.

    bcrypt.checkpw() internally uses constant-time comparison to prevent
    timing attacks. The salt is extracted from the hash automatically.

    Parameters
    ----------
    provided : str
        Plain-text secret provided by user
    expected_hash : str
        bcrypt hash string (60 characters)

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

    Notes
    -----
    This function is resistant to timing attacks due to bcrypt's
    constant-time comparison and slow hashing (cost factor 12).
    """
    try:
        return bcrypt.checkpw(provided.encode("utf-8"), expected_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Invalid hash format or encoding error
        return False


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
