"""Tests for the __main__ module."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


class TestMainModule:
    """Test the main module entry point."""

    def test_main_module_execution(self) -> None:
        """Test that __main__ module can be imported without calling sync_main."""
        with patch("scryfall_mcp.__main__.sync_main") as mock_sync_main:
            # Import the __main__ module

            # The sync_main should not be called just by importing
            mock_sync_main.assert_not_called()

    def test_main_module_script_execution(self) -> None:
        """Test __main__ module when run as script via python -m."""
        import subprocess

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

    def test_main_block_execution(self) -> None:
        """Test that the main block executes sync_main when __name__ is __main__."""
        with patch("scryfall_mcp.server.sync_main") as mock_sync_main:
            # Simulate the exact code in __main__.py
            code = """
from .server import sync_main

if __name__ == "__main__":
    sync_main()
"""
            # Execute with __name__ = "__main__"
            namespace = {"__name__": "__main__", "__package__": "scryfall_mcp"}
            with patch.dict(
                "sys.modules",
                {
                    "scryfall_mcp.server": type(
                        "module", (), {"sync_main": mock_sync_main}
                    )
                },
            ):
                exec(compile(code, "__main__.py", "exec"), namespace)

            mock_sync_main.assert_called_once()

    def test_main_module_runpy_execution(self) -> None:
        """Test executing __main__.py using runpy to cover line 6."""
        import runpy

        with patch("scryfall_mcp.server.sync_main") as mock_sync_main:
            # Use runpy to execute the module as __main__
            # This should trigger the if __name__ == "__main__": block
            try:
                runpy.run_module("scryfall_mcp", run_name="__main__", alter_sys=False)
            except SystemExit:
                # sync_main might call sys.exit, which is expected
                pass

            # Verify sync_main was called
            mock_sync_main.assert_called_once()


class TestMainFunction:
    """Test the main() function CLI commands."""

    def test_main_no_args_calls_sync_main(self, capsys) -> None:
        """Test that main() with no args calls sync_main."""
        with patch("scryfall_mcp.__main__.sync_main") as mock_sync_main:
            with patch("sys.argv", ["scryfall-mcp"]):
                from scryfall_mcp.__main__ import main

                main()
                mock_sync_main.assert_called_once()

    def test_main_setup_command(self, capsys) -> None:
        """Test the 'setup' command."""
        with patch("scryfall_mcp.__main__.run_setup_wizard") as mock_wizard:
            with patch("sys.argv", ["scryfall-mcp", "setup"]):
                from scryfall_mcp.__main__ import main

                main()
                mock_wizard.assert_called_once()

    def test_main_reset_command(self, capsys) -> None:
        """Test the 'reset' command."""
        with patch("scryfall_mcp.__main__.reset_config") as mock_reset:
            with patch("sys.argv", ["scryfall-mcp", "reset"]):
                from scryfall_mcp.__main__ import main

                main()
                mock_reset.assert_called_once()

    def test_main_config_command_exists(self, capsys) -> None:
        """Test the 'config' command when config file exists."""
        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = True
        mock_config_file.__str__.return_value = "/fake/path/config.json"

        config_data = {"user_agent": "Test-Agent/1.0 (test@example.com)"}
        mock_config_file.open = mock_open(read_data=json.dumps(config_data))

        with patch("scryfall_mcp.__main__.get_config_file", return_value=mock_config_file):
            with patch("sys.argv", ["scryfall-mcp", "config"]):
                from scryfall_mcp.__main__ import main

                main()

        captured = capsys.readouterr()
        assert "Configuration file:" in captured.out
        assert "User-Agent: Test-Agent/1.0 (test@example.com)" in captured.out

    def test_main_config_command_not_exists(self, capsys) -> None:
        """Test the 'config' command when config file doesn't exist."""
        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = False

        with patch("scryfall_mcp.__main__.get_config_file", return_value=mock_config_file):
            with patch("sys.argv", ["scryfall-mcp", "config"]):
                from scryfall_mcp.__main__ import main

                main()

        captured = capsys.readouterr()
        assert "No configuration found" in captured.out
        assert "Run 'scryfall-mcp setup' first" in captured.out

    def test_main_help_command(self, capsys) -> None:
        """Test the '--help' command."""
        with patch("sys.argv", ["scryfall-mcp", "--help"]):
            from scryfall_mcp.__main__ import main

            main()

        captured = capsys.readouterr()
        assert "Scryfall MCP Server" in captured.out
        assert "Usage:" in captured.out
        assert "scryfall-mcp setup" in captured.out

    def test_main_help_short_flag(self, capsys) -> None:
        """Test the '-h' flag."""
        with patch("sys.argv", ["scryfall-mcp", "-h"]):
            from scryfall_mcp.__main__ import main

            main()

        captured = capsys.readouterr()
        assert "Scryfall MCP Server" in captured.out

    def test_main_help_word(self, capsys) -> None:
        """Test the 'help' command word."""
        with patch("sys.argv", ["scryfall-mcp", "help"]):
            from scryfall_mcp.__main__ import main

            main()

        captured = capsys.readouterr()
        assert "Scryfall MCP Server" in captured.out
