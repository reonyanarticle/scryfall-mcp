"""Data models for search processing pipeline."""

from __future__ import annotations

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
    """Search presentation options."""

    max_results: int = 20
    include_images: bool = True
    format_filter: str | None = None
    language: str | None = None