"""Authentication module for Remote MCP support.

This module provides JWT validation middleware and OAuth 2.1 flow implementation
for secure Remote MCP access, as well as email-based authentication for simpler
deployments.
"""

from __future__ import annotations

from .middleware import EmailAuthMiddleware, JWTValidationMiddleware
from .oauth import OAuthClient, OAuthToken

__all__ = [
    "EmailAuthMiddleware",
    "JWTValidationMiddleware",
    "OAuthClient",
    "OAuthToken",
]
