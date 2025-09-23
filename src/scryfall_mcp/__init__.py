"""Scryfall MCP Server - Magic: The Gathering card information via MCP protocol.

This package provides a Model Context Protocol (MCP) server that connects
AI assistants to the Scryfall API for Magic: The Gathering card information,
with special support for Japanese language queries.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Scryfall MCP Server Team"
__description__ = "Magic: The Gathering card information via MCP protocol with Japanese support"

from .server import ScryfallMCPServer, main, sync_main

__all__ = [
    "ScryfallMCPServer",
    "__author__",
    "__description__",
    "__version__",
    "main",
    "sync_main",
]
