#!/usr/bin/env python3
"""Test direct MCP communication with the server."""

import asyncio
import json
import subprocess
import sys

async def test_mcp_communication():
    """Test direct MCP JSON-RPC communication."""

    # Start the server process
    process = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "scryfall_mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Users/tomoya/scryfall-mcp"
    )

    # Send initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    print("Sending initialize request...")
    process.stdin.write(json.dumps(initialize_request).encode() + b'\n')
    await process.stdin.drain()

    # Read response
    try:
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        if response_line:
            response = json.loads(response_line.decode())
            print(f"Initialize response: {json.dumps(response, indent=2)}")
        else:
            print("No response received")
    except asyncio.TimeoutError:
        print("Timeout waiting for initialize response")

    # Send initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }

    print("\nSending initialized notification...")
    process.stdin.write(json.dumps(initialized_notification).encode() + b'\n')
    await process.stdin.drain()

    # Wait a bit for the server to process the notification
    await asyncio.sleep(0.1)

    # Send tools/list request
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    print("\nSending tools/list request...")
    process.stdin.write(json.dumps(tools_request).encode() + b'\n')
    await process.stdin.drain()

    # Read response
    try:
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        if response_line:
            response = json.loads(response_line.decode())
            print(f"Tools/list response: {json.dumps(response, indent=2)}")
        else:
            print("No response received")
    except asyncio.TimeoutError:
        print("Timeout waiting for tools/list response")

    # Send tools/call request
    tools_call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "autocomplete_card_names",
            "arguments": {
                "query": "Light"
            }
        }
    }

    print("\nSending tools/call request...")
    process.stdin.write(json.dumps(tools_call_request).encode() + b'\n')
    await process.stdin.drain()

    # Read response
    try:
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
        if response_line:
            response = json.loads(response_line.decode())
            print(f"Tools/call response: {json.dumps(response, indent=2)}")
        else:
            print("No response received")
    except asyncio.TimeoutError:
        print("Timeout waiting for tools/call response")

    # Terminate process
    process.terminate()
    await process.wait()

    # Check stderr for any error messages
    stderr_output = await process.stderr.read()
    if stderr_output:
        print(f"\nServer stderr output:\n{stderr_output.decode()}")

if __name__ == "__main__":
    asyncio.run(test_mcp_communication())