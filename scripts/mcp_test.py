#!/usr/bin/env python3
"""Automated MCP server testing script using JSON-RPC protocol."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class MCPTestResult:
    """Represents the result of an MCP test."""

    def __init__(
        self, name: str, success: bool, message: str, data: dict[str, Any] | None = None
    ):
        self.name = name
        self.success = success
        self.message = message
        self.data = data or {}

    def __str__(self) -> str:
        status = "✅ PASS" if self.success else "❌ FAIL"
        return f"{status} {self.name}: {self.message}"


class MCPTester:
    """Test runner for MCP servers using JSON-RPC protocol."""

    def __init__(self, server_command: list[str], working_dir: str | None = None):
        self.server_command = server_command
        self.working_dir = working_dir or "."
        self.process: asyncio.subprocess.Process | None = None
        self.results: list[MCPTestResult] = []

    async def start_server(self) -> bool:
        """Start the MCP server process."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_dir,
            )
            return True
        except Exception as e:
            self.add_result("server_start", False, f"Failed to start server: {e}")
            return False

    async def stop_server(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def send_request(
        self, request: dict[str, Any], timeout: float = 5.0
    ) -> dict[str, Any] | None:
        """Send a JSON-RPC request to the server."""
        if not self.process or not self.process.stdin:
            print("❌ Process or stdin not available")
            return None

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            print(f"📤 Sending: {request_json.strip()}")
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Read response
            print(f"⏳ Waiting for response (timeout: {timeout}s)...")
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=timeout,
            )

            if response_line:
                response_text = response_line.decode().strip()
                print(f"📥 Received: {response_text}")
                return json.loads(response_text)
            print("❌ Empty response received")
            return None

        except TimeoutError:
            print("⏰ Timeout waiting for response")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    def add_result(
        self, name: str, success: bool, message: str, data: dict[str, Any] | None = None
    ) -> None:
        """Add a test result."""
        self.results.append(MCPTestResult(name, success, message, data))

    async def test_initialize(self) -> bool:
        """Test server initialization."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {},
                },
                "clientInfo": {
                    "name": "mcp-test-client",
                    "version": "1.0.0",
                },
            },
        }

        response = await self.send_request(request)

        if not response:
            self.add_result("initialize", False, "No response received")
            return False

        if response.get("error"):
            self.add_result("initialize", False, f"Error: {response['error']}")
            return False

        if "result" not in response:
            self.add_result("initialize", False, "Invalid response format")
            return False

        result = response["result"]
        server_info = result.get("serverInfo", {})
        capabilities = result.get("capabilities", {})

        self.add_result(
            "initialize",
            True,
            f"Server: {server_info.get('name', 'unknown')} v{server_info.get('version', 'unknown')}",
            {"serverInfo": server_info, "capabilities": capabilities},
        )
        return True

    async def send_initialized(self) -> None:
        """Send initialized notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        await self.send_message(notification)
        self.add_result("initialized", True, "Initialized notification sent")

    async def test_tools_list(self) -> bool:
        """Test tools/list endpoint."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        response = await self.send_request(request)

        if not response:
            self.add_result("tools_list", False, "No response received")
            return False

        if response.get("error"):
            self.add_result("tools_list", False, f"Error: {response['error']}")
            return False

        if "result" not in response:
            self.add_result("tools_list", False, "Invalid response format")
            return False

        tools = response["result"].get("tools", [])
        tool_names = [tool.get("name") for tool in tools]

        self.add_result(
            "tools_list",
            True,
            f"Found {len(tools)} tools: {', '.join(tool_names)}",
            {"tools": tools},
        )
        return True

    async def test_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Test calling a specific tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await self.send_request(
            request, timeout=10.0
        )  # Longer timeout for API calls

        if not response:
            self.add_result(f"tool_call_{tool_name}", False, "No response received")
            return False

        if response.get("error"):
            self.add_result(
                f"tool_call_{tool_name}", False, f"Error: {response['error']}"
            )
            return False

        if "result" not in response:
            self.add_result(f"tool_call_{tool_name}", False, "Invalid response format")
            return False

        result = response["result"]
        is_error = result.get("isError", False)

        if is_error:
            content = result.get("content", [])
            error_msg = (
                content[0].get("text", "Unknown error") if content else "Unknown error"
            )
            self.add_result(f"tool_call_{tool_name}", False, f"Tool error: {error_msg}")
            return False

        # Extract result content
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            text_result = content[0].get("text", "")[:100]  # First 100 chars
            self.add_result(
                f"tool_call_{tool_name}",
                True,
                f"Success: {text_result}...",
                {"result": result},
            )
            return True
        self.add_result(f"tool_call_{tool_name}", False, "Invalid result format")
        return False

    async def run_all_tests(self) -> bool:
        """Run all MCP tests."""
        print("🚀 Starting MCP Server Tests...")
        print(f"Server command: {' '.join(self.server_command)}")
        print(f"Working directory: {self.working_dir}")
        print("-" * 60)

        try:
            # Start server
            if not await self.start_server():
                return False

            # Wait for server startup
            await asyncio.sleep(1.0)

            # Test initialization
            if not await self.test_initialize():
                return False

            # Send initialized notification
            await self.send_initialized()

            # Test tools list
            if not await self.test_tools_list():
                return False

            # Test tool calls
            await self.test_tool_call("autocomplete_card_names", {"query": "Lightning"})
            await self.test_tool_call(
                "search_cards", {"query": "Lightning Bolt", "max_results": 2}
            )

            return True

        finally:
            await self.stop_server()

    def print_results(self) -> bool:
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("🧪 MCP Protocol Test Results")
        print("=" * 60)

        passed = 0
        total = len(self.results)

        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status}: {result.name} - {result.message}")
            if result.data:
                for key, value in result.data.items():
                    print(f"    {key}: {value}")
            if result.success:
                passed += 1

        print("=" * 60)
        print(f"📊 Summary: {passed}/{total} tests passed")
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")

        if passed == total:
            print("🎉 All tests passed! MCP server is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above.")
            return False


async def main() -> None:
    """Main test runner."""
    # Test configuration
    working_dir = Path(__file__).parent.parent

    tester = MCPTester(working_dir)
    success = await tester.run_all_tests()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
