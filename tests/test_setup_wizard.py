"""Tests for the setup_wizard module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from scryfall_mcp.setup_wizard import (
    get_config_dir,
    get_config_file,
    get_user_agent,
    is_first_run,
    load_config,
    reset_config,
    run_setup_wizard,
    validate_contact_info,
)


class TestConfigPaths:
    """Test configuration path utilities."""

    def test_get_config_dir_macos(self) -> None:
        """Test get_config_dir on macOS."""
        with patch("scryfall_mcp.setup_wizard.sys.platform", "darwin"):
            with patch("scryfall_mcp.setup_wizard.Path.home", return_value=Path("/Users/test")):
                with patch("scryfall_mcp.setup_wizard.Path.mkdir"):
                    config_dir = get_config_dir()
                    assert config_dir == Path(
                        "/Users/test/Library/Application Support/scryfall-mcp"
                    )

    def test_get_config_dir_linux(self) -> None:
        """Test get_config_dir on Linux."""
        with patch("scryfall_mcp.setup_wizard.sys.platform", "linux"):
            with patch("scryfall_mcp.setup_wizard.Path.home", return_value=Path("/home/test")):
                with patch("scryfall_mcp.setup_wizard.Path.mkdir"):
                    config_dir = get_config_dir()
                    assert config_dir == Path("/home/test/.config/scryfall-mcp")

    def test_get_config_dir_windows(self) -> None:
        """Test get_config_dir on Windows."""
        with patch("scryfall_mcp.setup_wizard.sys.platform", "win32"):
            with patch("scryfall_mcp.setup_wizard.Path.home", return_value=Path("C:/Users/test")):
                with patch("scryfall_mcp.setup_wizard.Path.mkdir"):
                    config_dir = get_config_dir()
                    assert config_dir == Path("C:/Users/test/AppData/Local/scryfall-mcp")

    def test_get_config_file(self) -> None:
        """Test get_config_file returns correct path."""
        with patch("scryfall_mcp.setup_wizard.get_config_dir") as mock_dir:
            mock_dir.return_value = Path("/test/dir")
            config_file = get_config_file()
            assert config_file == Path("/test/dir/config.json")


class TestIsFirstRun:
    """Test first run detection."""

    def test_is_first_run_no_config(self) -> None:
        """Test is_first_run when config doesn't exist."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            assert is_first_run() is True

    def test_is_first_run_with_config(self) -> None:
        """Test is_first_run when config exists."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            assert is_first_run() is False


class TestValidateContactInfo:
    """Test contact information validation."""

    def test_validate_email_valid(self) -> None:
        """Test valid email addresses."""
        assert validate_contact_info("user@example.com") is True
        assert validate_contact_info("test.user@domain.co.uk") is True

    def test_validate_email_invalid(self) -> None:
        """Test invalid email addresses."""
        assert validate_contact_info("notanemail") is False
        assert validate_contact_info("@example.com") is False
        assert validate_contact_info("user@") is False

    def test_validate_https_url_valid(self) -> None:
        """Test valid HTTPS URLs."""
        assert validate_contact_info("https://github.com/user/repo") is True
        assert validate_contact_info("https://example.com") is True

    def test_validate_http_url_rejected(self) -> None:
        """Test that HTTP URLs are rejected (HTTPS only)."""
        assert validate_contact_info("http://github.com/user/repo") is False

    def test_validate_bare_domain_rejected(self) -> None:
        """Test that bare domains are rejected."""
        assert validate_contact_info("github.com/user/repo") is False
        assert validate_contact_info("example.com") is False

    def test_validate_empty_string(self) -> None:
        """Test empty strings are rejected."""
        assert validate_contact_info("") is False
        assert validate_contact_info("   ") is False


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_success(self) -> None:
        """Test successful config loading."""
        config_data = {"user_agent": "Test-Agent/1.0", "contact": "test@example.com"}
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.open = mock_open(read_data=json.dumps(config_data))

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            config = load_config()
            assert config == config_data

    def test_load_config_file_not_found(self) -> None:
        """Test config loading when file doesn't exist."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            config = load_config()
            assert config is None

    def test_load_config_json_error(self) -> None:
        """Test config loading with JSON decode error."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                config = load_config()
                assert config is None


class TestGetUserAgent:
    """Test User-Agent retrieval."""

    def test_get_user_agent_from_config(self) -> None:
        """Test getting User-Agent from existing config."""
        config_data = {
            "user_agent": "Scryfall-MCP/1.0 (test@example.com)",
            "contact": "test@example.com",
        }

        with patch("scryfall_mcp.setup_wizard.load_config", return_value=config_data):
            user_agent = get_user_agent()
            assert user_agent == "Scryfall-MCP/1.0 (test@example.com)"

    def test_get_user_agent_run_wizard_interactive(self) -> None:
        """Test running wizard in interactive mode."""
        with patch("scryfall_mcp.setup_wizard.load_config", return_value=None):
            with patch("sys.stdin.isatty", return_value=True):
                with patch("sys.stdout.isatty", return_value=True):
                    with patch("scryfall_mcp.setup_wizard.run_setup_wizard") as mock_wizard:
                        mock_wizard.return_value = {
                            "user_agent": "Test-Agent/1.0",
                            "contact": "test@example.com",
                        }
                        user_agent = get_user_agent()
                        assert user_agent == "Test-Agent/1.0"
                        mock_wizard.assert_called_once()

    def test_get_user_agent_non_interactive(self) -> None:
        """Test get_user_agent without config runs wizard."""
        with patch("scryfall_mcp.setup_wizard.load_config", return_value=None):
            with patch("scryfall_mcp.setup_wizard.run_setup_wizard") as mock_wizard:
                mock_wizard.return_value = {
                    "user_agent": "Test-Agent/1.0",
                    "contact": "test@example.com",
                }
                user_agent = get_user_agent()
                assert user_agent == "Test-Agent/1.0"
                mock_wizard.assert_called_once()


class TestResetConfig:
    """Test configuration reset."""

    def test_reset_config_file_exists(self, capsys) -> None:
        """Test resetting existing config."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            reset_config()
            mock_file.unlink.assert_called_once()

        captured = capsys.readouterr()
        assert "Configuration reset" in captured.out

    def test_reset_config_file_not_exists(self) -> None:
        """Test resetting when no config exists."""
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            reset_config()
            # Should not try to unlink non-existent file
            mock_file.unlink.assert_not_called()


class TestRunSetupWizard:
    """Test the interactive setup wizard."""

    def test_run_setup_wizard_email(self, capsys) -> None:
        """Test setup wizard with email input."""
        mock_file = MagicMock(spec=Path)

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            with patch("builtins.input", return_value="user@example.com"):
                with patch("builtins.open", mock_open()):
                    config = run_setup_wizard()

                    assert config["contact"] == "user@example.com"
                    assert "user@example.com" in config["user_agent"]

        captured = capsys.readouterr()
        assert "First Time Setup" in captured.out
        assert "Setup complete" in captured.out

    def test_run_setup_wizard_https_url(self) -> None:
        """Test setup wizard with HTTPS URL input."""
        mock_file = MagicMock(spec=Path)

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            with patch("builtins.input", return_value="https://github.com/user/repo"):
                with patch("builtins.open", mock_open()):
                    config = run_setup_wizard()

                    assert config["contact"] == "https://github.com/user/repo"
                    assert "https://github.com/user/repo" in config["user_agent"]

    def test_run_setup_wizard_invalid_then_valid(self, capsys) -> None:
        """Test setup wizard with invalid input followed by valid input."""
        mock_file = MagicMock(spec=Path)

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            # First return invalid, then valid
            with patch(
                "builtins.input", side_effect=["invalid", "user@example.com"]
            ):
                with patch("builtins.open", mock_open()):
                    config = run_setup_wizard()

                    assert config["contact"] == "user@example.com"

        captured = capsys.readouterr()
        assert "Invalid format" in captured.out

    def test_run_setup_wizard_empty_then_valid(self, capsys) -> None:
        """Test setup wizard with empty input followed by valid input."""
        mock_file = MagicMock(spec=Path)

        with patch("scryfall_mcp.setup_wizard.get_config_file", return_value=mock_file):
            # First return empty, then valid
            with patch("builtins.input", side_effect=["", "user@example.com"]):
                with patch("builtins.open", mock_open()):
                    config = run_setup_wizard()

                    assert config["contact"] == "user@example.com"

        captured = capsys.readouterr()
        assert "Contact information is required" in captured.out
