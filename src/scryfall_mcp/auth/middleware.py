"""JWT validation middleware for Remote MCP authentication.

This module provides ASGI middleware to validate JWT tokens for secure
Remote MCP access with OAuth 2.1 authentication.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from jose import JWTError, jwt

if TYPE_CHECKING:
    from ..settings import Settings

# ASGI type definitions
ASGIScope = dict[str, Any]
ASGIReceiveCallable = Callable[[], Awaitable[dict[str, Any]]]
ASGISendCallable = Callable[[dict[str, Any]], Awaitable[None]]


class JWTValidationMiddleware:
    """Middleware for validating JWT tokens in MCP requests.

    This middleware extracts and validates JWT tokens from the Authorization
    header, adding user information to the request scope for downstream handlers.

    Parameters
    ----------
    app : Any
        ASGI application instance
    settings : Settings
        Application settings containing JWT configuration

    Examples
    --------
    >>> from scryfall_mcp.settings import get_settings
    >>> settings = get_settings()
    >>> middleware = JWTValidationMiddleware(app, settings)
    """

    def __init__(self, app: Any, settings: Settings) -> None:
        """Initialize JWT validation middleware.

        Parameters
        ----------
        app : Any
            ASGI application instance
        settings : Settings
            Application settings containing JWT configuration
        """
        self.app = app
        self.settings = settings

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        """Process request and validate JWT token.

        Parameters
        ----------
        scope : ASGIScope
            ASGI scope dictionary containing request metadata
        receive : ASGIReceiveCallable
            ASGI receive callable for request body
        send : ASGISendCallable
            ASGI send callable for response

        Raises
        ------
        HTTPException
            If token is missing, invalid, or expired
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract and validate token
        user_payload = await self._validate_jwt_from_scope(scope)
        scope["user"] = user_payload

        await self.app(scope, receive, send)

    async def _validate_jwt_from_scope(self, scope: ASGIScope) -> dict[str, Any]:
        """Extract and validate JWT token from ASGI scope.

        Parameters
        ----------
        scope : ASGIScope
            ASGI scope containing request headers

        Returns
        -------
        dict[str, Any]
            Decoded JWT payload with user information

        Raises
        ------
        HTTPException
            If token is missing, invalid, or expired
        """
        token = self._extract_bearer_token(scope)
        return self._decode_and_verify_token(token)

    def _extract_bearer_token(self, scope: ASGIScope) -> str:
        """Extract Bearer token from Authorization header.

        Parameters
        ----------
        scope : ASGIScope
            ASGI scope containing request headers

        Returns
        -------
        str
            Extracted JWT token

        Raises
        ------
        HTTPException
            If Authorization header is missing or invalid
        """
        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization", b"").decode()

        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
            )

        return auth_header[7:]  # Remove "Bearer " prefix

    def _decode_and_verify_token(self, token: str) -> dict[str, Any]:
        """Decode and verify JWT token signature.

        Parameters
        ----------
        token : str
            JWT token to validate

        Returns
        -------
        dict[str, Any]
            Decoded JWT payload containing user claims

        Raises
        ------
        HTTPException
            If token signature is invalid, expired, or malformed
        """
        try:
            return jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
                options={
                    "verify_exp": True,  # Verify expiration time
                    "verify_iat": True,  # Verify issued at time
                    "verify_nbf": True,  # Verify not before time
                    "require_exp": True,  # Require exp claim
                    "require_iat": True,  # Require iat claim
                },
            )
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {e}",
            ) from e
