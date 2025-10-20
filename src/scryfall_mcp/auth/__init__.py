"""Authentication module for Remote MCP support.

This module provides JWT validation middleware and OAuth 2.1 flow implementation
for secure Remote MCP access.
"""

from __future__ import annotations

from .middleware import JWTValidationMiddleware
from .oauth import OAuthClient, OAuthToken

__all__ = ["JWTValidationMiddleware", "OAuthClient", "OAuthToken"]
