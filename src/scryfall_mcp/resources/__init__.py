"""Resource management for Scryfall MCP Server.

This module provides utilities for loading static resources like
setup guides and documentation.
"""

from __future__ import annotations

from pathlib import Path


def load_setup_guide(language: str = "ja") -> str:
    """Load setup guide text from resource file.

    Parameters
    ----------
    language : str, optional
        Language code for the setup guide (default: "ja")

    Returns
    -------
    str
        Setup guide text content

    Raises
    ------
    FileNotFoundError
        If the setup guide file doesn't exist for the specified language
    """
    resources_dir = Path(__file__).parent
    guide_file = resources_dir / f"setup_guide.{language}"

    if not guide_file.exists():
        # Fallback to Japanese if specified language doesn't exist
        guide_file = resources_dir / "setup_guide.ja"

    return guide_file.read_text(encoding="utf-8")


__all__ = ["load_setup_guide"]
