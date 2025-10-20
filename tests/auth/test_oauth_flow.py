"""Tests for OAuth 2.1 flow implementation."""

from __future__ import annotations

import pytest

from scryfall_mcp.auth.oauth import OAuthClient
from scryfall_mcp.settings import Settings


class TestOAuthClient:
    """Test OAuth 2.1 client."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def oauth_client(self, settings: Settings) -> OAuthClient:
        """Create OAuth client instance."""
        return OAuthClient(settings)

    def test_generate_pkce_pair(self, oauth_client: OAuthClient) -> None:
        """Test PKCE code verifier and challenge generation."""
        verifier, challenge = oauth_client.generate_pkce_pair()

        # Verify verifier length (43-128 chars per RFC 7636)
        assert 43 <= len(verifier) <= 128

        # Verify challenge length (Base64URL encoded SHA256 = 43 chars without padding)
        assert len(challenge) == 43

        # Verify challenge is different from verifier
        assert challenge != verifier

        # Verify consistency: same verifier should produce same challenge
        import base64
        import hashlib

        expected_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge == expected_challenge

    def test_generate_pkce_pair_uniqueness(self, oauth_client: OAuthClient) -> None:
        """Test that each PKCE generation produces unique values."""
        verifier1, challenge1 = oauth_client.generate_pkce_pair()
        verifier2, challenge2 = oauth_client.generate_pkce_pair()

        # Verify uniqueness
        assert verifier1 != verifier2
        assert challenge1 != challenge2

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, oauth_client: OAuthClient) -> None:
        """Test authorization URL generation."""
        import urllib.parse

        redirect_uri = "https://app.example.com/callback"

        url, verifier, state = await oauth_client.get_authorization_url(redirect_uri)

        # Verify URL structure
        assert "response_type=code" in url
        assert "code_challenge_method=S256" in url
        # Check URL-encoded redirect_uri
        assert urllib.parse.quote(redirect_uri, safe="") in url

        # Verify PKCE verifier
        assert len(verifier) >= 43

        # Verify state
        assert len(state) >= 32

    @pytest.mark.asyncio
    async def test_get_authorization_url_with_custom_state(
        self, oauth_client: OAuthClient
    ) -> None:
        """Test authorization URL with custom state."""
        custom_state = "custom_state_value_123"
        redirect_uri = "https://app.example.com/callback"

        url, verifier, state = await oauth_client.get_authorization_url(
            redirect_uri, state=custom_state
        )

        # Verify custom state is used
        assert state == custom_state
        assert custom_state in url

    @pytest.mark.asyncio
    async def test_close(self, oauth_client: OAuthClient) -> None:
        """Test client cleanup."""
        # Should not raise any exception
        await oauth_client.close()
