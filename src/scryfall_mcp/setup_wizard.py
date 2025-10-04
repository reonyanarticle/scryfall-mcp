"""Interactive setup wizard for first-time configuration.

This module provides an interactive setup wizard that runs on first launch
to collect required configuration like User-Agent contact information.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get the configuration directory path.

    Returns
    -------
    Path
        Path to configuration directory
    """
    # Use XDG Base Directory specification
    if sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "scryfall-mcp"
    elif sys.platform == "win32":
        config_dir = Path.home() / "AppData" / "Local" / "scryfall-mcp"
    else:  # Linux and other Unix-like systems
        xdg_config_home = Path.home() / ".config"
        config_dir = xdg_config_home / "scryfall-mcp"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """Get the configuration file path.

    Returns
    -------
    Path
        Path to configuration file
    """
    return get_config_dir() / "config.json"


def is_first_run() -> bool:
    """Check if this is the first run (no config file exists).

    Returns
    -------
    bool
        True if this is the first run, False otherwise
    """
    return not get_config_file().exists()


def validate_contact_info(contact: str) -> bool:
    """Validate contact information.

    Parameters
    ----------
    contact : str
        Contact information (email or URL)

    Returns
    -------
    bool
        True if valid, False otherwise

    Notes
    -----
    URLs must start with https:// for proper User-Agent compliance and security.
    HTTP URLs and bare domain names like "github.com/user" are not accepted.
    """
    contact = contact.strip()

    # Check if it's an email
    if "@" in contact:
        # Basic email validation
        parts = contact.split("@")
        if len(parts) == 2 and all(parts) and "." in parts[1]:
            return True

    # Check if it's a full HTTPS URL (required for security compliance)
    if contact.startswith("https://"):
        return True

    return False


def run_setup_wizard() -> dict[str, str]:
    """Run the interactive setup wizard.

    Returns
    -------
    dict[str, str]
        Configuration dictionary with user settings
    """
    print("\n" + "=" * 70)
    print("🎴 Scryfall MCP Server - First Time Setup")
    print("=" * 70)
    print(
        "\nWelcome! Before using this server, we need to configure your User-Agent.\n"
    )
    print("Scryfall requires all API clients to provide contact information in the")
    print("User-Agent header. This helps them reach out if there are issues with")
    print("your requests.\n")

    contact = ""
    while not contact or not validate_contact_info(contact):
        print("Please provide your contact information:")
        print("  • Your email address (e.g., yourname@example.com)")
        print("  • Your repository URL (e.g., https://github.com/username/repo)")
        print("  • Or any other URL where you can be reached (must include https://)\n")

        contact = input("Contact info: ").strip()

        if not contact:
            print("❌ Contact information is required.\n")
            continue

        if not validate_contact_info(contact):
            print("❌ Invalid format. Please provide a valid email or URL.\n")
            continue

    # Build User-Agent string
    user_agent = f"Scryfall-MCP-Server/0.1.0 ({contact})"

    print(f"\n✅ User-Agent configured: {user_agent}")
    print("\nSaving configuration...")

    config = {"user_agent": user_agent, "contact": contact}

    # Save configuration
    config_file = get_config_file()
    with config_file.open("w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Configuration saved to: {config_file}")
    print("\n" + "=" * 70)
    print("Setup complete! Starting Scryfall MCP Server...\n")

    return config


def load_config() -> dict[str, str] | None:
    """Load configuration from file.

    Returns
    -------
    dict[str, str] | None
        Configuration dictionary, or None if not found
    """
    config_file = get_config_file()

    if not config_file.exists():
        return None

    try:
        with config_file.open() as f:
            config_data: dict[str, str] = json.load(f)
            return config_data
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None


def get_user_agent() -> str:
    """Get the configured User-Agent string.

    Runs setup wizard if this is the first run.

    Returns
    -------
    str
        Configured User-Agent string
    """
    config = load_config()

    if config is None:
        # First run - run setup wizard
        config = run_setup_wizard()

    return config.get("user_agent", "Scryfall-MCP-Server/0.1.0 (unconfigured)")


def reset_config() -> None:
    """Reset configuration (delete config file).

    This will trigger the setup wizard on next run.
    """
    config_file = get_config_file()
    if config_file.exists():
        config_file.unlink()
        print("Configuration reset. Setup wizard will run on next start.")
