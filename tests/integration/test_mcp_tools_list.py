#!/usr/bin/env python3
"""Test MCP tools list."""

import json
import subprocess
import sys


def send_request(proc, request):
    """Send a JSON-RPC request and get response."""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    return json.loads(response_line) if response_line else None


def test_tools_list():
    """Test listing available tools."""
    print("Testing MCP tools list...")
    print("=" * 80)

    # Start the server
    proc = subprocess.Popen(
        ["uv", "run", "scryfall-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        response = send_request(proc, init_request)
        print("✓ Initialized")

        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()

        # 3. List tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        response = send_request(proc, list_tools_request)

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"\n✓ Found {len(tools)} tools:")
            print()
            for tool in tools:
                print(f"  • {tool['name']}")
                print(f"    Description: {tool.get('description', 'N/A')}")
                print(
                    f"    Input schema: {json.dumps(tool.get('inputSchema', {}), indent=6)}"
                )
                print()
        else:
            print(f"\n✗ Unexpected response: {response}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        proc.terminate()
        proc.wait()

    print("=" * 80)


if __name__ == "__main__":
    test_tools_list()
