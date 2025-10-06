#!/usr/bin/env python3
"""Test MCP tool calls."""

import json
import subprocess


def send_request(proc, request):
    """Send a JSON-RPC request and get response."""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    return json.loads(response_line) if response_line else None


def test_tool_call():
    """Test calling MCP tools."""
    print("Testing MCP tool calls...")
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
        print("✓ Initialized\n")

        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()

        # Test 1: Search for Lightning Bolt
        print("Test 1: Searching for 'Lightning Bolt'...")
        search_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_cards",
                "arguments": {
                    "query": "Lightning Bolt",
                    "language": "en",
                    "max_results": 3,
                },
            },
        }
        response = send_request(proc, search_request)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                print(f"  ✓ Success! Received {len(content)} content items")
                for item in content[:1]:  # Show first item
                    if "text" in item:
                        print(f"  Preview: {item['text'][:200]}...")
            else:
                print("  ✗ No content in response")
        else:
            print(f"  ✗ Error: {response}")
        print()

        # Test 2: Japanese search
        print("Test 2: Japanese search '稲妻'...")
        search_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_cards",
                "arguments": {"query": "稲妻", "language": "ja", "max_results": 3},
            },
        }
        response = send_request(proc, search_request)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                print(f"  ✓ Success! Received {len(content)} content items")
                for item in content[:1]:
                    if "text" in item:
                        print(f"  Preview: {item['text'][:200]}...")
            else:
                print("  ✗ No content in response")
        else:
            print(f"  ✗ Error: {response}")
        print()

        # Test 3: Autocomplete
        print("Test 3: Autocomplete 'Light'...")
        autocomplete_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "autocomplete_card_names",
                "arguments": {"query": "Light", "language": "en"},
            },
        }
        response = send_request(proc, autocomplete_request)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                print(f"  ✓ Success! Received {len(content)} content items")
                for item in content[:1]:
                    if "text" in item:
                        print(f"  Preview: {item['text'][:150]}...")
            else:
                print("  ✗ No content in response")
        else:
            print(f"  ✗ Error: {response}")
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        proc.terminate()
        proc.wait()

    print("=" * 80)
    print("All tool call tests completed!")


if __name__ == "__main__":
    test_tool_call()
