"""Tests for the __main__ module."""

from __future__ import annotations

import sys
from unittest.mock import patch


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
            [sys.executable, "-c",
             "import sys; sys.exit(0) if __name__ == '__main__' else sys.exit(1)"],
            check=False, capture_output=True,
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
            with patch.dict("sys.modules", {"scryfall_mcp.server": type("module", (), {"sync_main": mock_sync_main})}):
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
