#!/usr/bin/env python3
"""Test MCP server tools directly."""

import asyncio
import sys
from scryfall_mcp.server import ScryfallMCPServer


async def test_tools():
    """Test MCP server tools."""
    server = ScryfallMCPServer()

    print("=" * 80)
    print("Testing Scryfall MCP Server")
    print("=" * 80)
    print()

    # Test 1: Search for Lightning Bolt
    print("Test 1: Searching for 'Lightning Bolt'...")
    try:
        result = await server._search_cards_async("Lightning Bolt", language="en", max_results=5)
        print(f"✓ Success: {len(result)} characters returned")
        print(f"Preview: {result[:200]}...")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Test 2: Japanese search
    print("Test 2: Japanese search '稲妻'...")
    try:
        result = await server._search_cards_async("稲妻", language="ja", max_results=5)
        print(f"✓ Success: {len(result)} characters returned")
        print(f"Preview: {result[:200]}...")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Test 3: Autocomplete
    print("Test 3: Autocomplete 'Light'...")
    try:
        result = await server._autocomplete_async("Light", language="en")
        print(f"✓ Success: {len(result)} characters returned")
        print(f"Preview: {result[:200]}...")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Test 4: Natural language query (Japanese)
    print("Test 4: Natural language query '赤いクリーチャー'...")
    try:
        result = await server._search_cards_async("赤いクリーチャー", language="ja", max_results=5)
        print(f"✓ Success: {len(result)} characters returned")
        print(f"Preview: {result[:200]}...")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    print("=" * 80)
    print("Tests completed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_tools())
