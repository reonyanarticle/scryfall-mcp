"""Main module entry point for Scryfall MCP Server.

Provides CLI commands for running the server and managing configuration.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

import typer

from .server import ScryfallMCPServer
from .settings import get_settings
from .setup_wizard import get_config_file, reset_config, run_setup_wizard

app = typer.Typer(
    name="scryfall-mcp",
    help="Scryfall MCP Server - Magic: The Gathering card information via MCP protocol",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    """Run the stdio server when no subcommand is given.

    Keeps `scryfall-mcp` (bare) working for MCP clients such as Claude
    Desktop, whose configurations launch the command without arguments.
    """
    if ctx.invoked_subcommand is None:
        serve()


@app.command()
def serve(
    transport: Annotated[
        str,
        typer.Option(
            "--transport",
            "-t",
            help="Transport mode for MCP server",
        ),
    ] = "stdio",
    http_host: Annotated[
        str,
        typer.Option(
            "--http-host",
            help="HTTP server host (for http/streamable_http mode)",
        ),
    ] = "127.0.0.1",
    http_port: Annotated[
        int,
        typer.Option(
            "--http-port",
            "-p",
            help="HTTP server port (for http/streamable_http mode)",
        ),
    ] = 8000,
    http_path: Annotated[
        str,
        typer.Option(
            "--http-path",
            help="HTTP endpoint path (for http/streamable_http mode)",
        ),
    ] = "/mcp",
) -> None:
    """Start the MCP server with specified transport mode.

    Supported transport modes:
    - stdio: Standard I/O mode for local MCP compatibility (default)
    - http: HTTP mode for Remote MCP
    - streamable_http: Streamable HTTP transport for Remote MCP (recommended)

    Examples:
    - scryfall-mcp serve
    - scryfall-mcp serve --transport streamable_http --http-port 8080
    - scryfall-mcp serve -t http -p 3000
    """
    # Validate transport mode
    valid_modes = ["stdio", "http", "streamable_http"]
    if transport not in valid_modes:
        typer.echo(
            f"Error: Invalid transport mode '{transport}'. "
            f"Valid modes: {', '.join(valid_modes)}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Override settings with CLI arguments
    settings = get_settings()
    settings.transport_mode = transport
    settings.http_host = http_host
    settings.http_port = http_port
    settings.http_path = http_path

    # Display server info (to stderr in stdio mode to avoid interfering with JSON-RPC)
    if transport == "stdio":
        typer.echo("Starting Scryfall MCP Server in stdio mode...", err=True)
    else:
        typer.echo(
            f"Starting Scryfall MCP Server in {transport} mode on "
            f"{http_host}:{http_port}{http_path}..."
        )

    # Run server
    server = ScryfallMCPServer()
    try:
        asyncio.run(server.run(transport_mode=transport))
    except KeyboardInterrupt:
        typer.echo("\nServer stopped.")
    except Exception as e:
        typer.echo(f"Server error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def setup() -> None:
    """Run configuration setup wizard.

    This interactive wizard will guide you through setting up your Scryfall MCP
    server configuration, including User-Agent and other important settings.
    """
    run_setup_wizard()


@app.command()
def config() -> None:
    """Show current configuration.

    Displays the current configuration file location and settings,
    including the configured User-Agent.
    """
    config_file = get_config_file()
    if config_file.exists():
        typer.echo(f"Configuration file: {config_file}")
        with config_file.open() as f:
            config_data = json.load(f)
        user_agent = config_data.get("user_agent", "Not configured")
        typer.echo(f"User-Agent: {user_agent}")
    else:
        typer.echo(
            "No configuration found. Run 'scryfall-mcp setup' first.",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def reset() -> None:
    """Reset configuration to defaults.

    This will delete your current configuration file. You will need to run
    'scryfall-mcp setup' again to reconfigure the server.
    """
    confirm = typer.confirm("Are you sure you want to reset the configuration?")
    if not confirm:
        typer.echo("Reset cancelled.")
        raise typer.Abort()

    reset_config()
    typer.echo("Configuration reset successfully.")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
