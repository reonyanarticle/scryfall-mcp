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



class EmailAuthMiddleware:
    """Middleware for email-based authentication (alternative to JWT).

    This middleware validates HTTP Basic authentication credentials
    (email:secret) as a simpler alternative to OAuth/JWT for personal deployments.

    Parameters
    ----------
    app : Callable
        The ASGI application to wrap
    settings : Settings
        Application settings containing email credentials

    Examples
    --------
    >>> from starlette.applications import Starlette
    >>> app = Starlette()
    >>> app.add_middleware(EmailAuthMiddleware, settings=settings)
    """

    def __init__(
        self,
        app: Callable[[ASGIScope, ASGIReceiveCallable, ASGISendCallable], Awaitable[None]],
        settings: Settings,
    ) -> None:
        """Initialize email authentication middleware.

        Parameters
        ----------
        app : Callable
            ASGI application callable
        settings : Settings
            Application settings
        """
        self.app = app
        self.settings = settings


    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email address for logging (GDPR/CCPA compliance).

        Returns first 2 characters + SHA-256 hash prefix (8 chars) to allow
        correlation across logs without exposing PII.

        Parameters
        ----------
        email : str
            Email address to mask

        Returns
        -------
        str
            Masked email (e.g., "us:a3f2c8b1" for "user@example.com")

        Examples
        --------
        >>> EmailAuthMiddleware._mask_email("user@example.com")
        'us:a3f2c8b1...'
        """
        import hashlib

        prefix = email if len(email) < 2 else email[:2]
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:8]
        return f"{prefix}:{email_hash}"

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        """Process ASGI request with email authentication.

        Parameters
        ----------
        scope : ASGIScope
            ASGI connection scope
        receive : ASGIReceiveCallable
            ASGI receive callable
        send : ASGISendCallable
            ASGI send callable

        Raises
        ------
        HTTPException
            401 if authentication fails
        """
        # Only authenticate HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")

        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        # Parse Basic auth credentials
        from .email import parse_basic_auth_header, validate_email_credentials

        credentials = parse_basic_auth_header(auth_header)
        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid Authorization header format. Expected: Basic base64(email:secret)",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        email, secret = credentials

        # Validate credentials
        is_valid = validate_email_credentials(
            email=email,
            secret=secret,
            credentials=self.settings.email_auth_credentials,
            blocklist=self.settings.email_blocklist_patterns,
        )

        if not is_valid:
            # Log failed authentication with masked email
            import logging

            logger = logging.getLogger(__name__)
            masked_email = self._mask_email(email)
            logger.warning(f"Authentication failed for user: {masked_email}")

            raise HTTPException(
                status_code=401,
                detail="Invalid email or secret",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        # Log successful authentication (GDPR/CCPA compliant)
        import logging

        logger = logging.getLogger(__name__)
        masked_email = self._mask_email(email)
        logger.info(f"User authenticated: {masked_email}")

        # Add user info to scope (same format as JWT middleware)
        # Store masked email in scope to prevent downstream PII exposure
        scope["user"] = {"email": email, "masked_email": masked_email}

        # Continue to application
        await self.app(scope, receive, send)
