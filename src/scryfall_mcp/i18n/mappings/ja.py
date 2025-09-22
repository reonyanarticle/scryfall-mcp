"""Japanese language mappings.

This module provides Japanese translations for Magic: The Gathering
terms and search syntax conversion.
"""

from __future__ import annotations

from .common import LanguageMapping


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
                "コストが": "usd<",
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
                "マナコスト": "マナコスト",
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
                "ドル": "USD",
                "ユーロ": "EUR",
                "チケット": "TIX",
                "円": "JPY",
                "米ドル": "USD",
            }
        )


# Global instance
japanese_mapping = JapaneseMapping()

# Common Japanese card names mapping (frequently searched cards)
JAPANESE_CARD_NAMES = {
    # Lands
    "平地": "Plains",
    "島": "Island",
    "沼": "Swamp",
    "山": "Mountain",
    "森": "Forest",

    # Famous cards
    "稲妻": "Lightning Bolt",
    "対抗呪文": "Counterspell",
    "暗黒の儀式": "Dark Ritual",
    "巨大化": "Giant Growth",
    "剣を鍬に": "Swords to Plowshares",
    "蓮の花の花びら": "Lotus Petal",
    "Black Lotus": "Black Lotus",
    "時の歩み": "Time Walk",
    "祖先の回想": "Ancestral Recall",
    "タイムツイスター": "Timetwister",
    "Mox Sapphire": "Mox Sapphire",
    "Mox Ruby": "Mox Ruby",
    "Mox Pearl": "Mox Pearl",
    "Mox Emerald": "Mox Emerald",
    "Mox Jet": "Mox Jet",

    # Common creatures
    "稲妻の天使": "Lightning Angel",
    "タルモゴイフ": "Tarmogoyf",
    "瞬唱の魔道士": "Snapcaster Mage",
    "石鍛冶の神秘家": "Stoneforge Mystic",
    "真の名の宿敵": "True-Name Nemesis",
    "宝船の巡航": "Treasure Cruise",
    "時を解す者、テフェリー": "Teferi, Time Raveler",

    # Planeswalkers
    "精神を刻む者、ジェイス": "Jace, the Mind Sculptor",
    "炎の血族、チャンドラ": "Chandra, Fire of Kaladesh",
    "死者の王、リリアナ": "Liliana of the Veil",
    "自然の怒り、ガラク": "Garruk Wildspeaker",

    # Artifacts
    "太陽の指輪": "Sol Ring",
    "精神石": "Mind Stone",
    "統率者の宝球": "Commander's Sphere",
    "敏捷なこそ泥": "Deft Duelist",
}