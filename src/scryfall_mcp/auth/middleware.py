"""JWT validation middleware for Remote MCP authentication.

This module provides ASGI middleware to validate JWT tokens for secure
Remote MCP access with OAuth 2.1 authentication.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from jose import JWTError, jwt

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..settings import Settings

# ASGI type definitions
ASGIScope = dict[str, Any]
ASGIReceiveCallable = Callable[[], Awaitable[dict[str, Any]]]
ASGISendCallable = Callable[[dict[str, Any]], Awaitable[None]]


class AuthenticationError(Exception):
    """Authentication failure, converted to an HTTP 401 response.

    Raw ASGI middleware added via ``add_middleware`` runs *outside*
    Starlette's exception handling, so raising ``HTTPException`` there
    would surface as a 500. Instead, the middlewares catch this exception
    and emit the 401 response directly on the ASGI ``send`` channel.

    Parameters
    ----------
    detail : str
        Human-readable error message (returned to the client as JSON)
    headers : dict[str, str] | None, optional (default: None)
        Additional response headers (e.g. ``WWW-Authenticate``)
    """

    def __init__(self, detail: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.headers = headers or {}


async def _send_unauthorized(
    send: ASGISendCallable, error: AuthenticationError
) -> None:
    """Send a 401 JSON response directly on the ASGI send channel."""
    body = json.dumps({"detail": error.detail}).encode("utf-8")
    headers: list[tuple[bytes, bytes]] = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    headers.extend(
        (key.encode("ascii"), value.encode("ascii"))
        for key, value in error.headers.items()
    )
    await send({"type": "http.response.start", "status": 401, "headers": headers})
    await send({"type": "http.response.body", "body": body})


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

        Notes
        -----
        Authentication failures are answered directly with a 401 response;
        they are not raised past this middleware.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract and validate token
        try:
            user_payload = await self._validate_jwt_from_scope(scope)
        except AuthenticationError as error:
            await _send_unauthorized(send, error)
            return
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
        AuthenticationError
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
        AuthenticationError
            If Authorization header is missing or invalid
        """
        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization", b"").decode()

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token: str = auth_header[7:]  # Remove "Bearer " prefix
        return token

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
        AuthenticationError
            If token signature is invalid, expired, or malformed
        """
        options = {
            "verify_exp": True,  # Verify expiration time
            "verify_iat": True,  # Verify issued at time
            "verify_nbf": True,  # Verify not before time
            "require_exp": True,  # Require exp claim
            "require_iat": True,  # Require iat claim
        }
        decode_kwargs: dict[str, Any] = {}

        # Mirror the API Gateway authorizer: reject tokens minted for other
        # audiences/issuers even though they share the signing secret.
        if self.settings.jwt_audience:
            decode_kwargs["audience"] = self.settings.jwt_audience
            options["verify_aud"] = True
        if self.settings.jwt_issuer:
            decode_kwargs["issuer"] = self.settings.jwt_issuer

        try:
            decoded: dict[str, Any] = jwt.decode(
                token,
                self.settings.jwt_secret_key.get_secret_value(),
                algorithms=[self.settings.jwt_algorithm],
                options=options,
                **decode_kwargs,
            )
            return decoded
        except JWTError as e:
            logger.warning("JWT validation failed: %s", e)
            raise AuthenticationError("Invalid or expired token") from e


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
        app: Callable[
            [ASGIScope, ASGIReceiveCallable, ASGISendCallable], Awaitable[None]
        ],
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

    def _extract_credentials(self, scope: ASGIScope) -> tuple[str, str]:
        """Extract and parse credentials from ASGI scope.

        Parameters
        ----------
        scope : ASGIScope
            ASGI connection scope

        Returns
        -------
        tuple[str, str]
            Email and secret from Basic auth header

        Raises
        ------
        AuthenticationError
            401 if header is missing or invalid
        """
        from .email import parse_basic_auth_header

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")

        if not auth_header:
            raise AuthenticationError(
                "Missing Authorization header",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        credentials = parse_basic_auth_header(auth_header)
        if credentials is None:
            raise AuthenticationError(
                "Invalid Authorization header format. Expected: Basic base64(email:secret)",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        return credentials

    def _validate_and_log_auth(self, email: str, secret: str) -> str:
        """Validate credentials and log authentication result.

        Parameters
        ----------
        email : str
            User email address
        secret : str
            User secret/password

        Returns
        -------
        str
            Masked email for logging

        Raises
        ------
        AuthenticationError
            401 if validation fails
        """
        from .email import validate_email_credentials

        masked_email = self._mask_email(email)

        is_valid = validate_email_credentials(
            email=email,
            secret=secret,
            credentials=self.settings.email_auth_credentials,
            blocklist=self.settings.email_blocklist_patterns,
        )

        if not is_valid:
            logger.warning(f"Authentication failed for user: {masked_email}")
            raise AuthenticationError(
                "Invalid email or secret",
                headers={"WWW-Authenticate": 'Basic realm="Scryfall MCP"'},
            )

        logger.info(f"User authenticated: {masked_email}")
        return masked_email

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

        Notes
        -----
        Authentication failures are answered directly with a 401 response;
        they are not raised past this middleware.
        """
        # Only authenticate HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract and validate credentials
        try:
            email, secret = self._extract_credentials(scope)
            masked_email = self._validate_and_log_auth(email, secret)
        except AuthenticationError as error:
            await _send_unauthorized(send, error)
            return

        # Add user info to scope (same format as JWT middleware)
        scope["user"] = {"email": email, "masked_email": masked_email}

        # Continue to application
        await self.app(scope, receive, send)
