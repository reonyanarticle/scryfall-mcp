"""Entry point for running scryfall-mcp as a module."""

from .server import sync_main

if __name__ == "__main__":
    sync_main()
