# カード表示仕様（MCP出力フォーマット）

MCPツールがカード検索結果を返す際の表示フィールド・MCP Annotations・優先度の正本。調査・分析の経緯は [MCP-OUTPUT-DESIGN-REPORT.md](MCP-OUTPUT-DESIGN-REPORT.md) を参照。

## 表示フィールド一覧

MCPツール（`search_cards`）でカード検索結果を返す際、以下のフィールドを表示します：

### 必須フィールド（常に表示）
1. **カード名** (`name` / `printed_name`)
   - 日本語検索時は`printed_name`を優先表示
   - フォールバック: `name`（英語名）

2. **マナコスト** (`mana_cost`)
   - シンボル形式: `{R}`, `{2}{U}{U}`等
   - マナコストがないカード（土地等）は表示なし

3. **タイプライン** (`type_line` / `printed_type_line`)
   - 日本語検索時は`printed_type_line`を優先表示
   - フォールバック: `type_line`（英語タイプ）

4. **パワー/タフネス** (`power` / `toughness`)
   - クリーチャーカードのみ表示
   - 形式: `3/3`, `*/1+*`等

5. **オラクルテキスト** (`oracle_text` / `printed_text`)
   - 日本語検索時は`printed_text`を優先表示
   - フォールバック: `oracle_text`（英語テキスト）
   - カードの能力や効果を記載

6. **セット情報、レアリティ** (`set_name`, `rarity`)
   - セット名: 日本語または英語
   - レアリティ: コモン、アンコモン、レア、神話レア

### 追加フィールド（デフォルトON・`SearchOptions` で制御可能）

7. **キーワード能力** (`keywords`)
   - 飛行、速攻、接死、トランプル等のキーワード一覧
   - リスト形式: `["Flying", "Haste"]`
   - 表示形式: カンマ区切り

8. **イラストレーター** (`artist`)
   - カードイラストの作成者名
   - 表示形式: `*イラスト: アーティスト名*`（日本語）/ `*Illustrated by Artist Name*`（英語）

9. **マナ生成情報** (`produced_mana`)
   - **土地カード専用**のフィールド
   - 生成可能なマナ色のリスト: `["W", "U"]`等
   - 表示形式: `{W} {U}`（マナシンボル形式）

10. **フォーマット適格性** (`legalities`)
    - 各フォーマット（Standard、Modern、Legacy等）での適格性
    - 値: `legal`, `not_legal`, `restricted`, `banned`
    - **表示制御**: `format_filter`パラメータ指定時のみ、そのフォーマットの適格性を表示

## MCP Annotations仕様

すべてのコンテンツに**MCP Annotations**を付与し、クライアント側での適切な表示制御を可能にします。

### audience フィールドの重要な注意点

**Issue**: `audience=["user"]`はMCP仕様では"UIに表示される"と記載されているが、Claude DesktopなどのMCPクライアントでは**表示されないことがある**。

**解決策**: ユーザー向けコンテンツ（カード情報など）は`audience=["user", "assistant"]`を使用することで、**UIとLLMコンテキストの両方に確実に表示される**。

```python
# ✅ 正しい実装: ユーザー向けコンテンツ（TextContent）
TextContent(
    type="text",
    text="カード情報...",
    annotations=Annotations(
        audience=["user", "assistant"],  # UIとLLM両方に確実に表示
        priority=0.8                     # 高優先度
    )
)

# ✅ 正しい実装: アシスタント向けコンテンツ（EmbeddedResource）
EmbeddedResource(
    type="resource",
    resource=TextResourceContents(...),
    annotations=Annotations(
        audience=["assistant"],  # LLMコンテキストのみ（UI非表示）
        priority=0.6             # 中優先度
    )
)
```

**audience値の動作**:
| 値 | 意味 | 実際の動作 | 使用推奨 |
|----|------|-----------|---------|
| `["user"]` | ユーザー向け | UIに表示される**可能性**があるが保証されない | ❌ 非推奨 |
| `["assistant"]` | アシスタント向け | LLMコンテキストのみ、UI非表示 | ✅ 構造化データ用 |
| `["user", "assistant"]` | 両方 | **UI+LLM両方に確実に表示** | ✅ カード情報、エラー用 |

## 優先度ガイドライン

| フィールド | Priority | 理由 |
|-----------|----------|------|
| カード名、マナコスト、タイプ | 1.0 | 最重要（カード識別に必須） |
| オラクルテキスト、P/T | 0.8 | 高優先度（ゲームプレイに重要） |
| keywords、produced_mana | 0.7 | 高優先度（頻繁に参照） |
| セット、レアリティ、価格 | 0.5 | 中優先度（補助情報） |
| artist、legalities | 0.3-0.5 | 中-低優先度（オプション情報） |

## 実装参照

- 詳細設計: [MCP-OUTPUT-DESIGN-REPORT.md](MCP-OUTPUT-DESIGN-REPORT.md)
- 現在の実装: `src/scryfall_mcp/search/presenter.py`
- データモデル: `src/scryfall_mcp/models.py`（`Card` クラス）

