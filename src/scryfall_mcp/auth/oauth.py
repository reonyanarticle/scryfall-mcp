"""OAuth 2.1 authentication flow for Remote MCP.

This module implements OAuth 2.1 Authorization Code flow with PKCE
(Proof Key for Code Exchange) for secure authentication.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..settings import Settings


class OAuthToken(BaseModel):
    """OAuth token response model.

    Attributes
    ----------
    access_token : str
        JWT access token for API authorization
    token_type : str
        Token type (typically "Bearer")
    expires_in : int
        Token expiration time in seconds
    refresh_token : str | None
        Optional refresh token for token renewal
    scope : str | None
        Optional token scope
    """

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None


class OAuthClient:
    """OAuth 2.1 client implementation.

    Supports Authorization Code with PKCE flow for secure authentication.
    Implements RFC 7636 (PKCE) and RFC 6749 (OAuth 2.0) standards.

    Parameters
    ----------
    settings : Settings
        Application settings containing OAuth configuration

    Examples
    --------
    >>> from scryfall_mcp.settings import get_settings
    >>> client = OAuthClient(get_settings())
    >>> verifier, challenge = client.generate_pkce_pair()
    >>> len(verifier) >= 43
    True
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize OAuth client.

        Parameters
        ----------
        settings : Settings
            Application settings containing OAuth configuration
        """
        self.settings = settings
        self.client = httpx.AsyncClient()

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge per RFC 7636.

        Returns
        -------
        tuple[str, str]
            Code verifier (43-128 chars) and code challenge (SHA256 hashed)

        Notes
        -----
        Implements PKCE (Proof Key for Code Exchange) as required by OAuth 2.1.
        The code_challenge is computed using the S256 method:
        BASE64URL(SHA256(code_verifier))

        See Also
        --------
        RFC 7636: https://datatracker.ietf.org/doc/html/rfc7636

        Examples
        --------
        >>> client = OAuthClient(settings)
        >>> verifier, challenge = client.generate_pkce_pair()
        >>> len(verifier) >= 43
        True
        >>> len(challenge) == 43
        True
        """
        # Generate code verifier (43-128 characters per RFC 7636)
        code_verifier = secrets.token_urlsafe(43)

        # Generate code challenge using S256 method
        code_verifier_bytes = code_verifier.encode("ascii")
        code_challenge_bytes = hashlib.sha256(code_verifier_bytes).digest()
        code_challenge = (
            base64.urlsafe_b64encode(code_challenge_bytes).rstrip(b"=").decode("ascii")
        )

        return code_verifier, code_challenge

    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        scope: str | None = None,
    ) -> tuple[str, str, str]:
        """Get authorization URL for user login.

        Parameters
        ----------
        redirect_uri : str
            Redirect URI after authorization
        state : str | None, optional
            State parameter for CSRF protection.
            If None, generates a random state.
        scope : str | None, optional
            OAuth scopes to request.
            If None, requests default scope.

        Returns
        -------
        tuple[str, str, str]
            Authorization URL, code_verifier, and state

        Notes
        -----
        The code_verifier must be stored securely and used later
        in the token exchange step.

        Examples
        --------
        >>> client = OAuthClient(settings)
        >>> url, verifier, state = await client.get_authorization_url(
        ...     "https://app.example.com/callback"
        ... )
        >>> "response_type=code" in url
        True
        """
        # Generate PKCE parameters
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Generate state if not provided
        if state is None:
            state = secrets.token_urlsafe(32)

        # Build authorization URL (placeholder - configure per provider)
        # This should be configured based on the OAuth provider
        # (e.g., Auth0, Cloudflare Access, Keycloak)
        auth_url = "https://auth.example.com/authorize"
        params = {
            "response_type": "code",
            "client_id": "YOUR_CLIENT_ID",  # Configure in settings
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": scope or "openid profile email",
        }

        # Construct URL
        url = httpx.URL(auth_url, params=params)

        return str(url), code_verifier, state

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OAuthToken:
        """Exchange authorization code for access token.

        Parameters
        ----------
        code : str
            Authorization code from OAuth provider
        redirect_uri : str
            Redirect URI used in authorization request
        code_verifier : str
            PKCE code verifier from authorization request

        Returns
        -------
        OAuthToken
            Access token and metadata

        Raises
        ------
        httpx.HTTPStatusError
            If token exchange fails

        Notes
        -----
        This implements the token exchange step of OAuth 2.1 with PKCE.
        The code_verifier is used by the authorization server to verify
        that the token request comes from the same client that initiated
        the authorization request.

        Examples
        --------
        >>> client = OAuthClient(settings)
        >>> token = await client.exchange_code_for_token(
        ...     code="auth_code_123",
        ...     redirect_uri="https://app.example.com/callback",
        ...     code_verifier="verifier_from_authorization_step"
        ... )
        >>> token.token_type
        'Bearer'
        """
        token_url = "https://auth.example.com/oauth/token"  # Configure per provider

        response = await self.client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": "YOUR_CLIENT_ID",  # Configure in settings
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response.raise_for_status()
        return OAuthToken.model_validate(response.json())

    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh access token using refresh token.

        Parameters
        ----------
        refresh_token : str
            Refresh token from previous token response

        Returns
        -------
        OAuthToken
            New access token and metadata

        Raises
        ------
        httpx.HTTPStatusError
            If token refresh fails

        Examples
        --------
        >>> client = OAuthClient(settings)
        >>> new_token = await client.refresh_token("refresh_token_123")
        >>> new_token.access_token != "refresh_token_123"
        True
        """
        token_url = "https://auth.example.com/oauth/token"  # Configure per provider

        response = await self.client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": "YOUR_CLIENT_ID",  # Configure in settings
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response.raise_for_status()
        return OAuthToken.model_validate(response.json())

    async def close(self) -> None:
        """Close HTTP client connection.

        This should be called when the OAuth client is no longer needed.

        Examples
        --------
        >>> client = OAuthClient(settings)
        >>> await client.close()
        """
        await self.client.aclose()
