"""Search-pipeline data models (parser -> builder -> presenter)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class ParsedQuery(BaseModel):
    """Parsed natural language query with extracted entities."""

    original_text: str
    normalized_text: str
    intent: str
    entities: dict[str, list[str]]
    language: str


class BuiltQuery(BaseModel):
    """Built Scryfall query with metadata."""

    scryfall_query: str
    original_query: str
    suggestions: list[str]
    query_metadata: dict[str, Any]


class SearchOptions(BaseModel):
    """Search presentation options.

    Attributes
    ----------
    max_results : int
        Maximum number of results to return (default: 10).
        Reduced from 20 to prevent BrokenPipeError with large responses.
        Users can override to request up to 175 results.
    format_filter : str | None
        Optional format filter (e.g., "standard", "modern")
    language : str | None
        Optional language code for search (e.g., "en", "ja")
    use_annotations : bool
        Whether to use MCP Annotations for content (default: True)
    include_keywords : bool
        Include keyword abilities in output (default: True)
    include_artist : bool
        Include artist information in output (default: True)
    include_mana_production : bool
        Include mana production for lands (default: True)

    Notes
    -----
    Image data is not included in responses to comply with MCP ImageContent spec.
    Image URLs are provided in Scryfall links within card details.
    """

    max_results: int = 10  # Reduced from 20 to prevent pipe overflow
    format_filter: str | None = None
    language: str | None = None

    # Display control parameters
    use_annotations: bool = True
    include_keywords: bool = True
    include_artist: bool = True
    include_mana_production: bool = True

    # Opt-in legalities information
    include_legalities: bool = False


@dataclass(frozen=True)
class PresentedText:
    """Framework-neutral text section produced by the presenter.

    The tools layer converts this into ``mcp.types.TextContent``; the
    presenter itself stays unaware of the MCP SDK (Ports & Adapters).

    Attributes
    ----------
    text : str
        Markdown text to display
    audience : tuple[str, ...] | None
        Intended audience (e.g. ``("user", "assistant")``).
        None means "emit no annotations".
    priority : float | None
        Display priority for MCP annotations
    """

    text: str
    audience: tuple[str, ...] | None = None
    priority: float | None = None


@dataclass(frozen=True)
class PresentedResource:
    """Framework-neutral structured-data section (JSON resource).

    Converted into ``mcp.types.EmbeddedResource`` by the tools layer.

    Attributes
    ----------
    uri : str
        Resource URI (e.g. ``card://scryfall/{id}``)
    text : str
        Serialized resource body (JSON)
    mime_type : str
        MIME type of the body
    audience : tuple[str, ...] | None
        Intended audience; None means "emit no annotations"
    priority : float | None
        Display priority for MCP annotations
    """

    uri: str
    text: str
    mime_type: str = "application/json"
    audience: tuple[str, ...] | None = None
    priority: float | None = None
