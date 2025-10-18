# MCP出力設計 - 調査・分析レポート

**作成日**: 2025-10-16
**MCP仕様バージョン**: 2025-06-18
**対象Issue**: #7 - MCP出力形式の改善

---

## エグゼクティブサマリー

MCPの最新仕様（2025-06-18）を徹底調査した結果、**現在の実装はMCP Annotationsを全く使用しておらず、LLMチャットUIへの出力制御が不十分**であることが判明しました。

### 主要な発見

1. **Annotations機能の未活用**: `audience`と`priority`を使えば、ユーザー向けとアシスタント向けの情報を適切に分離できる
2. **カード情報の不足**: keywords、artist、flavor_text、produced_mana、legalities、edhrec_rankがTextContentに表示されていない
3. **構造化データの最適化不足**: EmbeddedResourceにもAnnotationsを付与すべき

### 推奨アクション

- **Phase 1**: Annotationsの導入（audience、priority）
- **Phase 2**: 欠けているカード情報の追加（keywords、artist等）
- **Phase 3**: SearchOptionsによるユーザー制御可能な表示オプション

---

## 1. MCP仕様調査結果（2025-06-18）

### 1.1 三つのプリミティブ

MCPサーバーは3種類のプリミティブでコンテキストを提供します：

| プリミティブ | 制御主体 | 用途 | Scryfall MCPでの実装状況 |
|------------|---------|------|------------------------|
| **Prompts** | ユーザー | テンプレート化されたメッセージ | ❌ 未実装 |
| **Resources** | アプリケーション | 参照可能なコンテキストデータ | ❌ 未実装（将来的にルールテキスト等で有用） |
| **Tools** | モデル（LLM） | 実行可能な関数 | ✅ 実装済み（search_cards、autocomplete） |

### 1.2 Content Types完全仕様

#### TextContent（現在使用中）

```python
TextContent(
    type="text",
    text: str,  # マークダウン対応
    annotations: Annotations | None = None  # ⚠️ 現在未使用
)
```

**特性**:
- マークダウン形式をサポート（仕様で義務付けられてはいないが、多くのクライアントがサポート）
- LLMチャットUIに表示される主要コンテンツ
- `annotations.audience`で表示対象を制御可能

#### ImageContent

```python
ImageContent(
    type="image",
    data: str,  # Base64エンコード必須
    mimeType: str,  # "image/png", "image/jpeg"等
    annotations: Annotations | None = None
)
```

**制約**:
- URLは不可、Base64エンコードされたバイト列が必須
- サイズは1MB未満を推奨
- 現在の実装では未使用（カード画像はURL参照のみ）

#### EmbeddedResource（現在使用中）

```python
EmbeddedResource(
    type="resource",
    resource: TextResourceContents | BlobResourceContents,
    annotations: Annotations | None = None  # ⚠️ 現在未使用
)
```

**用途**:
- 構造化データの埋め込み（JSON等）
- アシスタント向けメタデータの提供
- 現在の実装ではJSON形式でカードデータを提供

### 1.3 Annotations詳細仕様

```python
Annotations(
    audience: list[Literal['user', 'assistant']] | None = None,
    priority: float (0.0-1.0) | None = None,
    lastModified: str | None = None  # ISO 8601形式
)
```

#### audience フィールド

| 値 | 意味 | クライアントの動作 | 使用例 |
|----|------|------------------|--------|
| `["user"]` | ユーザー向け | UIに表示、LLMコンテキストに**含めない可能性** | 成功メッセージ、カード画像 |
| `["assistant"]` | アシスタント向け | LLMコンテキストに含める、UIに**表示しない可能性** | デバッグ情報、詳細な構造化データ |
| `["user", "assistant"]` | 両方向け | UIに表示し、LLMコンテキストにも含める | エラーメッセージ、重要な通知 |

**重要**: `audience`の解釈はクライアント実装に依存しますが、仕様で標準化されています。

#### priority フィールド

| 範囲 | 意味 | 使用例 |
|------|------|--------|
| `1.0` | 最重要（必須） | エラーメッセージ、クリティカルな警告 |
| `0.7～0.9` | 高優先度 | カード名、マナコスト、タイプライン |
| `0.4～0.6` | 中優先度 | セット情報、価格情報 |
| `0.1～0.3` | 低優先度 | フレーバーテキスト、アーティスト情報 |
| `0.0` | 最低（完全にオプション） | デバッグログ |

**用途**: トークン制限時に、低優先度コンテンツを省略する判断材料として使用されます。

---

## 2. 現在の実装分析

### 2.1 presenter.py の現状

#### _format_single_card メソッド（lines 175-258）

**表示している情報**:
- ✅ カード名、マナコスト
- ✅ タイプライン
- ✅ パワー/タフネス
- ✅ オラクルテキスト
- ✅ セット情報、レアリティ
- ✅ 価格情報
- ✅ Scryfallリンク

**表示していない重要情報**:
- ❌ **keywords** (line 417 in models.py) - キーワード能力
- ❌ **flavor_text** (line 443) - フレーバーテキスト
- ❌ **artist** (line 445) - イラストレーター名
- ❌ **produced_mana** (line 418) - マナ生成情報（土地用）
- ❌ **legalities** (line 421) - フォーマット適格性
- ❌ **edhrec_rank** (line 467) - Commander人気度

**Annotationsの使用状況**:
```python
return TextContent(type="text", text=card_text)  # ⚠️ annotationsなし
```

#### _create_card_resource メソッド（lines 374-459）

**含まれているフィールド**:
- id, oracle_id, name, lang
- mana_cost, cmc, type_line, oracle_text
- colors, color_identity
- power, toughness, loyalty
- set, set_name, rarity, collector_number
- prices（非nullのみ）
- image_url（normal sizeのみ）

**含まれていない重要フィールド**:
- ❌ keywords
- ❌ flavor_text
- ❌ artist
- ❌ produced_mana
- ❌ legalities（意図的に除外、サイズ削減のため）
- ❌ edhrec_rank（意図的に除外）

**Annotationsの使用状況**:
```python
return EmbeddedResource(
    type="resource",
    resource=TextResourceContents(...)
    # ⚠️ annotationsなし
)
```

### 2.2 問題点の整理

#### 問題1: Annotationsの未活用

現在の実装では、すべてのコンテンツが以下のように扱われています：

```python
TextContent(type="text", text=card_text)
# デフォルト動作:
# - audience: 不明（クライアント依存）
# - priority: 不明（クライアント依存）
```

**影響**:
- ユーザー向けとアシスタント向けの情報が分離されていない
- トークン制限時の優先順位が不明確
- クライアントが適切な表示判断を下せない

#### 問題2: 重要情報の欠落

**ユーザーが頻繁に参照する情報が表示されていない**:

1. **keywords**: 「このカードは飛行を持っているか？」→ オラクルテキストを読まないとわからない
2. **artist**: MTGコミュニティで重視される情報
3. **produced_mana**: 「この土地は何色のマナを出せるか？」→ オラクルテキストを読まないとわからない
4. **format_filter指定時のlegality**: フォーマット適格性が即座にわからない

#### 問題3: 情報の過剰/不足のバランス

- **TextContent**: ユーザー向け情報が不足
- **EmbeddedResource**: アシスタント向け詳細データも不足（keywords等が含まれていない）

---

## 3. LLMチャットUI出力方法の分析

### 3.1 MCP仕様におけるUI表示フロー

```
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (scryfall-mcp)                                   │
│                                                              │
│ Tool実行 → Content生成                                       │
│  ├─ TextContent(audience=["user"], priority=0.8)           │
│  ├─ TextContent(audience=["assistant"], priority=0.9)      │
│  └─ EmbeddedResource(audience=["assistant"], priority=0.6) │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ MCP Client (Claude Desktop, VS Code等)                      │
│                                                              │
│ Annotationsに基づいてコンテンツをルーティング                │
│  ├─ audience=["user"] → UIに表示                           │
│  ├─ audience=["assistant"] → LLMコンテキストに送信         │
│  └─ priority考慮 → トークン制限時に低優先度を省略          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ ユーザーインターフェース                                      │
│                                                              │
│ 【チャットUI】                                               │
│  audience=["user"]のコンテンツを表示                         │
│  - カード名、マナコスト、タイプ                              │
│  - キーワード能力                                            │
│  - アーティスト情報                                          │
│  - Scryfallリンク                                           │
│                                                              │
│ 【LLMコンテキスト（非表示）】                                 │
│  audience=["assistant"]のコンテンツを送信                    │
│  - 構造化JSON（全フィールド）                                │
│  - デバッグ情報                                              │
│  - 内部統計                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 ベストプラクティスに基づく推奨設計

#### ユーザー向けコンテンツ（TextContent）

**目的**: 人間が読みやすい、簡潔な情報

```python
TextContent(
    type="text",
    text="""
## 1. 稲妻 {R}

**タイプ**: インスタント
**キーワード**: なし

**オラクルテキスト**:
クリーチャー1体かプレインズウォーカー1体かプレイヤー1人を対象とする。稲妻はそれに3点のダメージを与える。

**セット**: Dominaria Remastered (アンコモン)
**価格**: $0.25 | €0.20

*イラスト: Christopher Moeller*

[Scryfallで見る](https://scryfall.com/card/...)
""",
    annotations={
        "audience": ["user"],
        "priority": 0.8  # 高優先度（ユーザーが見るべき情報）
    }
)
```

#### アシスタント向けコンテンツ（EmbeddedResource）

**目的**: LLMが理解しやすい、構造化された詳細データ

```python
EmbeddedResource(
    type="resource",
    resource=TextResourceContents(
        uri="card://scryfall/abc123",
        mimeType="application/json",
        text=json.dumps({
            "id": "abc123",
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "cmc": 1,
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "keywords": [],  # 追加
            "produced_mana": None,
            "colors": ["R"],
            "legalities": {  # 追加（最小限）
                "standard": "not_legal",
                "modern": "legal",
                "legacy": "legal",
                "vintage": "legal",
                "commander": "legal"
            },
            "artist": "Christopher Moeller",  # 追加
            "flavor_text": None,  # 追加
            "edhrec_rank": 1234,  # 追加
            "prices": {"usd": "0.25"},
            "scryfall_uri": "https://..."
        }, indent=2)
    ),
    annotations={
        "audience": ["assistant"],
        "priority": 0.6  # 中優先度（補助データ）
    }
)
```

---

## 4. 設計修正案

### 4.1 Phase 1: Annotations導入（即座に実装可能）

#### 変更1: models.py - SearchOptionsの拡張

```python
class SearchOptions(BaseModel):
    """Search presentation options."""

    max_results: int = 10
    format_filter: str | None = None
    language: str | None = None

    # NEW: Annotations使用制御
    use_annotations: bool = True  # デフォルトでAnnotationsを使用

    # NEW: 表示制御オプション
    include_keywords: bool = True
    include_artist: bool = True
    include_flavor: bool = False
    include_mana_production: bool = True  # 土地用
    include_legalities: bool = False  # format_filter指定時のみ表示を推奨
    include_edhrec_rank: bool = False
```

#### 変更2: presenter.py - _format_single_card の拡張

```python
def _format_single_card(
    self, card: Card, index: int, options: SearchOptions
) -> TextContent:
    """Format a single card result with MCP Annotations."""
    from ..i18n.constants import CARD_LABELS

    is_japanese = self._mapping.language_code == "ja"
    labels = CARD_LABELS[self._mapping.language_code]

    # カード名とマナコスト（priority: 1.0 - 最重要）
    card_name = (
        card.printed_name if (is_japanese and card.printed_name) else card.name
    )
    card_text = f"## {index}. {card_name}"

    if card.mana_cost:
        card_text += f" {card.mana_cost}"

    card_text += "\n\n"

    # タイプライン（priority: 1.0 - 最重要）
    type_line_display = (
        card.printed_type_line
        if (is_japanese and card.printed_type_line)
        else card.type_line
    )

    if type_line_display:
        card_text += f"**{labels['type']}**: {type_line_display}\n"

    # NEW: キーワード能力（priority: 0.7 - 高優先度）
    if options.include_keywords and card.keywords:
        keywords_label = "キーワード能力" if is_japanese else "Keywords"
        card_text += f"**{keywords_label}**: {', '.join(card.keywords)}\n"

    # パワー/タフネス（priority: 0.7 - 高優先度）
    if card.power is not None and card.toughness is not None:
        card_text += f"**{labels['power_toughness']}**: {card.power}/{card.toughness}\n"

    # NEW: マナ生成（土地カード用、priority: 0.7 - 高優先度）
    if (options.include_mana_production and
        "Land" in card.type_line and
        card.produced_mana):
        produces_label = "生成マナ" if is_japanese else "Produces"
        mana_symbols = ' '.join([f"{{{m}}}" for m in card.produced_mana])
        card_text += f"**{produces_label}**: {mana_symbols}\n"

    # オラクルテキスト（priority: 0.8 - 高優先度）
    oracle_text_display = (
        card.printed_text
        if (is_japanese and card.printed_text)
        else card.oracle_text
    )

    if oracle_text_display:
        card_text += f"\n**{labels['oracle_text']}**:\n{oracle_text_display}\n"

    # NEW: フレーバーテキスト（priority: 0.3 - 低優先度、オプトイン）
    if options.include_flavor and card.flavor_text:
        card_text += f"\n> *{card.flavor_text}*\n"

    # セット情報（priority: 0.5 - 中優先度）
    if card.set_name:
        card_text += f"\n**{labels['set']}**: {card.set_name}"

        if card.rarity:
            rarity_map = self._RARITY_JA if is_japanese else self._RARITY_EN
            rarity_display = rarity_map.get(card.rarity, card.rarity.title())
            card_text += f" ({rarity_display})"

    # NEW: フォーマット適格性（format_filter指定時、priority: 0.7）
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

    # NEW: EDHREC順位（priority: 0.4 - 中-低優先度、オプトイン）
    if options.include_edhrec_rank and card.edhrec_rank is not None:
        rank_label = "EDHREC順位" if is_japanese else "EDHREC Rank"
        card_text += f"\n**{rank_label}**: #{card.edhrec_rank:,}"

    # 価格情報（priority: 0.5 - 中優先度）
    if card.prices:
        price_text = self._format_prices(card.prices.model_dump())
        if price_text:
            card_text += f"\n{price_text}"

    # NEW: アーティスト情報（priority: 0.3 - 低優先度、デフォルトON）
    if options.include_artist and card.artist:
        illustrated_by = "イラスト" if is_japanese else "Illustrated by"
        card_text += f"\n\n*{illustrated_by} {card.artist}*"

    # Scryfallリンク（priority: 0.5 - 中優先度）
    if card.scryfall_uri:
        card_text += f"\n[{labels['view_on_scryfall']}]({card.scryfall_uri})"

    card_text += "\n\n---\n"

    # NEW: MCP Annotations（ユーザー向け）
    annotations = None
    if options.use_annotations:
        annotations = Annotations(
            audience=["user"],  # ユーザーUI向け
            priority=0.8        # 高優先度
        )

    return TextContent(type="text", text=card_text, annotations=annotations)
```

#### 変更3: presenter.py - _create_card_resource の拡張

```python
def _create_card_resource(self, card: Card, index: int, options: SearchOptions) -> EmbeddedResource:
    """Create an EmbeddedResource with full metadata and MCP Annotations."""

    # 基本フィールド（既存）
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

    # NEW: 欠けていたフィールドの追加
    if card.keywords:
        card_metadata["keywords"] = card.keywords

    if card.flavor_text:
        card_metadata["flavor_text"] = card.flavor_text

    if card.artist:
        card_metadata["artist"] = card.artist

    if card.produced_mana:
        card_metadata["produced_mana"] = card.produced_mana

    # NEW: 最小限のlegalities（legal/banned/restrictedのみ、not_legalは除外）
    if options.include_legalities:
        legalities_compact = {
            fmt: status
            for fmt, status in card.legalities.model_dump().items()
            if status != "not_legal"
        }
        if legalities_compact:
            card_metadata["legalities"] = legalities_compact

    if card.edhrec_rank is not None:
        card_metadata["edhrec_rank"] = card.edhrec_rank

    # 価格情報（既存、non-nullのみ）
    if card.prices:
        prices = card.prices.model_dump()
        non_null_prices = {k: v for k, v in prices.items() if v is not None}
        if non_null_prices:
            card_metadata["prices"] = non_null_prices

    # 画像URL（既存、normal sizeのみ）
    if card.image_uris and card.image_uris.normal:
        card_metadata["image_url"] = str(card.image_uris.normal)

    # 両面カード情報（既存）
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

    # NEW: MCP Annotations（アシスタント向け）
    annotations = None
    if options.use_annotations:
        annotations = Annotations(
            audience=["assistant"],  # LLMコンテキスト向け
            priority=0.6             # 中優先度
        )

    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=AnyUrl(f"card://scryfall/{card.id}"),
            mimeType="application/json",
            text=json.dumps(card_metadata, indent=2, ensure_ascii=False),
        ),
        annotations=annotations
    )
```

#### 変更4: tools/search.py - SearchCardsRequestの拡張

```python
class SearchCardsRequest(BaseModel):
    """Request model for card search."""

    query: str = Field(description="Natural language search query (supports Japanese)")
    language: str | None = Field(default=None, description="Language code (ja, en)")
    max_results: int | None = Field(default=10, ge=1, le=175, description="Maximum results")
    format_filter: str | None = Field(default=None, description="Filter by Magic format")

    # NEW: 表示オプション
    use_annotations: bool = Field(default=True, description="Use MCP Annotations")
    include_keywords: bool = Field(default=True, description="Include keyword abilities")
    include_artist: bool = Field(default=True, description="Include artist information")
    include_flavor: bool = Field(default=False, description="Include flavor text")
    include_mana_production: bool = Field(default=True, description="Include mana production for lands")
    include_legalities: bool = Field(default=False, description="Include all format legalities")
    include_edhrec_rank: bool = Field(default=False, description="Include EDHREC rank")
```

#### 変更5: tools/search.py - SearchOptionsへのパラメータ伝播

```python
# Step 4: Present the results
search_options = SearchOptions(
    max_results=request.max_results or 10,
    format_filter=request.format_filter,
    language=request.language,
    # NEW: 表示オプション伝播
    use_annotations=request.use_annotations,
    include_keywords=request.include_keywords,
    include_artist=request.include_artist,
    include_flavor=request.include_flavor,
    include_mana_production=request.include_mana_production,
    include_legalities=request.include_legalities,
    include_edhrec_rank=request.include_edhrec_rank,
)

return presenter.present_results(search_result, built, search_options)
```

### 4.2 実装の優先順位

#### Phase 1: 即座に実装（Issue #7 対応）

1. ✅ **Annotationsの導入**
   - `_format_single_card`: `audience=["user"]`, `priority=0.8`
   - `_create_card_resource`: `audience=["assistant"]`, `priority=0.6`
   - 実装コスト: 低（既存コードに追加のみ）

2. ✅ **Keywords表示**
   - `include_keywords: bool = True`（デフォルトON）
   - クリーチャーカードで最も参照される情報
   - 実装コスト: 低

3. ✅ **Artist情報**
   - `include_artist: bool = True`（デフォルトON）
   - MTGコミュニティで重視される情報
   - 実装コスト: 低

4. ✅ **format_filter指定時のlegality表示**
   - `options.format_filter`が指定されている場合のみ表示
   - コンテキストに応じた有用な情報
   - 実装コスト: 低

#### Phase 2: 次期バージョン

5. **マナ生成情報**
   - `include_mana_production: bool = True`（デフォルトON）
   - 土地カード専用の条件付き表示
   - 実装コスト: 低-中

6. **EmbeddedResourceへのフィールド追加**
   - keywords, artist, flavor_text, produced_mana, edhrec_rank
   - legalities（最小限、オプトイン）
   - 実装コスト: 低

#### Phase 3: 将来的な拡張

7. **フレーバーテキスト**
   - `include_flavor: bool = False`（デフォルトOFF、オプトイン）
   - 需要は高いが全ユーザーには不要
   - 実装コスト: 低

8. **EDHREC順位**
   - `include_edhrec_rank: bool = False`（デフォルトOFF）
   - Commanderプレイヤー向け
   - 実装コスト: 低

9. **全フォーマット適格性**
   - `include_legalities: bool = False`（デフォルトOFF）
   - レスポンスサイズへの影響が大きい
   - 実装コスト: 低

---

## 5. 期待される効果

### 5.1 ユーザー体験の向上

**Before（現在）**:
```
## 1. Lightning Bolt {R}

**タイプ**: インスタント

**オラクルテキスト**:
クリーチャー1体かプレインズウォーカー1体かプレイヤー1人を対象とする。
稲妻はそれに3点のダメージを与える。

**セット**: Dominaria Remastered (アンコモン)
**価格**: $0.25

[Scryfallで見る](https://scryfall.com/card/...)
```

**After（Phase 1実装後）**:
```
## 1. Lightning Bolt {R}

**タイプ**: インスタント
**キーワード**: なし  ← NEW

**オラクルテキスト**:
クリーチャー1体かプレインズウォーカー1体かプレイヤー1人を対象とする。
稲妻はそれに3点のダメージを与える。

**セット**: Dominaria Remastered (アンコモン)
**価格**: $0.25

*イラスト: Christopher Moeller*  ← NEW

[Scryfallで見る](https://scryfall.com/card/...)
```

**After（Phase 2実装後）**:
```
## 1. Birds of Paradise {G}

**タイプ**: クリーチャー — 鳥
**キーワード**: 飛行  ← NEW
**パワー/タフネス**: 0/1
**生成マナ**: {W} {U} {B} {R} {G}  ← NEW（土地専用機能を応用）

**オラクルテキスト**:
飛行
{T}: 好きな色1色のマナ1点を加える。

**セット**: Ravnica Remastered (レア)
**Modern**: 適正  ← NEW（format_filter指定時）
**価格**: $5.99

*イラスト: Marcelo Vignali*  ← NEW

[Scryfallで見る](https://scryfall.com/card/...)
```

### 5.2 技術的な改善

1. **Annotationsによるメタデータ管理**
   - クライアントが適切な表示判断を下せる
   - トークン制限時の優先順位付けが明確

2. **情報の適切な分離**
   - ユーザー向け（`audience=["user"]`）: 簡潔で読みやすい
   - アシスタント向け（`audience=["assistant"]`）: 構造化された詳細データ

3. **柔軟な表示制御**
   - SearchOptionsによるユーザー制御
   - デフォルト値で適切な情報量を提供
   - オプトインで追加情報を取得可能

4. **後方互換性の維持**
   - すべての新オプションはデフォルト値を持つ
   - 既存のAPIリクエストは変更なく動作

### 5.3 パフォーマンスへの影響

**追加されるデータサイズ（1カードあたりの推定）**:

| フィールド | サイズ | 備考 |
|-----------|--------|------|
| keywords | ~50 bytes | 平均2-3個のキーワード |
| artist | ~30 bytes | アーティスト名 |
| flavor_text | ~0-200 bytes | オプトイン、ないカードも多い |
| produced_mana | ~20 bytes | 土地カードのみ |
| legalities（最小限） | ~0-100 bytes | オプトイン、legal/banned/restrictedのみ |
| edhrec_rank | ~10 bytes | オプトイン |
| **合計** | **~110-410 bytes/card** | オプトインなしで~110 bytes |

**10カード表示時の増加量**: 約1.1KB～4.1KB（オプトインなしで1.1KB）

**結論**: BrokenPipeError対策（16KB制限）には影響しない範囲内。

---

## 6. 実装チェックリスト

### Phase 1 実装タスク

- [ ] `src/scryfall_mcp/models.py`
  - [ ] SearchOptionsに新しいboolフラグを追加
  - [ ] SearchCardsRequestに新しいパラメータを追加

- [ ] `src/scryfall_mcp/search/presenter.py`
  - [ ] Annotationsをインポート
  - [ ] `_format_single_card`にAnnotationsを追加
  - [ ] keywords表示ロジックを追加
  - [ ] artist情報表示ロジックを追加
  - [ ] format_filter時のlegality表示ロジックを追加
  - [ ] `_create_card_resource`にAnnotationsを追加
  - [ ] `_create_card_resource`の引数に`options`を追加

- [ ] `src/scryfall_mcp/tools/search.py`
  - [ ] SearchOptionsへのパラメータ伝播を実装

- [ ] テストの追加
  - [ ] `tests/search/test_presenter.py`
    - [ ] Annotationsが正しく設定されているかテスト
    - [ ] keywords表示のテスト
    - [ ] artist表示のテスト
    - [ ] format_filter時のlegality表示テスト
    - [ ] オプションOFF時に表示されないことのテスト

### Phase 2 実装タスク

- [ ] `src/scryfall_mcp/search/presenter.py`
  - [ ] マナ生成情報の表示ロジック（土地カード用）
  - [ ] EmbeddedResourceに全フィールドを追加

- [ ] テストの追加
  - [ ] マナ生成表示のテスト（土地カード）
  - [ ] EmbeddedResourceのフィールド検証

### Phase 3 実装タスク

- [ ] `src/scryfall_mcp/search/presenter.py`
  - [ ] フレーバーテキスト表示ロジック
  - [ ] EDHREC順位表示ロジック
  - [ ] 全フォーマット適格性の表示ロジック

- [ ] テストの追加
  - [ ] フレーバーテキスト表示のテスト
  - [ ] EDHREC順位表示のテスト
  - [ ] 全フォーマット適格性表示のテスト

---

## 7. リスクと緩和策

### リスク1: クライアントがAnnotationsをサポートしない

**リスク**: 一部のMCPクライアントがAnnotationsを無視する可能性

**緩和策**:
- Annotationsがない場合でも動作するよう設計
- `use_annotations: bool`フラグで無効化可能
- TextContentの内容は変わらず、ユーザーには影響なし

### リスク2: レスポンスサイズの増加

**リスク**: 新しいフィールド追加でBrokenPipeErrorのリスク

**緩和策**:
- オプトイン方式（デフォルトOFFのフィールドが多い）
- 推定増加量は1.1KB/10カード（16KB制限に対して十分小さい）
- legalities、flavor_textは明示的にオプトイン

### リスク3: 後方互換性の破損

**リスク**: 既存のクライアントが動作しなくなる可能性

**緩和策**:
- すべての新パラメータにデフォルト値を設定
- 既存のAPIリクエストは変更なく動作
- Annotationsは追加のみ、既存フィールドは変更なし

---

## 8. 参考資料

### MCP仕様

- [MCP Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18)
- [Server Specification](https://modelcontextprotocol.io/specification/2025-06-18/server)
- [Tools Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Resources Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
- [Prompts Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

### Scryfall API

- [Scryfall API - Card Objects](https://scryfall.com/docs/api/cards)

### 関連ファイル

- `src/scryfall_mcp/models.py` (Card定義: lines 388-476)
- `src/scryfall_mcp/search/presenter.py` (現在の実装)
- `src/scryfall_mcp/tools/search.py` (検索ツール)

---

## 9. 結論

MCP 2025-06-18仕様の徹底調査により、**Annotations機能を活用することでLLMチャットUIへの出力を適切に制御できる**ことが判明しました。

### 重要な発見

1. **`audience`フィールド**: ユーザー向けとアシスタント向けの情報を明確に分離
2. **`priority`フィールド**: トークン制限時の優先順位付けを明示
3. **現在の実装の不足**: Annotationsを全く使用しておらず、重要なカード情報（keywords等）も欠落

### 推奨実装

**Phase 1（即座に実装）**:
- Annotationsの導入
- keywords、artist、format_filter時のlegality表示

**Phase 2（次期バージョン）**:
- マナ生成情報（土地用）
- EmbeddedResourceの拡張

**Phase 3（将来的な拡張）**:
- フレーバーテキスト、EDHREC順位、全フォーマット適格性

### 期待される効果

- ✅ ユーザーが必要な情報に即座にアクセス可能
- ✅ LLMが構造化データを適切に処理
- ✅ トークン制限時の適切な優先順位付け
- ✅ 後方互換性を維持しながらの段階的な改善

このレポートに基づいてIssue #7の実装を進めることを推奨します。
