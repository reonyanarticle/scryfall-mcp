"""Search result presentation layer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.types import EmbeddedResource, ImageContent, TextContent, TextResourceContents
from pydantic import AnyUrl

if TYPE_CHECKING:
    from ..i18n import LanguageMapping
    from ..models import BuiltQuery, Card, SearchOptions, SearchResult


class SearchPresenter:
    """Presents search results in MCP-compatible format."""

    # Rarity translations (language-independent constants)
    _RARITY_JA = {
        "common": "コモン",
        "uncommon": "アンコモン",
        "rare": "レア",
        "mythic": "神話レア",
    }

    _RARITY_EN = {
        "common": "Common",
        "uncommon": "Uncommon",
        "rare": "Rare",
        "mythic": "Mythic Rare",
    }

    def __init__(self, locale_mapping: LanguageMapping):
        """Initialize the presenter with locale-specific mappings.

        Parameters
        ----------
        locale_mapping : LanguageMapping
            Language-specific mappings for presentation
        """
        self._mapping = locale_mapping

    def present_results(
        self,
        search_result: SearchResult,
        built_query: BuiltQuery,
        search_options: SearchOptions,
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Format search results for MCP presentation.

        Parameters
        ----------
        search_result : SearchResult
            Search results from Scryfall API
        built_query : BuiltQuery
            Built query with metadata
        search_options : SearchOptions
            Presentation options

        Returns
        -------
        list
            MCP content items for presentation
        """
        content_items: list[TextContent | ImageContent | EmbeddedResource] = []

        # Add search summary
        summary = self._create_summary(search_result, built_query)
        content_items.append(summary)

        # Add card results
        card_items = self._format_cards(
            search_result.data[: search_options.max_results], search_options
        )
        content_items.extend(card_items)

        # Add suggestions if available
        if built_query.suggestions:
            suggestions = self._create_suggestions(built_query.suggestions)
            content_items.append(suggestions)

        # Add query explanation for complex queries
        if built_query.query_metadata.get("query_complexity") == "complex":
            explanation = self._create_query_explanation(built_query)
            content_items.append(explanation)

        return content_items

    def _create_summary(
        self, search_result: SearchResult, built_query: BuiltQuery
    ) -> TextContent:
        """Create search summary content.

        Parameters
        ----------
        search_result : SearchResult
            Search results
        built_query : BuiltQuery
            Built query information

        Returns
        -------
        TextContent
            Summary content item
        """
        if self._mapping.language_code == "ja":
            summary_text = (
                f"🔍 **検索結果**\n\n"
                f"**元のクエリ**: {built_query.original_query}\n"
                f"**Scryfallクエリ**: `{built_query.scryfall_query}`\n"
                f"**見つかったカード**: {search_result.total_cards}枚"
            )

            if search_result.total_cards > len(search_result.data):
                summary_text += f" (最初の{len(search_result.data)}枚を表示)"

            if search_result.has_more:
                summary_text += "\n**注意**: さらに多くの結果があります"

        else:
            summary_text = (
                f"🔍 **Search Results**\n\n"
                f"**Original Query**: {built_query.original_query}\n"
                f"**Scryfall Query**: `{built_query.scryfall_query}`\n"
                f"**Cards Found**: {search_result.total_cards}"
            )

            if search_result.total_cards > len(search_result.data):
                summary_text += f" (showing first {len(search_result.data)})"

            if search_result.has_more:
                summary_text += "\n**Note**: More results are available"

        return TextContent(type="text", text=summary_text)

    def _format_cards(
        self, cards: list[Card], options: SearchOptions
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Format individual card results.

        Parameters
        ----------
        cards : list[Card]
            Cards to format
        options : SearchOptions
            Formatting options

        Returns
        -------
        list
            Formatted card content items
        """
        content_items: list[TextContent | ImageContent | EmbeddedResource] = []

        for i, card in enumerate(cards, 1):
            # Add human-readable card presentation
            card_content = self._format_single_card(card, i, options)
            content_items.append(card_content)

            # Add structured card data as EmbeddedResource for metadata preservation
            card_resource = self._create_card_resource(card, i)
            content_items.append(card_resource)

            # Add card image if requested and available
            if options.include_images and card.image_uris and card.image_uris.normal:
                image_content = ImageContent(
                    type="image",
                    data=str(card.image_uris.normal),
                    mimeType="image/jpeg",
                )
                content_items.append(image_content)

        return content_items

    def _format_single_card(
        self, card: Card, index: int, options: SearchOptions
    ) -> TextContent:  # noqa: ARG002
        """Format a single card result.

        Parameters
        ----------
        card : Card
            Card to format
        index : int
            Card index in results
        options : SearchOptions
            Formatting options

        Returns
        -------
        TextContent
            Formatted card content
        """
        if self._mapping.language_code == "ja":
            card_text = f"## {index}. {card.name}"
        else:
            card_text = f"## {index}. {card.name}"

        # Add mana cost if available
        if card.mana_cost:
            card_text += f" {card.mana_cost}"

        card_text += "\n\n"

        # Add type line
        if card.type_line:
            if self._mapping.language_code == "ja":
                card_text += f"**タイプ**: {card.type_line}\n"
            else:
                card_text += f"**Type**: {card.type_line}\n"

        # Add power/toughness for creatures
        if card.power is not None and card.toughness is not None:
            if self._mapping.language_code == "ja":
                card_text += f"**パワー/タフネス**: {card.power}/{card.toughness}\n"
            else:
                card_text += f"**Power/Toughness**: {card.power}/{card.toughness}\n"

        # Add oracle text
        if card.oracle_text:
            if self._mapping.language_code == "ja":
                card_text += f"**効果**:\n{card.oracle_text}\n"
            else:
                card_text += f"**Oracle Text**:\n{card.oracle_text}\n"

        # Add set information
        if card.set_name:
            if self._mapping.language_code == "ja":
                card_text += f"**セット**: {card.set_name}"
            else:
                card_text += f"**Set**: {card.set_name}"

            if card.rarity:
                rarity_map = (
                    self._RARITY_JA
                    if self._mapping.language_code == "ja"
                    else self._RARITY_EN
                )
                rarity_display = rarity_map.get(card.rarity, card.rarity.title())
                card_text += f" ({rarity_display})"

        # Add prices if available
        if card.prices:
            price_text = self._format_prices(card.prices.model_dump())
            if price_text:
                card_text += f"\n{price_text}"

        # Add Scryfall link
        if card.scryfall_uri:
            if self._mapping.language_code == "ja":
                card_text += f"\n\n[Scryfallで詳細を見る]({card.scryfall_uri})"
            else:
                card_text += f"\n\n[View on Scryfall]({card.scryfall_uri})"

        card_text += "\n\n---\n"

        return TextContent(type="text", text=card_text)

    def _format_prices(self, prices: dict[str, str | None]) -> str:
        """Format card pricing information.

        Parameters
        ----------
        prices : dict
            Price information from Scryfall

        Returns
        -------
        str
            Formatted price string
        """
        price_parts = []

        if prices.get("usd"):
            price_parts.append(f"${prices['usd']}")

        if prices.get("eur"):
            price_parts.append(f"€{prices['eur']}")

        if prices.get("tix"):
            price_parts.append(f"{prices['tix']} tix")

        if price_parts:
            if self._mapping.language_code == "ja":
                return f"**価格**: {' | '.join(price_parts)}"
            else:
                return f"**Price**: {' | '.join(price_parts)}"

        return ""

    def _create_suggestions(self, suggestions: list[str]) -> TextContent:
        """Create suggestions content.

        Parameters
        ----------
        suggestions : list[str]
            List of suggestions

        Returns
        -------
        TextContent
            Suggestions content item
        """
        if self._mapping.language_code == "ja":
            suggestions_text = "💡 **検索のヒント**\n\n"
        else:
            suggestions_text = "💡 **Search Suggestions**\n\n"

        for suggestion in suggestions:
            suggestions_text += f"• {suggestion}\n"

        return TextContent(type="text", text=suggestions_text)

    def _create_query_explanation(self, built_query: BuiltQuery) -> TextContent:
        """Create query explanation for complex queries.

        Parameters
        ----------
        built_query : BuiltQuery
            Built query with metadata

        Returns
        -------
        TextContent
            Query explanation content item
        """
        if self._mapping.language_code == "ja":
            explanation_text = "🔍 **検索クエリの詳細**\n\n"
            explanation_text += f"**複雑さ**: {built_query.query_metadata.get('query_complexity', 'unknown')}\n"
            explanation_text += f"**予想結果数**: {built_query.query_metadata.get('estimated_results', 'unknown')}\n"
        else:
            explanation_text = "🔍 **Query Analysis**\n\n"
            explanation_text += f"**Complexity**: {built_query.query_metadata.get('query_complexity', 'unknown')}\n"
            explanation_text += f"**Expected Results**: {built_query.query_metadata.get('estimated_results', 'unknown')}\n"

        # Add entity breakdown
        entities = built_query.query_metadata.get("extracted_entities", {})
        if any(entities.values()):
            if self._mapping.language_code == "ja":
                explanation_text += "\n**抽出された要素**:\n"
            else:
                explanation_text += "\n**Extracted Elements**:\n"

            for entity_type, entity_list in entities.items():
                if entity_list:
                    entity_names = {
                        "colors": "色"
                        if self._mapping.language_code == "ja"
                        else "Colors",
                        "types": "タイプ"
                        if self._mapping.language_code == "ja"
                        else "Types",
                        "numbers": "数値"
                        if self._mapping.language_code == "ja"
                        else "Numbers",
                        "card_names": "カード名"
                        if self._mapping.language_code == "ja"
                        else "Card Names",
                        "sets": "セット"
                        if self._mapping.language_code == "ja"
                        else "Sets",
                        "formats": "フォーマット"
                        if self._mapping.language_code == "ja"
                        else "Formats",
                    }
                    entity_name = entity_names.get(entity_type, entity_type)
                    explanation_text += (
                        f"• **{entity_name}**: {', '.join(entity_list)}\n"
                    )

        return TextContent(type="text", text=explanation_text)

    def _create_card_resource(self, card: Card, index: int) -> EmbeddedResource:
        """Create an EmbeddedResource with structured card metadata.

        Parameters
        ----------
        card : Card
            Card object to create resource for
        index : int
            Card index in search results

        Returns
        -------
        EmbeddedResource
            Structured card data resource
        """
        # Create structured card data preserving key metadata
        card_metadata: dict[str, Any] = {
            "id": str(card.id),
            "oracle_id": str(card.oracle_id),
            "name": card.name,
            "lang": card.lang,
            "mana_cost": card.mana_cost,
            "cmc": card.cmc,
            "type_line": card.type_line,
            "oracle_text": card.oracle_text,
            "colors": card.colors,
            "color_identity": card.color_identity,
            "keywords": card.keywords,
            "power": card.power,
            "toughness": card.toughness,
            "loyalty": card.loyalty,
            "set": card.set,
            "set_name": card.set_name,
            "rarity": card.rarity,
            "collector_number": card.collector_number,
            "artist": card.artist,
            "released_at": card.released_at.isoformat(),
            "digital": card.digital,
            "prices": card.prices.model_dump() if card.prices else None,
            "legalities": card.legalities.model_dump(),
            "image_uris": self._serialize_urls(card.image_uris.model_dump())
            if card.image_uris
            else None,
            "purchase_uris": self._serialize_urls(card.purchase_uris.model_dump())
            if card.purchase_uris
            else None,
            "related_uris": self._serialize_urls(card.related_uris.model_dump())
            if card.related_uris
            else None,
            "scryfall_uri": str(card.scryfall_uri),
            "uri": str(card.uri),
            "edhrec_rank": card.edhrec_rank,
            "penny_rank": card.penny_rank,
            "reserved": card.reserved,
            "foil": card.foil,
            "nonfoil": card.nonfoil,
            "promo": card.promo,
            "reprint": card.reprint,
            "variation": card.variation,
            "full_art": card.full_art,
            "textless": card.textless,
        }

        # Add card faces for double-faced cards
        if card.card_faces:
            face_data: list[dict[str, Any]] = [
                face.model_dump() for face in card.card_faces
            ]
            card_metadata["card_faces"] = face_data

        return EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=AnyUrl(f"card://scryfall/{card.id}"),
                mimeType="application/json",
                text=json.dumps(card_metadata, indent=2, ensure_ascii=False),
            ),
        )

    def _serialize_urls(self, data: dict[str, Any]) -> dict[str, str | None]:
        """Convert HttpUrl objects to strings for JSON serialization.

        Parameters
        ----------
        data : dict
            Dictionary potentially containing HttpUrl objects

        Returns
        -------
        dict
            Dictionary with HttpUrl objects converted to strings
        """
        return {
            key: str(value) if value is not None else None
            for key, value in data.items()
        }
