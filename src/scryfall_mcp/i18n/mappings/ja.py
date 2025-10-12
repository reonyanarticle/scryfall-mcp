"""Japanese language mappings.

This module provides Japanese translations for Magic: The Gathering
terms and search syntax conversion.
"""

from __future__ import annotations

from ...models import LanguageMapping


class JapaneseMapping(LanguageMapping):
    """Japanese language mappings for Magic: The Gathering terms."""

    def __init__(self) -> None:
        """Initialize Japanese mappings."""
        super().__init__(
            language_code="ja",
            language_name="日本語",
            locale_code="ja_JP",
            colors={
                "white": "w",
                "blue": "u",
                "black": "b",
                "red": "r",
                "green": "g",
                "colorless": "c",
            },
            types={
                # Basic types
                "artifact": "artifact",
                "creature": "creature",
                "enchantment": "enchantment",
                "instant": "instant",
                "land": "land",
                "planeswalker": "planeswalker",
                "sorcery": "sorcery",
                # Supertypes
                "basic": "basic",
                "legendary": "legendary",
                "snow": "snow",
                # Common subtypes
                "equipment": "equipment",
                "aura": "aura",
                "vehicle": "vehicle",
                "token": "token",
            },
            operators={
                "equals": "=",
                "not_equals": "!=",
                "less_than": "<",
                "less_than_or_equal": "<=",
                "greater_than": ">",
                "greater_than_or_equal": ">=",
                "contains": ":",
                "not_contains": "-",
            },
            formats={
                "standard": "standard",
                "pioneer": "pioneer",
                "modern": "modern",
                "legacy": "legacy",
                "vintage": "vintage",
                "commander": "commander",
                "pauper": "pauper",
                "historic": "historic",
                "alchemy": "alchemy",
                "brawl": "brawl",
            },
            rarities={
                "common": "common",
                "uncommon": "uncommon",
                "rare": "rare",
                "mythic": "mythic",
                "special": "special",
                "bonus": "bonus",
            },
            set_types={
                "core": "core",
                "expansion": "expansion",
                "masters": "masters",
                "draft_innovation": "draft_innovation",
                "commander": "commander",
                "planechase": "planechase",
                "archenemy": "archenemy",
                "from_the_vault": "from_the_vault",
                "premium_deck": "premium_deck",
                "duel_deck": "duel_deck",
                "starter": "starter",
                "box": "box",
                "promo": "promo",
                "token": "token",
                "memorabilia": "memorabilia",
                "treasure_chest": "treasure_chest",
                "spellbook": "spellbook",
                "arsenal": "arsenal",
            },
            search_keywords={
                # Colors
                "白": "c:w",
                "青": "c:u",
                "黒": "c:b",
                "赤": "c:r",
                "緑": "c:g",
                "無色": "c:c",
                "白い": "c:w",
                "青い": "c:u",
                "黒い": "c:b",
                "赤い": "c:r",
                "緑い": "c:g",
                "無色の": "c:c",
                # Basic search terms
                "色": "c",
                "カラー": "c",
                "色識別": "id",
                "マナ": "m",
                "マナコスト": "m",
                "点数で見たマナコスト": "cmc",
                "マナ総量": "mv",
                "タイプ": "t",
                "種族": "t",
                "テキスト": "o",
                "オラクルテキスト": "o",
                "パワー": "p",
                "タフネス": "tou",
                "忠誠度": "loy",
                "レアリティ": "r",
                "希少度": "r",
                "セット": "s",
                "エキスパンション": "s",
                "ブロック": "b",
                "フォーマット": "f",
                "アーティスト": "a",
                "イラストレーター": "a",
                "フレーバー": "fl",
                "フレーバーテキスト": "ft",
                "ウォーターマーク": "w",
                "年": "year",
                "価格": "usd",
                "言語": "lang",
                # Card types (Japanese)
                "アーティファクト": "t:artifact",
                "クリーチャー": "t:creature",
                "エンチャント": "t:enchantment",
                "インスタント": "t:instant",
                "土地": "t:land",
                "ランド": "t:land",
                "プレインズウォーカー": "t:planeswalker",
                "ソーサリー": "t:sorcery",
                "部族": "t:tribal",
                # Supertypes
                "基本": "t:basic",
                "伝説の": "t:legendary",
                "雪": "t:snow",
                # Subtypes
                "装身具": "t:equipment",
                "オーラ": "t:aura",
                "機体": "t:vehicle",
                "トークン": "t:token",
                # Boolean terms
                "である": "is",
                "でない": "not",
                "かつ": "",  # implicit in Scryfall
                "または": "or",
                "そして": "",
                "でかつ": "",
                # Special keywords
                "多色": "multicolor",
                "多色の": "multicolor",
                "単色": "monocolor",
                "単色の": "monocolor",
                "再録": "reprint",
                "新しい": "new",
                "古い": "old",
                "フォイル": "foil",
                "ノンフォイル": "nonfoil",
                "デジタル": "digital",
                "紙": "paper",
                "プロモ": "promo",
                "ユニーク": "unique",
                "ファニー": "funny",
                "使用可能": "legal",
                "禁止": "banned",
                "制限": "restricted",
                # Keyword abilities - Phase 1: Evergreen keywords (常磐木キーワード)
                "飛行": "keyword:flying",
                "飛行を持つ": "keyword:flying",
                "飛行持ち": "keyword:flying",
                "速攻": "keyword:haste",
                "速攻を持つ": "keyword:haste",
                "速攻持ち": "keyword:haste",
                "接死": "keyword:deathtouch",
                "接死を持つ": "keyword:deathtouch",
                "接死持ち": "keyword:deathtouch",
                "トランプル": "keyword:trample",
                "トランプルを持つ": "keyword:trample",
                "トランプル持ち": "keyword:trample",
                "警戒": "keyword:vigilance",
                "警戒を持つ": "keyword:vigilance",
                "警戒持ち": "keyword:vigilance",
                "先制攻撃": 'keyword:"first strike"',
                "先制攻撃を持つ": 'keyword:"first strike"',
                "先制攻撃持ち": 'keyword:"first strike"',
                "二段攻撃": 'keyword:"double strike"',
                "二段攻撃を持つ": 'keyword:"double strike"',
                "二段攻撃持ち": 'keyword:"double strike"',
                "絆魂": "keyword:lifelink",
                "絆魂を持つ": "keyword:lifelink",
                "絆魂持ち": "keyword:lifelink",
                "呪禁": "keyword:hexproof",
                "呪禁を持つ": "keyword:hexproof",
                "呪禁持ち": "keyword:hexproof",
                "到達": "keyword:reach",
                "到達を持つ": "keyword:reach",
                "到達持ち": "keyword:reach",
                # Keyword abilities - Phase 2: Common deciduous keywords
                "威迫": "keyword:menace",
                "威迫を持つ": "keyword:menace",
                "威迫持ち": "keyword:menace",
                "瞬速": "keyword:flash",
                "瞬速を持つ": "keyword:flash",
                "瞬速持ち": "keyword:flash",
                "多相": "keyword:changeling",
                "多相を持つ": "keyword:changeling",
                "多相持ち": "keyword:changeling",
                "防衛": "keyword:defender",
                "防衛を持つ": "keyword:defender",
                "防衛持ち": "keyword:defender",
                "護法": "keyword:ward",
                "護法を持つ": "keyword:ward",
                "護法持ち": "keyword:ward",
                # Formats (Japanese)
                "スタンダード": "f:standard",
                "パイオニア": "f:pioneer",
                "モダン": "f:modern",
                "レガシー": "f:legacy",
                "ヴィンテージ": "f:vintage",
                "統率者": "f:commander",
                "コマンダー": "f:commander",
                "パウパー": "f:pauper",
                "ヒストリック": "f:historic",
                "アルケミー": "f:alchemy",
                "ブロール": "f:brawl",
                # Rarities (Japanese)
                "コモン": "r:common",
                "アンコモン": "r:uncommon",
                "レア": "r:rare",
                "神話レア": "r:mythic",
                "特殊": "r:special",
                "ボーナス": "r:bonus",
                # Operators (Japanese)
                "等しい": "=",
                "と等しい": "=",
                "ではない": "!=",
                "未満": "<",
                "以下": "<=",
                "より大きい": ">",
                "以上": ">=",
                "含む": ":",
                "含まない": "-",
            },
            phrases={
                # Common search phrases
                "を持つカード": "",
                "のカード": "",
                "を持つクリーチャー": "t:creature",
                "を持つアーティファクト": "t:artifact",
                "を持つエンチャント": "t:enchantment",
                "を持つインスタント": "t:instant",
                "を持つソーサリー": "t:sorcery",
                "を持つプレインズウォーカー": "t:planeswalker",
                "を持つ土地": "t:land",
                # Power/toughness
                "パワーが": "p=",
                "パワーが等しい": "p=",
                "パワーがより大きい": "p>",
                "パワーが未満": "p<",
                "パワーが以上": "p>=",
                "パワーが以下": "p<=",
                "タフネスが": "tou=",
                "タフネスが等しい": "tou=",
                "タフネスがより大きい": "tou>",
                "タフネスが未満": "tou<",
                "タフネスが以上": "tou>=",
                "タフネスが以下": "tou<=",
                # Mana cost
                "マナコスト": "m:",
                "点数で見たマナコスト": "cmc:",
                "マナ総量": "mv:",
                "コストが": "m:",
                "のマナを必要とする": "m:",
                # Colors
                "白のカード": "c:w",
                "青のカード": "c:u",
                "黒のカード": "c:b",
                "赤のカード": "c:r",
                "緑のカード": "c:g",
                "無色のカード": "c:c",
                # Formats
                "で使用可能": "f:",
                "で禁止": "banned:",
                "で制限": "restricted:",
                # Sets
                "セットから": "s:",
                "に収録": "s:",
                "から": "s:",
                # Text search
                "テキストに": "o:",
                "オラクルテキストに": "o:",
                "フレーバーテキストに": "ft:",
                # Price
                "価格が": "usd<",
                "価格未満": "usd<",
                "価格以上": "usd>",
                "価格ちょうど": "usd:",
                "価格コストが": "usd<",
                "より安い": "usd<",
                "より高い": "usd>",
                # Numeric expressions
                "マナ": "",
                "点": "",
                "円": "",
                "ドル": "",
                # Common responses
                "検索結果がありません": "検索にマッチするカードが見つかりませんでした。",
                "結果が多すぎます": "結果が多すぎます。検索条件を絞り込んでください。",
                "検索エラー": "検索でエラーが発生しました。",
                "無効なクエリ": "無効な検索クエリです。",
                # Card information
                "マナコスト情報": "マナコスト",
                "タイプ": "タイプ",
                "オラクルテキスト": "オラクルテキスト",
                "フレーバーテキスト": "フレーバーテキスト",
                "パワー／タフネス": "パワー／タフネス",
                "忠誠度": "忠誠度",
                "レアリティ": "レアリティ",
                "セット": "セット",
                "アーティスト": "アーティスト",
                "コレクター番号": "コレクター番号",
                "価格": "価格",
                "リーガル情報": "使用可能フォーマット",
                # Currency
                "通貨ドル": "USD",
                "ユーロ": "EUR",
                "チケット": "TIX",
                "通貨円": "JPY",
                "米ドル": "USD",
            },
        )


# Global instance
japanese_mapping = JapaneseMapping()

# DEPRECATED: This static card name dictionary is no longer used.
# Scryfall natively supports multilingual card names via the printed_name field
# and lang: parameter. No pre-translation is needed.
#
# The query builder now passes Japanese card names directly to Scryfall,
# which handles the lookup automatically. This provides:
# - Complete coverage of all 27,000+ cards
# - Zero maintenance burden
# - Automatic support for new sets
# - Native fuzzy matching in all languages
#
# For reference only (will be removed in future version):
JAPANESE_CARD_NAMES: dict[str, str] = {
    # This dictionary is no longer used by the codebase
    # See: builder.py _convert_card_names() method
}
