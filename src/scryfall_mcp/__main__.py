"""Main module entry point for Scryfall MCP Server.

Provides CLI commands for running the server and managing configuration.
"""

import sys

from .server import sync_main
from .setup_wizard import get_config_file, reset_config, run_setup_wizard


def main() -> None:
    """CLI entry point with command handling."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "setup":
            # Run setup wizard
            run_setup_wizard()
            return
        elif command == "reset":
            # Reset configuration
            reset_config()
            return
        elif command == "config":
            # Show current config location
            config_file = get_config_file()
            if config_file.exists():
                print(f"Configuration file: {config_file}")
                import json

                with config_file.open() as f:
                    config = json.load(f)
                print(f"User-Agent: {config.get('user_agent', 'Not configured')}")
            else:
                print("No configuration found. Run 'scryfall-mcp setup' first.")
            return
        elif command in ("--help", "-h", "help"):
            print("Scryfall MCP Server")
            print("\nUsage:")
            print("  scryfall-mcp           Start the MCP server")
            print("  scryfall-mcp setup     Run configuration setup wizard")
            print("  scryfall-mcp config    Show current configuration")
            print("  scryfall-mcp reset     Reset configuration")
            print("  scryfall-mcp --help    Show this help message")
            return

    # Default: start server
    sync_main()


if __name__ == "__main__":
    main()
