"""Tests for email-based authentication module.

Tests cover bcrypt hashing, Basic auth parsing, email validation,
and PII masking for GDPR/CCPA compliance.
"""

from __future__ import annotations

import base64

import pytest

from scryfall_mcp.auth.email import (
    hash_secret,
    is_email_blocked,
    parse_basic_auth_header,
    validate_email_credentials,
    verify_secret,
)


class TestParseBasicAuthHeader:
    """Test HTTP Basic authentication header parsing."""

    def test_parse_valid_basic_auth(self) -> None:
        """Test parsing valid Basic auth header."""
        # Arrange
        credentials = "user@example.com:secret123"
        encoded = base64.b64encode(credentials.encode()).decode()
        header = f"Basic {encoded}"

        # Act
        result = parse_basic_auth_header(header)

        # Assert
        assert result is not None
        email, secret = result
        assert email == "user@example.com"
        assert secret == "secret123"

    def test_parse_with_whitespace_in_email(self) -> None:
        """Test parsing strips whitespace from email."""
        credentials = "  user@example.com  :secret123"
        encoded = base64.b64encode(credentials.encode()).decode()
        header = f"Basic {encoded}"

        result = parse_basic_auth_header(header)

        assert result is not None
        email, _ = result
        assert email == "user@example.com"

    def test_parse_with_colon_in_secret(self) -> None:
        """Test secret can contain colons."""
        credentials = "user@example.com:secret:with:colons"
        encoded = base64.b64encode(credentials.encode()).decode()
        header = f"Basic {encoded}"

        result = parse_basic_auth_header(header)

        assert result is not None
        _, secret = result
        assert secret == "secret:with:colons"

    def test_parse_bearer_token_returns_none(self) -> None:
        """Test non-Basic auth returns None."""
        header = "Bearer jwt-token-here"
        result = parse_basic_auth_header(header)
        assert result is None

    def test_parse_missing_basic_prefix_returns_none(self) -> None:
        """Test missing 'Basic ' prefix returns None."""
        credentials = "user@example.com:secret123"
        encoded = base64.b64encode(credentials.encode()).decode()

        result = parse_basic_auth_header(encoded)
        assert result is None

    def test_parse_invalid_base64_returns_none(self) -> None:
        """Test invalid base64 encoding returns None."""
        header = "Basic invalid-base64!!!"
        result = parse_basic_auth_header(header)
        assert result is None

    def test_parse_missing_colon_returns_none(self) -> None:
        """Test credentials without colon returns None."""
        credentials = "user@example.com"  # No colon
        encoded = base64.b64encode(credentials.encode()).decode()
        header = f"Basic {encoded}"

        result = parse_basic_auth_header(header)
        assert result is None

    def test_parse_non_utf8_returns_none(self) -> None:
        """Test non-UTF8 encoded credentials returns None."""
        # Invalid UTF-8 sequence
        invalid_bytes = b"\xff\xfe"
        encoded = base64.b64encode(invalid_bytes).decode()
        header = f"Basic {encoded}"

        result = parse_basic_auth_header(header)
        assert result is None


class TestHashAndVerifySecret:
    """Test bcrypt hashing and verification."""

    def test_hash_secret_returns_valid_bcrypt_format(self) -> None:
        """Test hash_secret returns valid bcrypt hash."""
        secret = "my-secret-key"

        hashed = hash_secret(secret)

        # bcrypt format: $2b$12$<22-char-salt><31-char-hash>
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_secret_different_each_time(self) -> None:
        """Test each hash has unique salt."""
        secret = "same-secret"

        hash1 = hash_secret(secret)
        hash2 = hash_secret(secret)

        # Different salts -> different hashes
        assert hash1 != hash2

    def test_verify_secret_with_correct_secret(self) -> None:
        """Test verify_secret returns True for correct secret."""
        secret = "correct-secret"
        hashed = hash_secret(secret)

        result = verify_secret(secret, hashed)

        assert result is True

    def test_verify_secret_with_wrong_secret(self) -> None:
        """Test verify_secret returns False for wrong secret."""
        correct_secret = "correct-secret"
        wrong_secret = "wrong-secret"
        hashed = hash_secret(correct_secret)

        result = verify_secret(wrong_secret, hashed)

        assert result is False

    def test_verify_secret_with_empty_string(self) -> None:
        """Test verify_secret handles empty strings."""
        hashed = hash_secret("non-empty")

        result = verify_secret("", hashed)

        assert result is False

    def test_verify_secret_with_invalid_hash_format(self) -> None:
        """Test verify_secret returns False for invalid hash."""
        result = verify_secret("any-secret", "invalid-hash-format")

        assert result is False

    def test_verify_secret_with_none_hash_returns_false(self) -> None:
        """Test verify_secret handles None gracefully."""
        # Type error should be caught
        result = verify_secret("secret", None)  # type: ignore[arg-type]

        assert result is False

    def test_hash_verify_roundtrip(self) -> None:
        """Test hash -> verify roundtrip with various secrets."""
        test_secrets = [
            "simple",
            "with-special-chars!@#$%",
            "a-72-byte-secret-limit",  # bcrypt has 72-byte limit
            "日本語シークレット",  # Unicode
            "secret with spaces",
        ]

        for secret in test_secrets:
            hashed = hash_secret(secret)
            assert verify_secret(secret, hashed), f"Failed for secret: {secret}"


class TestIsEmailBlocked:
    """Test email blocklist pattern matching."""

    def test_exact_match_blocked(self) -> None:
        """Test exact email match is blocked."""
        blocklist = ["blocked@example.com"]

        result = is_email_blocked("blocked@example.com", blocklist)

        assert result is True

    def test_wildcard_domain_match(self) -> None:
        """Test wildcard domain pattern blocks email."""
        blocklist = ["*@example.com"]

        assert is_email_blocked("user@example.com", blocklist) is True
        assert is_email_blocked("admin@example.com", blocklist) is True

    def test_wildcard_user_match(self) -> None:
        """Test wildcard user pattern blocks email."""
        blocklist = ["test@*"]

        assert is_email_blocked("test@example.com", blocklist) is True
        assert is_email_blocked("test@any-domain.org", blocklist) is True

    def test_not_blocked_with_different_email(self) -> None:
        """Test email not matching pattern is allowed."""
        blocklist = ["*@example.com", "test@*"]

        result = is_email_blocked("user@allowed.com", blocklist)

        assert result is False

    def test_empty_blocklist_allows_all(self) -> None:
        """Test empty blocklist allows all emails."""
        result = is_email_blocked("any@example.com", [])

        assert result is False

    def test_multiple_patterns_any_match_blocks(self) -> None:
        """Test any matching pattern blocks email."""
        blocklist = ["*@spam.com", "abuse@*", "test@example.com"]

        assert is_email_blocked("user@spam.com", blocklist) is True
        assert is_email_blocked("abuse@anywhere.com", blocklist) is True
        assert is_email_blocked("test@example.com", blocklist) is True


class TestValidateEmailCredentials:
    """Test email credential validation."""

    def test_valid_credentials_returns_true(self) -> None:
        """Test validation succeeds with correct credentials."""
        email = "user@example.com"
        secret = "correct-secret"
        hashed = hash_secret(secret)
        credentials = {email: hashed}

        result = validate_email_credentials(email, secret, credentials, [])

        assert result is True

    def test_wrong_secret_returns_false(self) -> None:
        """Test validation fails with wrong secret."""
        email = "user@example.com"
        correct_secret = "correct-secret"
        wrong_secret = "wrong-secret"
        hashed = hash_secret(correct_secret)
        credentials = {email: hashed}

        result = validate_email_credentials(email, wrong_secret, credentials, [])

        assert result is False

    def test_unknown_email_returns_false(self) -> None:
        """Test validation fails for unregistered email."""
        credentials = {"user@example.com": hash_secret("secret")}

        result = validate_email_credentials("unknown@example.com", "any", credentials, [])

        assert result is False

    def test_blocked_email_returns_false(self) -> None:
        """Test validation fails for blocked email."""
        email = "blocked@example.com"
        secret = "correct-secret"
        hashed = hash_secret(secret)
        credentials = {email: hashed}
        blocklist = ["blocked@*"]

        result = validate_email_credentials(email, secret, credentials, blocklist)

        assert result is False

    def test_blocklist_checked_before_credentials(self) -> None:
        """Test blocklist is checked before credential lookup."""
        # Even with valid credentials, blocked email should fail
        email = "test@spam.com"
        secret = "secret"
        hashed = hash_secret(secret)
        credentials = {email: hashed}
        blocklist = ["*@spam.com"]

        result = validate_email_credentials(email, secret, credentials, blocklist)

        assert result is False

    def test_empty_credentials_dict_returns_false(self) -> None:
        """Test validation fails with empty credentials."""
        result = validate_email_credentials("any@example.com", "any", {}, [])

        assert result is False
