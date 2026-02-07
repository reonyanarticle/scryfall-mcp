"""AWS Lambda handler for Scryfall MCP Server.

This module provides the entry point for AWS Lambda deployment of the
Scryfall MCP Server, using Mangum as an ASGI adapter to bridge FastMCP's
Starlette/FastAPI implementation with AWS API Gateway.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mangum import Mangum

from scryfall_mcp.server import ScryfallMCPServer
from scryfall_mcp.settings import get_settings

if TYPE_CHECKING:
    from mangum.types import LambdaContext, LambdaEvent

# Initialize server instance (reused across Lambda invocations)
_server: ScryfallMCPServer | None = None


def get_server() -> ScryfallMCPServer:
    """Get or create ScryfallMCPServer instance.

    This function implements lazy initialization and reuses the server
    instance across Lambda invocations to avoid cold start overhead.

    Returns
    -------
    ScryfallMCPServer
        Initialized MCP server instance

    Notes
    -----
    The server instance is cached in the global `_server` variable and
    reused for subsequent invocations within the same Lambda container.
    This significantly reduces cold start latency.
    """
    global _server
    if _server is None:
        _server = ScryfallMCPServer()
    return _server


# Lazily initialized Mangum handler (avoids module-level server instantiation)
_mangum_handler: Mangum | None = None


def _get_mangum_handler() -> Mangum:
    """Get or create the Mangum ASGI handler.

    Returns
    -------
    Mangum
        Configured Mangum handler instance
    """
    global _mangum_handler
    if _mangum_handler is None:
        _mangum_handler = Mangum(
            app=get_server().app,
            lifespan="off",
            api_gateway_base_path="/mcp",
        )
    return _mangum_handler


def handler(event: LambdaEvent, context: LambdaContext) -> dict[str, Any]:
    """AWS Lambda entry point for MCP requests.

    Parameters
    ----------
    event : LambdaEvent
        AWS Lambda event dict containing HTTP request data from API Gateway
    context : LambdaContext
        AWS Lambda context object with runtime information

    Returns
    -------
    dict[str, Any]
        API Gateway-compatible response dict with statusCode, headers, and body
    """
    settings = get_settings()

    if settings.log_level == "DEBUG":
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "Lambda invocation - Request ID: %s, Path: %s",
            context.aws_request_id,
            event.get("requestContext", {}).get("http", {}).get("path", "unknown"),
        )

    return _get_mangum_handler()(event, context)
