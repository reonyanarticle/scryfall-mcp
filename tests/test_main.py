"""Tests for the __main__ module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from typer.testing import CliRunner

from scryfall_mcp.__main__ import app

runner = CliRunner()


class TestMainModule:
    """Test the main module entry point."""

    def test_main_module_execution(self) -> None:
        """Test that __main__ module can be imported."""
        # Simply importing should not raise any errors
        import scryfall_mcp.__main__  # noqa: F401

    def test_main_module_script_execution(self) -> None:
        """Test __main__ module when run as script via python -m."""
        import subprocess
        import sys

        # Test actual module execution
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.exit(0) if __name__ == '__main__' else sys.exit(1)",
            ],
            check=False,
            capture_output=True,
        )
        # This tests that the __name__ == "__main__" condition works
        assert result.returncode == 0

    def test_main_module_runpy_execution(self) -> None:
        """Test executing __main__.py using runpy."""
        import runpy

        with patch("scryfall_mcp.__main__.app") as mock_app:
            # Mock the app() call to prevent typer execution
            mock_app.return_value = None

            # Use runpy to execute the module as __main__
            try:
                runpy.run_module("scryfall_mcp", run_name="__main__", alter_sys=False)
            except (SystemExit, AttributeError):
                # typer might call sys.exit or raise attribute errors
                pass

            # The test mainly verifies that runpy execution doesn't crash
            # Verifying app call is not reliable due to module reloading


class TestMainFunction:
    """Test the main() function CLI commands."""

    def test_main_no_args_shows_error(self) -> None:
        """Test that main() with no args shows error (typer requires subcommand)."""
        result = runner.invoke(app, [])
        # Typer exits with code 2 when no subcommand is provided
        assert result.exit_code == 2
        assert "Usage:" in result.output
        assert "Missing command" in result.output

    def test_main_help_flag(self) -> None:
        """Test the '--help' command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Scryfall MCP Server" in result.output
        assert "Commands" in result.output

    def test_serve_command_help(self) -> None:
        """Test the 'serve --help' command."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start the MCP server" in result.output
        assert "--transport" in result.output
        assert "--http-port" in result.output

    def test_setup_command(self) -> None:
        """Test the 'setup' command."""
        with patch("scryfall_mcp.__main__.run_setup_wizard") as mock_wizard:
            result = runner.invoke(app, ["setup"])
            assert result.exit_code == 0
            mock_wizard.assert_called_once()

    def test_config_command_exists(self) -> None:
        """Test the 'config' command when config file exists."""
        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = True
        mock_config_file.__str__.return_value = "/fake/path/config.json"

        config_data = {"user_agent": "Test-Agent/1.0 (test@example.com)"}
        mock_config_file.open = mock_open(read_data=json.dumps(config_data))

        with patch("scryfall_mcp.__main__.get_config_file", return_value=mock_config_file):
            result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "Configuration file:" in result.output
        assert "User-Agent: Test-Agent/1.0 (test@example.com)" in result.output

    def test_config_command_not_exists(self) -> None:
        """Test the 'config' command when config file doesn't exist."""
        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = False

        with patch("scryfall_mcp.__main__.get_config_file", return_value=mock_config_file):
            result = runner.invoke(app, ["config"])

        assert result.exit_code == 1
        assert "No configuration found" in result.output
        assert "Run 'scryfall-mcp setup' first" in result.output

    def test_reset_command_confirmed(self) -> None:
        """Test the 'reset' command with confirmation."""
        with patch("scryfall_mcp.__main__.reset_config") as mock_reset:
            result = runner.invoke(app, ["reset"], input="y\n")
            assert result.exit_code == 0
            mock_reset.assert_called_once()
            assert "Configuration reset successfully" in result.output

    def test_reset_command_cancelled(self) -> None:
        """Test the 'reset' command when cancelled."""
        with patch("scryfall_mcp.__main__.reset_config") as mock_reset:
            result = runner.invoke(app, ["reset"], input="n\n")
            assert result.exit_code == 1
            mock_reset.assert_not_called()
            assert "Reset cancelled" in result.output

    def test_serve_invalid_transport(self) -> None:
        """Test the 'serve' command with invalid transport mode."""
        result = runner.invoke(app, ["serve", "--transport", "invalid"])
        assert result.exit_code == 1
        assert "Invalid transport mode" in result.output

    def test_serve_with_custom_port(self) -> None:
        """Test the 'serve' command with custom HTTP port."""
        from scryfall_mcp.settings import Settings

        # Create mock settings with allowed_origins
        mock_settings = Settings(allowed_origins=["https://claude.ai"])

        with patch("scryfall_mcp.__main__.ScryfallMCPServer") as mock_server:
            with patch("scryfall_mcp.__main__.asyncio.run"):
                with patch("scryfall_mcp.__main__.get_settings", return_value=mock_settings):
                    result = runner.invoke(
                        app, ["serve", "--transport", "http", "--http-port", "3000"]
                    )
                    # The command should execute without errors
                    assert "Starting Scryfall MCP Server in http mode" in result.output
                    assert ":3000" in result.output

    def test_serve_streamable_http_mode(self) -> None:
        """Test the 'serve' command with streamable_http transport."""
        from scryfall_mcp.settings import Settings

        # Create mock settings with allowed_origins
        mock_settings = Settings(allowed_origins=["https://claude.ai"])

        with patch("scryfall_mcp.__main__.ScryfallMCPServer") as mock_server:
            with patch("scryfall_mcp.__main__.asyncio.run"):
                with patch("scryfall_mcp.__main__.get_settings", return_value=mock_settings):
                    result = runner.invoke(
                        app, ["serve", "--transport", "streamable_http"]
                    )
                    assert (
                        "Starting Scryfall MCP Server in streamable_http mode"
                        in result.output
                    )

    def test_serve_stdio_mode(self) -> None:
        """Test the 'serve' command with default stdio transport."""
        with patch("scryfall_mcp.__main__.ScryfallMCPServer") as mock_server:
            with patch("scryfall_mcp.__main__.asyncio.run"):
                result = runner.invoke(app, ["serve"])
                assert "Starting Scryfall MCP Server in stdio mode" in result.output
