#!/usr/bin/env python3
"""Test MCP protocol connection."""

import json
import subprocess
import sys


def test_mcp_connection():
    """Test MCP server can respond to protocol messages."""
    print("Testing MCP protocol connection...")
    print("=" * 80)

    # Start the server
    proc = subprocess.Popen(
        ["uv", "run", "scryfall-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Send initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    try:
        # Send request
        proc.stdin.write(json.dumps(initialize_request) + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        print(f"Response: {response_line}")

        if response_line:
            response = json.loads(response_line)
            print("\n✓ MCP server responded successfully!")
            print(
                f"Protocol version: {response.get('result', {}).get('protocolVersion', 'unknown')}"
            )
            print(
                f"Server capabilities: {json.dumps(response.get('result', {}).get('capabilities', {}), indent=2)}"
            )
            print(
                f"Server info: {json.dumps(response.get('result', {}).get('serverInfo', {}), indent=2)}"
            )
        else:
            print("\n✗ No response from server")

    except Exception as e:
        print(f"\n✗ Error: {e}")

    finally:
        proc.terminate()
        proc.wait()

    print("=" * 80)


if __name__ == "__main__":
    test_mcp_connection()
