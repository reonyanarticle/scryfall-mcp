#!/usr/bin/env python3
"""Test MCP content structure validation."""

from __future__ import annotations

import json
import subprocess
import sys


def validate_mcp_content(content_items: list) -> tuple[bool, list[str]]:
    """Validate MCP content structure.

    Args:
        content_items: List of MCP content items to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if not isinstance(content_items, list):
        return False, [f"Content must be a list, got {type(content_items)}"]

    for i, item in enumerate(content_items):
        if not isinstance(item, dict):
            errors.append(f"Item {i}: Not a dict, got {type(item)}")
            continue

        item_type = item.get("type")
        if not item_type:
            errors.append(f"Item {i}: Missing 'type' field")
            continue

        if item_type == "text":
            if "text" not in item:
                errors.append(f"Item {i}: TextContent missing 'text' field")
            elif not isinstance(item["text"], str):
                errors.append(
                    f"Item {i}: TextContent 'text' must be string, got {type(item['text'])}"
                )
        elif item_type == "image":
            if "data" not in item:
                errors.append(f"Item {i}: ImageContent missing 'data' field")
            if "mimeType" not in item:
                errors.append(f"Item {i}: ImageContent missing 'mimeType' field")
        elif item_type == "resource":
            if "resource" not in item:
                errors.append(f"Item {i}: EmbeddedResource missing 'resource' field")
        else:
            errors.append(f"Item {i}: Unknown content type '{item_type}'")

    return len(errors) == 0, errors


def send_request(proc: subprocess.Popen, request: dict) -> dict | None:
    """Send a JSON-RPC request and get response.

    Skips notification messages and waits for the actual response.
    """
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()

    # Read responses until we get one with matching ID or result
    while True:
        response_line = proc.stdout.readline()
        if not response_line:
            return None

        response = json.loads(response_line)

        # Skip notifications (messages without 'id')
        if "method" in response and response.get("method") == "notifications/message":
            continue

        # Skip notifications/progress
        if "method" in response and "notifications" in response.get("method", ""):
            continue

        # Return actual response (has 'id' or 'result')
        return response


def test_content_validation() -> None:
    """Test MCP content structure validation."""
    print("Testing MCP Content Structure Validation...")
    print("=" * 80)

    # Start server
    proc = subprocess.Popen(
        ["uv", "run", "scryfall-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Initialize
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

        # Send initialized notification (required by MCP 2024-11-05)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()
        print("✓ Sent initialized notification\n")

        # Test 1: search_cards content validation
        print("Test 1: Validating search_cards content structure...")
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
                    "include_images": False,
                },
            },
        }

        response = send_request(proc, search_request)
        if response and "result" in response:
            content = response["result"].get("content", [])
            is_valid, errors = validate_mcp_content(content)

            if is_valid:
                print(f"  ✓ All {len(content)} content items are valid MCP structures")
                # Show structure of first item
                if content:
                    first_item = content[0]
                    print(f"  First item type: {first_item.get('type')}")
                    if first_item.get("type") == "text":
                        print(f"  Text preview: {first_item.get('text', '')[:100]}...")
            else:
                print("  ✗ Content validation failed:")
                for error in errors:
                    print(f"    - {error}")
                sys.exit(1)
        else:
            print(f"  ✗ No valid response: {response}")
            sys.exit(1)

        print()

        # Test 2: autocomplete_card_names content validation
        print("Test 2: Validating autocomplete_card_names content structure...")
        autocomplete_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "autocomplete_card_names",
                "arguments": {"query": "Light", "language": "en"},
            },
        }

        response = send_request(proc, autocomplete_request)
        if response and "result" in response:
            content = response["result"].get("content", [])
            is_valid, errors = validate_mcp_content(content)

            if is_valid:
                print(f"  ✓ All {len(content)} content items are valid MCP structures")
                if content:
                    first_item = content[0]
                    print(f"  First item type: {first_item.get('type')}")
            else:
                print("  ✗ Content validation failed:")
                for error in errors:
                    print(f"    - {error}")
                sys.exit(1)
        else:
            print(f"  ✗ No valid response: {response}")
            sys.exit(1)

        print()

        # Test 3: Error response validation
        print("Test 3: Validating error response content structure...")
        error_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_cards",
                "arguments": {"query": "!!!invalid_query!!!", "max_results": 500},  # Invalid query
            },
        }

        response = send_request(proc, error_request)
        if response:
            if "error" in response:
                print(f"  ✓ Error handled as JSON-RPC error: {response['error'].get('message', '')[:100]}...")
            elif "result" in response:
                content = response["result"].get("content", [])
                is_valid, errors = validate_mcp_content(content)

                if is_valid:
                    print(f"  ✓ Error returned as valid MCP content ({len(content)} items)")
                    # Check if it's an error message
                    if content and content[0].get("type") == "text":
                        text = content[0].get("text", "")
                        if "error" in text.lower() or "エラー" in text:
                            print(f"  ✓ Error message in content: {text[:100]}...")
                else:
                    print("  ✗ Error content validation failed:")
                    for error in errors:
                        print(f"    - {error}")
                    sys.exit(1)

        print("\n" + "=" * 80)
        print("✓ All MCP content structure validation tests passed!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_content_validation()
