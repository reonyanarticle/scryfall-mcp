"""Search result presentation layer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .models import PresentedResource, PresentedText

if TYPE_CHECKING:
    from ..i18n import LanguageMapping
    from ..models import BuiltQuery, Card, SearchOptions, SearchResult

# Annotation priority levels (consumed by the MCP adapter in tools/)
PRIORITY_USER_CONTENT = 0.8  # User-facing card display
PRIORITY_METADATA = 0.6  # Machine-readable card data


class SearchPresenter:
    """Presents search results as framework-neutral content sections.

    Emits PresentedText / PresentedResource DTOs; the tools layer converts
    them to MCP content types. This keeps the core pipeline free of any
    MCP SDK dependency.
    """

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

    def __init__(self, locale_mapping: LanguageMapping) -> None:
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
    ) -> list[PresentedText | PresentedResource]:
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
        content_items: list[PresentedText | PresentedResource] = []

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
    ) -> PresentedText:
        """Create search summary content.

        Parameters
        ----------
        search_result : SearchResult
            Search results
        built_query : BuiltQuery
            Built query information

        Returns
        -------
        PresentedText
            Summary content item
        """
        from ..i18n.constants import CARD_LABELS

        labels = CARD_LABELS[self._mapping.language_code]
        is_japanese = self._mapping.language_code == "ja"

        if is_japanese:
            summary_text = (
                f"🔍 **{labels['search_results']}**\n\n"
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
                f"🔍 **{labels['search_results']}**\n\n"
                f"**Original Query**: {built_query.original_query}\n"
                f"**Scryfall Query**: `{built_query.scryfall_query}`\n"
                f"**Cards Found**: {search_result.total_cards}"
            )

            if search_result.total_cards > len(search_result.data):
                summary_text += f" (showing first {len(search_result.data)})"

            if search_result.has_more:
                summary_text += "\n**Note**: More results are available"

        return PresentedText(text=summary_text)

    def _format_cards(
        self, cards: list[Card], options: SearchOptions
    ) -> list[PresentedText | PresentedResource]:
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
        content_items: list[PresentedText | PresentedResource] = []

        for i, card in enumerate(cards, 1):
            # Add human-readable card presentation
            card_content = self._format_single_card(card, i, options)
            content_items.append(card_content)

            # Add structured card data as a resource for metadata preservation
            card_resource = self._create_card_resource(card, i, options)
            content_items.append(card_resource)

            # Note: ImageContent removed - MCP spec requires base64 data, not URLs
            # Image URLs are already included in text content and the card resource

        return content_items

    def _is_japanese(self) -> bool:
        """Return True when the presenter locale is Japanese."""
        return self._mapping.language_code == "ja"

    def _labels(self) -> dict[str, str]:
        """Return the localized card label dictionary for the current locale."""
        from ..i18n.constants import CARD_LABELS

        return CARD_LABELS[self._mapping.language_code]

    def _format_single_card(
        self, card: Card, index: int, options: SearchOptions
    ) -> PresentedText:
        """Format a single card result.

        Orchestrates the section helpers; each section owns its own
        markdown fragment.

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
        PresentedText
            Formatted card content
        """
        card_text = (
            self._format_card_header(card, index)
            + self._format_card_stats(card, options)
            + self._format_card_oracle_text(card)
            + self._format_card_set_info(card, options)
            + self._format_card_footer(card, options)
            + "\n\n---\n"
        )

        if options.use_annotations:
            return PresentedText(
                text=card_text,
                audience=("user", "assistant"),
                priority=PRIORITY_USER_CONTENT,
            )
        return PresentedText(text=card_text)

    def _format_card_header(self, card: Card, index: int) -> str:
        """Format the card heading (name + mana cost)."""
        # Use printed name for Japanese if available
        card_name = (
            card.printed_name
            if (self._is_japanese() and card.printed_name)
            else card.name
        )

        card_text = f"## {index}. {card_name}"
        if card.mana_cost:
            card_text += f" {card.mana_cost}"
        return card_text + "\n\n"

    def _format_card_stats(self, card: Card, options: SearchOptions) -> str:
        """Format type line, keywords, P/T, and mana production."""
        is_japanese = self._is_japanese()
        labels = self._labels()
        card_text = ""

        # Add type line - use printed version for Japanese if available
        type_line_display = (
            card.printed_type_line
            if (is_japanese and card.printed_type_line)
            else card.type_line
        )
        if type_line_display:
            card_text += f"**{labels['type']}**: {type_line_display}\n"

        # Add keywords
        if options.include_keywords and card.keywords:
            keywords_label = "キーワード能力" if is_japanese else "Keywords"
            card_text += f"**{keywords_label}**: {', '.join(card.keywords)}\n"

        if card.power is not None and card.toughness is not None:
            card_text += (
                f"**{labels['power_toughness']}**: {card.power}/{card.toughness}\n"
            )

        # Add mana production for lands
        if (
            options.include_mana_production
            and "Land" in card.type_line
            and card.produced_mana
        ):
            produces_label = "生成マナ" if is_japanese else "Produces"
            mana_symbols = " ".join([f"{{{m}}}" for m in card.produced_mana])
            card_text += f"**{produces_label}**: {mana_symbols}\n"

        return card_text

    def _format_card_oracle_text(self, card: Card) -> str:
        """Format the oracle text section (printed text preferred for ja)."""
        oracle_text_display = (
            card.printed_text
            if (self._is_japanese() and card.printed_text)
            else card.oracle_text
        )
        if not oracle_text_display:
            return ""
        return f"\n**{self._labels()['oracle_text']}**:\n{oracle_text_display}\n"

    def _format_card_set_info(self, card: Card, options: SearchOptions) -> str:
        """Format set name, rarity, format legality, and prices."""
        is_japanese = self._is_japanese()
        labels = self._labels()
        card_text = ""

        if card.set_name:
            card_text += f"\n**{labels['set']}**: {card.set_name}"

            if card.rarity:
                rarity_map = self._RARITY_JA if is_japanese else self._RARITY_EN
                rarity_display = rarity_map.get(card.rarity, card.rarity.title())
                card_text += f" ({rarity_display})"

        # Add format legality when format_filter is specified
        if options.format_filter:
            legality = getattr(card.legalities, options.format_filter, None)
            if legality:
                format_name = options.format_filter.title()
                legality_labels = {
                    "legal": "適正" if is_japanese else "Legal",
                    "not_legal": "不適正" if is_japanese else "Not Legal",
                    "restricted": "制限" if is_japanese else "Restricted",
                    "banned": "禁止" if is_japanese else "Banned",
                }
                legality_display = legality_labels.get(legality, legality)
                card_text += f"\n**{format_name}**: {legality_display}"

        if card.prices:
            price_text = self._format_prices(card.prices.model_dump())
            if price_text:
                card_text += f"\n{price_text}"

        return card_text

    def _format_card_footer(self, card: Card, options: SearchOptions) -> str:
        """Format artist attribution and the Scryfall link."""
        card_text = ""

        if options.include_artist and card.artist:
            illustrated_by = "イラスト" if self._is_japanese() else "Illustrated by"
            card_text += f"\n\n*{illustrated_by} {card.artist}*"

        if card.scryfall_uri:
            card_text += (
                f"\n\n[{self._labels()['view_on_scryfall']}]({card.scryfall_uri})"
            )

        return card_text

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

    def _create_suggestions(self, suggestions: list[str]) -> PresentedText:
        """Create suggestions content.

        Parameters
        ----------
        suggestions : list[str]
            List of suggestions

        Returns
        -------
        PresentedText
            Suggestions content item
        """
        if self._mapping.language_code == "ja":
            suggestions_text = "💡 **検索のヒント**\n\n"
        else:
            suggestions_text = "💡 **Search Suggestions**\n\n"

        for suggestion in suggestions:
            suggestions_text += f"• {suggestion}\n"

        return PresentedText(text=suggestions_text)

    def _create_query_explanation(self, built_query: BuiltQuery) -> PresentedText:
        """Create query explanation for complex queries.

        Parameters
        ----------
        built_query : BuiltQuery
            Built query with metadata

        Returns
        -------
        PresentedText
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

        return PresentedText(text=explanation_text)

    def _create_card_resource(
        self, card: Card, index: int, options: SearchOptions
    ) -> PresentedResource:
        """Create a card resource with minimal essential metadata.

        This method creates a compact card resource containing only essential
        game data, reducing response size by ~84% to prevent BrokenPipeError
        while maintaining all critical information for gameplay and analysis.

        Parameters
        ----------
        card : Card
            Card object to create resource for
        index : int
            Card index in search results
        options : SearchOptions
            Formatting options

        Returns
        -------
        PresentedResource
            Minimal structured card data resource

        Notes
        -----
        Removed bloat fields to reduce response size:
        - legalities (544 bytes) - query Scryfall API if needed
        - Extra image URLs (5 URLs) - keep only normal size
        - purchase_uris - use scryfall_uri instead
        - related_uris - use scryfall_uri instead
        - Metadata flags (digital, foil, promo, etc.)
        - Rank numbers (edhrec_rank, penny_rank)
        """
        # Create MINIMAL structured card data (essential fields only)
        card_metadata: dict[str, Any] = {
            "id": str(card.id),
            "oracle_id": str(card.oracle_id) if card.oracle_id else None,
            "name": card.name,
            "lang": card.lang,
            "mana_cost": card.mana_cost,
            "cmc": card.cmc,
            "type_line": card.type_line,
            "oracle_text": card.oracle_text,
            "colors": card.colors,
            "color_identity": card.color_identity,
            "power": card.power,
            "toughness": card.toughness,
            "loyalty": card.loyalty,
            "set": card.set,
            "set_name": card.set_name,
            "rarity": card.rarity,
            "collector_number": card.collector_number,
            "released_at": card.released_at.isoformat(),
            "scryfall_uri": str(card.scryfall_uri),
            "uri": str(card.uri),
        }

        # Add prices if available (compact format - only non-null prices)
        if card.prices:
            prices = card.prices.model_dump()
            non_null_prices = {k: v for k, v in prices.items() if v is not None}
            if non_null_prices:
                card_metadata["prices"] = non_null_prices

        # Add single image URL (normal size only - most commonly used)
        if card.image_uris and card.image_uris.normal:
            card_metadata["image_url"] = str(card.image_uris.normal)

        # Add card faces for double-faced cards (essential info only)
        if card.card_faces:
            card_metadata["card_faces"] = [
                {
                    "name": face.name,
                    "mana_cost": face.mana_cost,
                    "type_line": face.type_line,
                    "oracle_text": face.oracle_text,
                    "power": face.power,
                    "toughness": face.toughness,
                }
                for face in card.card_faces
            ]

        # Add optional display fields
        if card.keywords:
            card_metadata["keywords"] = card.keywords

        if card.flavor_text:
            card_metadata["flavor_text"] = card.flavor_text

        if card.artist:
            card_metadata["artist"] = card.artist

        if card.produced_mana:
            card_metadata["produced_mana"] = card.produced_mana

        if card.edhrec_rank is not None:
            card_metadata["edhrec_rank"] = card.edhrec_rank

        # Minimal legalities (legal/banned/restricted only, not_legal excluded)
        if options.include_legalities:
            legalities_compact = {
                fmt: status
                for fmt, status in card.legalities.model_dump().items()
                if status != "not_legal"
            }
            if legalities_compact:
                card_metadata["legalities"] = legalities_compact

        body = json.dumps(card_metadata, indent=2, ensure_ascii=False)
        if options.use_annotations:
            return PresentedResource(
                uri=f"card://scryfall/{card.id}",
                text=body,
                audience=("assistant",),
                priority=PRIORITY_METADATA,
            )
        return PresentedResource(uri=f"card://scryfall/{card.id}", text=body)
