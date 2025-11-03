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


# Create Mangum handler
# lifespan="off" is recommended for Lambda to avoid lifecycle management issues
_mangum_handler = Mangum(
    app=get_server().app,
    lifespan="off",
    api_gateway_base_path="/mcp",
)


def handler(event: LambdaEvent, context: LambdaContext) -> dict[str, Any]:
    """AWS Lambda entry point for MCP requests.

    This function is invoked by AWS Lambda when an HTTP request arrives
    via API Gateway. It delegates to Mangum to convert the Lambda event
    to an ASGI request and routes it to the FastMCP application.

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

    Examples
    --------
    Typical Lambda event structure:

    >>> event = {
    ...     "requestContext": {"http": {"method": "POST", "path": "/mcp"}},
    ...     "headers": {"authorization": "Bearer <token>"},
    ...     "body": '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
    ... }
    >>> response = handler(event, context)
    >>> assert response["statusCode"] == 200

    Notes
    -----
    - Cold starts: First invocation may take 1-3 seconds
    - Warm invocations: Typically <100ms due to server reuse
    - Memory: Configured for 768MB in serverless.yml (optimal balance)
    - Timeout: 30 seconds max (API Gateway maximum)

    The handler automatically:
    - Validates JWT tokens via API Gateway authorizer (when enabled)
    - Enforces CORS policies (configured in serverless.yml)
    - Applies rate limiting (via RateLimiterManager)
    - Uses in-memory caching (no Redis for cost optimization)
    """
    settings = get_settings()

    # Log request details for debugging (sanitized)
    if settings.log_level == "DEBUG":
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Lambda invocation - Request ID: {context.aws_request_id}, "
            f"Path: {event.get('requestContext', {}).get('http', {}).get('path', 'unknown')}"
        )

    return _mangum_handler(event, context)
