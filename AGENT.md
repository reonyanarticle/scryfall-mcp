# Scryfall MCP Server - AI Agent Instructions

このドキュメントは、Scryfall MCP Serverプロジェクトに対する重要な設計思想、技術的制約、および改善課題をまとめたものです。

## プロジェクト概要

Magic: The GatheringのカードデータをMCP (Model Context Protocol)経由でAIアシスタントに提供するサーバー。Scryfall APIとの統合により、日本語を含む自然言語でのカード検索機能を提供します。

## 重要な技術的制約

### Scryfall API制約
- **レート制限**: 最大10 requests/second、リクエスト間隔75-100ms以上を維持
- **必須HTTPヘッダー**: `User-Agent`と`Accept`ヘッダーがないと403でブロック
- **データ制限**: 1ページ最大175カード

### 開発規約
- **型ヒント必須**: PEP585準拠、pydanticベース
- **docstring必須**: Numpy styleで記載
- **非同期処理**: すべてのI/O処理はasync/await
- **早期リターン推奨**: 深いネスト回避
- **言語依存ファイル命名規則**: 言語コードを拡張子として使用
  - 形式: `{base_name}.{language_code}`
  - 例: `setup_guide.ja` (日本語), `setup_guide.en` (英語)
  - フォールバック: デフォルト言語ファイル（拡張子なし）または`.ja`
  - 実装: `Path(__file__).parent / f"setup_guide.{language}"`
  - 目的: 言語別リソースの管理を簡潔化し、ファイル命名の一貫性を保つ

## コーディング規約

このセクションでは、Readable CodeとClean Codeの原則に基づく具体的なコーディング規約を定義します。

### 関数の長さ制限

**原則**: 関数は最大50行を目安とし、それを超える場合は小さなヘルパーメソッドに分割すること。

**理由**:
- 可読性の向上: 短い関数は理解しやすく、レビューしやすい
- テスト容易性: 小さな関数は単体テストが書きやすい
- 保守性: バグの発見と修正が容易

**実装例**:
```python
# ❌ 悪い例: 90行の長大な関数
async def execute(arguments: dict[str, Any]) -> list[TextContent]:
    request = SearchCardsRequest(**arguments)
    mapping = get_current_mapping()
    parser = SearchParser(mapping)
    builder = QueryBuilder(mapping)
    # ... 80行以上のロジックが続く ...

# ✅ 良い例: ヘルパーメソッドに分割（26行）
async def execute(arguments: dict[str, Any]) -> list[TextContent]:
    request = _validate_request(arguments)
    builder, presenter, built = _build_query_pipeline(request)
    scryfall_query = _add_query_filters(built.scryfall_query, request)
    result = await _execute_api_search(scryfall_query, request)
    if isinstance(result, list):
        return result
    search_options = _create_search_options(request)
    return presenter.present_results(result, built, search_options)
```

**参考**: `src/scryfall_mcp/tools/search.py` の `CardSearchTool.execute` メソッドは90行→26行にリファクタリング済み

### 型アノテーション必須

**原則**: すべての変数、関数パラメータ、戻り値に明示的な型ヒントを付けること。

**詳細ルール**:
1. **PEP 585準拠**: `list[str]`, `dict[str, int]` など組み込み型を使用（Python 3.9+）
2. **Union型**: `str | None`, `int | str` のようにパイプ演算子を使用（Python 3.10+）
3. **Optional禁止**: `Optional[str]` ではなく `str | None` を使用
4. **循環インポート回避**: `TYPE_CHECKING` ブロックを使用

**実装例**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..i18n import LanguageMapping
    from .ability_patterns import AbilityPatternMatcher

class QueryBuilder:
    def __init__(self, mapping: LanguageMapping) -> None:
        self._mapping: LanguageMapping = mapping
        self._pattern_matcher: AbilityPatternMatcher | None = None

    def build(self, parsed: ParsedQuery) -> BuiltQuery:
        """Build Scryfall query from parsed input.

        Parameters
        ----------
        parsed : ParsedQuery
            Parsed user query

        Returns
        -------
        BuiltQuery
            Built query with metadata
        """
        # ... implementation ...
```

**禁止事項**:
```python
# ❌ 型ヒントなし
def process_data(items):
    result = []
    for item in items:
        result.append(item.upper())
    return result

# ❌ typing.Optional使用
from typing import Optional
def get_value() -> Optional[str]:
    pass

# ✅ 正しい実装
def process_data(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        result.append(item.upper())
    return result

def get_value() -> str | None:
    pass
```

### ハンガリアン記法の禁止

**原則**: 変数名に型情報を含めないこと（Hungarian notation禁止）。

**理由**:
- 型ヒントがあれば型情報は不要
- 型名を含む変数名は冗長で可読性を下げる
- 型が変更された際に変数名との不整合が発生

**禁止パターン**:
```python
# ❌ 悪い例: 型名を含む変数名
str_name = "Alice"
int_count = 42
list_items = ["a", "b", "c"]
dict_mapping = {"key": "value"}
bool_is_valid = True

# ✅ 良い例: 型ヒントで型を明示
name: str = "Alice"
count: int = 42
items: list[str] = ["a", "b", "c"]
mapping: dict[str, str] = {"key": "value"}
is_valid: bool = True
```

**例外**:
- ビジネスロジック上で型が意味を持つ場合は許容される
  - 例: `json_data` (JSON形式であることが重要), `html_content` (HTML形式であることが重要)
  - ただし、この場合も型ヒントは必須

### 可読性原則

#### 早期リターンの活用

**原則**: ネストを減らすために早期リターンを使用すること。

**実装例**:
```python
# ❌ 悪い例: 深いネスト
def process_user(user: User | None) -> str:
    if user is not None:
        if user.is_active:
            if user.has_permission("admin"):
                return f"Admin: {user.name}"
            else:
                return f"User: {user.name}"
        else:
            return "Inactive user"
    else:
        return "No user"

# ✅ 良い例: 早期リターン
def process_user(user: User | None) -> str:
    if user is None:
        return "No user"

    if not user.is_active:
        return "Inactive user"

    if user.has_permission("admin"):
        return f"Admin: {user.name}"

    return f"User: {user.name}"
```

#### ネストの深さ制限

**原則**: ネストは最大3レベルまでとすること。

**実装例**:
```python
# ❌ 悪い例: 4レベルのネスト
for user in users:
    if user.is_active:
        for order in user.orders:
            if order.is_paid:
                for item in order.items:
                    # ... 処理 ...

# ✅ 良い例: ヘルパーメソッドで分割
def process_users(users: list[User]) -> None:
    for user in users:
        if user.is_active:
            _process_user_orders(user.orders)

def _process_user_orders(orders: list[Order]) -> None:
    for order in orders:
        if order.is_paid:
            _process_order_items(order.items)

def _process_order_items(items: list[Item]) -> None:
    for item in items:
        # ... 処理 ...
```

#### 明確な変数名

**原則**: 変数名は意図を明確に表現すること。

**ルール**:
- 省略形は避ける（一般的な慣習を除く）
- 単一文字の変数名は避ける（ループカウンタ `i`, `j` は許容）
- ブール値は `is_`, `has_`, `can_` などの接頭辞を使用

**実装例**:
```python
# ❌ 悪い例
def calc(n: int, m: int) -> int:
    tmp = n + m
    res = tmp * 2
    return res

# ✅ 良い例
def calculate_doubled_sum(first_number: int, second_number: int) -> int:
    sum_result = first_number + second_number
    doubled_result = sum_result * 2
    return doubled_result
```

### Single Responsibility Principle (単一責任の原則)

**原則**: 1つの関数は1つの責任のみを持つこと。

**実装例**:
```python
# ❌ 悪い例: 複数の責任を持つ関数
async def execute(arguments: dict[str, Any]) -> list[TextContent]:
    # バリデーション
    request = SearchCardsRequest(**arguments)

    # パイプライン構築
    mapping = get_current_mapping()
    parser = SearchParser(mapping)
    builder = QueryBuilder(mapping)
    presenter = SearchPresenter(mapping)

    # クエリ解析
    parsed = parser.parse(request.query)
    built = builder.build(parsed)

    # フィルタ追加
    if request.format_filter:
        built.scryfall_query += f" f:{request.format_filter}"

    # API呼び出し
    client = await get_client()
    result = await client.search_cards(query=built.scryfall_query)

    # プレゼンテーション
    return presenter.present_results(result, built)

# ✅ 良い例: 責任を分離
async def execute(arguments: dict[str, Any]) -> list[TextContent]:
    """Execute search - orchestration only."""
    request = _validate_request(arguments)
    builder, presenter, built = _build_query_pipeline(request)
    scryfall_query = _add_query_filters(built.scryfall_query, request)
    result = await _execute_api_search(scryfall_query, request)
    search_options = _create_search_options(request)
    return presenter.present_results(result, built, search_options)

@staticmethod
def _validate_request(arguments: dict[str, Any]) -> SearchCardsRequest:
    """Validate and parse request arguments."""
    return SearchCardsRequest(**arguments)

@staticmethod
def _build_query_pipeline(request: SearchCardsRequest) -> tuple[QueryBuilder, SearchPresenter, BuiltQuery]:
    """Build the query processing pipeline."""
    mapping = get_current_mapping()
    parser = SearchParser(mapping)
    builder = QueryBuilder(mapping)
    presenter = SearchPresenter(mapping)
    parsed = parser.parse(request.query)
    built = builder.build(parsed)
    return builder, presenter, built
```

### リファクタリングの実践例

**参考実装**: `src/scryfall_mcp/tools/search.py` のリファクタリング

**Before**: 90行の `CardSearchTool.execute` メソッド
- 複数の責任が混在（バリデーション、パイプライン構築、API呼び出し、エラー処理）
- ネストが深い
- テストが困難

**After**: 26行の `execute` メソッド + 8つのヘルパーメソッド
1. `_validate_request` - リクエストバリデーション
2. `_build_query_pipeline` - パイプライン構築
3. `_add_query_filters` - フィルタ追加
4. `_execute_api_search` - API呼び出し
5. `_handle_api_error` - APIエラー処理
6. `_handle_no_results` - 結果なし処理
7. `_create_search_options` - オプション生成
8. `_handle_unexpected_error` - 予期しないエラー処理

**効果**:
- 各ヘルパーメソッドは単一の責任を持つ
- テスト可能性の向上
- 可読性の大幅な改善
- 保守性の向上

### ドキュメント方針
- **動的情報は記載しない**: テスト数、カバレッジ率、コミットハッシュ、日付などの変動する情報は記載しない
- **理由**: これらの情報はgitログ、テスト実行結果、CIで確認可能。ドキュメントに記載すると更新漏れで陳腐化する
- **例外**: バージョン番号、リリース日などリリースに紐づく情報は記載可
- **OK**: "全テスト合格"、"カバレッジ90%以上を維持"（目標値）
- **NG**: "389テスト合格"、"95%カバレッジ"（具体的な数値）、"2025-10-05"（日付）

## カード表示仕様（MCP出力フォーマット）

### 表示フィールド一覧

MCPツール（`search_cards`）でカード検索結果を返す際、以下のフィールドを表示します：

#### 必須フィールド（常に表示）
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

#### Phase 1追加フィールド（Issue #7対応）

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

### MCP Annotations仕様

すべてのコンテンツに**MCP Annotations**を付与し、クライアント側での適切な表示制御を可能にします。

#### audience フィールドの重要な注意点

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

### 優先度ガイドライン

| フィールド | Priority | 理由 |
|-----------|----------|------|
| カード名、マナコスト、タイプ | 1.0 | 最重要（カード識別に必須） |
| オラクルテキスト、P/T | 0.8 | 高優先度（ゲームプレイに重要） |
| keywords、produced_mana | 0.7 | 高優先度（頻繁に参照） |
| セット、レアリティ、価格 | 0.5 | 中優先度（補助情報） |
| artist、legalities | 0.3-0.5 | 中-低優先度（オプション情報） |

### 実装参照

- 詳細設計: `docs/MCP-OUTPUT-DESIGN-REPORT.md`
- 現在の実装: `src/scryfall_mcp/search/presenter.py`
- データモデル: `src/scryfall_mcp/models.py` (Card: lines 388-476)

## 実装済みアーキテクチャ

### 並行性セーフなロケール管理
```python
# contextvarsベースのスレッドセーフ実装
_current_locale_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default="en"
)

@contextmanager
def use_locale(locale_code: str):
    """リクエスト毎に独立したロケールコンテキスト"""
    token = _current_locale_context.set(locale_code)
    try:
        yield locale_code
    finally:
        _current_locale_context.reset(token)
```

### 2層キャッシュシステム
- **L1 (Memory)**: LRU、最大1000エントリ、インメモリ高速キャッシュ
- **L2 (Redis)**: TTL付き永続化、複数プロセス間共有
- **グレースフルフォールバック**: Redis接続失敗時もメモリキャッシュで継続動作

### 検索パイプライン分離
```
自然言語クエリ → Parser → QueryBuilder → Presenter → MCPレスポンス
                    ↓          ↓           ↓
               ParsedQuery → BuiltQuery → EmbeddedResource
```

### 構造化MCPレスポンス
- **EmbeddedResource**: カードメタデータをJSONで構造化保持
- **カスタムURIスキーマ**: `card://scryfall/{id}` による一意識別
- **MCP標準準拠**: TextContentとEmbeddedResourceのみ使用（ImageContentは非標準のため削除）

### 多言語エラーハンドリング
- **ステータス別対応**: 400/403/429/500+系の詳細ガイダンス
- **実行可能な提案**: クエリ固有の回復方法提示
- **多言語サポート**: 日本語・英語での詳細エラーメッセージ

### ネイティブ多言語カード検索
```python
# 日本語カード名をそのまま Scryfall API に渡す
def _convert_card_names(self, text: str) -> str:
    """Pass card names as-is to Scryfall.

    Scryfall natively supports multilingual card names through
    the printed_name field and lang: parameter.
    """
    return text  # No pre-translation needed

# search.py で言語フィルタを追加
if request.language and request.language != "en":
    scryfall_query += f" lang:{request.language}"

search_result = await client.search_cards(
    query=scryfall_query,
    include_multilingual=True,  # 多言語カードデータを取得
)
```
- **完全カバレッジ**: 全27000+カードを自動サポート
- **メンテナンスフリー**: 新セットの手動登録が不要
- **ネイティブファジーマッチング**: Scryfallの高精度検索を活用

## ブランチ別の主要な改善

### feature/issue#7-add-missing-card-fields (2025-10-17)

#### Phase 1-3: Issue #7対応 - 追加カードフィールドの実装
**実装内容**:
- **Phase 1**: キーワード能力、アーティスト、マナ生成フィールドの追加
  - `keywords`, `artist`, `produced_mana` フィールドのサポート
  - デフォルトでON、`SearchOptions`で制御可能
  - 土地カード専用の`produced_mana`表示ロジック

- **Phase 2**: MCP Annotations対応
  - すべてのコンテンツに`Annotations`を付与
  - `audience`と`priority`による表示制御
  - TextContent（ユーザー向け）とEmbeddedResource（アシスタント向け）の適切な使い分け

- **Phase 3**: フォーマット適格性情報の追加
  - `include_legalities`パラメータによるオプトイン表示
  - `format_filter`指定時の自動表示
  - `not_legal`を除外したコンパクトな表示

**テスト**:
- 全510テスト成功、97%カバレッジ達成
- Phase 1-3の全機能を網羅する統合テスト追加

#### コード品質改善 (2025-10-17)
**実施内容**:
- **型アノテーション修正**: 5つの`__init__`メソッドに`-> None`を追加
- **docstring形式統一**: Google Style → NumPy Style変換（1箇所）
- **docstring型表記更新**: 30+箇所で`type, optional` → `type | None, optional (default: value)`
- **リント・フォーマット**: ruff check/format で2エラー修正、6ファイル再フォーマット
- **型チェック**: mypy --strict で全29ファイル合格

**品質チェック結果**:
- ✅ ruff check: 全ファイル合格
- ✅ ruff format: 統一フォーマット適用済み
- ✅ mypy --strict: 型エラー0件
- ✅ pytest: 510テスト成功、97%カバレッジ

#### MCP Annotations UI表示問題の修正 (2025-10-17)
**問題**: アーティスト名がJSONメタデータには含まれるが、Claude Desktop ChatUIに表示されない

**原因調査**:
1. `docs/MCP-OUTPUT-DESIGN-REPORT.md`からMCP仕様を調査
2. `audience=["user"]`の動作が仕様と実装で異なることを発見
3. MCP仕様: "UIに表示される"
4. 実際の動作: "UIに表示される**可能性がある**が保証されない"

**実装済み解決策**:
- `presenter.py:302-305`: `audience=["user"]` → `audience=["user", "assistant"]`
- これにより**UIとLLMコンテキストの両方に確実に表示**
- テストケース更新: 2箇所で期待値を`["user", "assistant"]`に修正

**修正ファイル**:
```python
# src/scryfall_mcp/search/presenter.py (lines 302-305)
annotations = Annotations(
    audience=["user", "assistant"],  # UIとLLM両方に確実に表示
    priority=PRIORITY_USER_CONTENT
)

# tests/search/test_presenter.py (lines 866, 1065)
assert card_text.annotations.audience == ["user", "assistant"]
```

**テスト結果**:
- presenter tests: 58/58 成功
- 全テスト: 510/510 成功
- カバレッジ: 97%維持

**推奨事項**:
- ユーザー向けコンテンツ（カード情報、エラーメッセージ等）は常に`audience=["user", "assistant"]`を使用
- 構造化メタデータ（EmbeddedResource）のみ`audience=["assistant"]`を使用
- `audience=["user"]`は使用しない（表示保証なし）

## v0.1.0での主要な改善

### セキュリティ強化（2025-10-04）

#### User-Agent設定
**実装内容**:

**主要な設定方法（MCP使用時）**: 環境変数
- Claude DesktopなどのMCPクライアントでは、`claude_desktop_config.json`の`env`セクションで設定
- 環境変数名: `SCRYFALL_MCP_USER_AGENT`
- 形式: `"YourApp/1.0 (your-email@example.com)"` または `"YourApp/1.0 (https://github.com/username/repo)"`
- 設定なしでツール呼び出し時、設定手順を含むメッセージを表示

**設定ウィザード（CLI使用時）**: 対話式セットアップ
- スタンドアローン実行時のみ使用
- メールアドレス・HTTPS URLのバリデーション
- プラットフォーム固有の設定ディレクトリ
  - macOS: `~/Library/Application Support/scryfall-mcp/`
  - Linux: `~/.config/scryfall-mcp/`
  - Windows: `%APPDATA%\Local\scryfall-mcp\`
- CLIコマンド: `setup`, `config`, `reset`, `--help` （非推奨：MCP使用時は環境変数を推奨）

#### PII保護とファイルパーミッション
**実装済みセキュリティ対策**:
- 設定ディレクトリ: `mode=0o700` (所有者のみアクセス可能)
- 設定ファイル: `chmod(0o600)` (所有者のみ読み書き可能)
- User-Agent検証:
  - 空白文字・プレースホルダー値（"setup-recommended"）のバリデーション
  - `is_user_agent_configured()` ヘルパー関数
- ツールレベルでの検証:
  - `search_cards` 実行時にUser-Agent設定を確認
  - 未設定時は環境変数設定手順を含むエラーメッセージを返却
- 機密情報のログ出力防止:
  - Redis認証情報・連絡先情報を含む設定のログ出力を削除
  - 必要最小限の情報のみログに記録

```python
# tools/search.py - ツールレベルでの検証
async def execute(arguments: dict[str, Any]) -> list[TextContent | EmbeddedResource]:
    # Check if User-Agent is configured before allowing search
    if not is_user_agent_configured():
        config_message = (
            "⚠️ **User-Agent Configuration Required**\n\n"
            "Before searching for cards, you need to configure your contact information "
            "for Scryfall API compliance.\n\n"
            "**Please add the following to your Claude Desktop configuration:**\n\n"
            # ... 設定手順を詳細に表示 ...
        )
        return [TextContent(type="text", text=config_message)]

# settings.py - 検証ヘルパー
def is_user_agent_configured() -> bool:
    """Check if User-Agent has been properly configured."""
    settings = get_settings()
    user_agent = settings.user_agent.strip() if settings.user_agent else ""

    if not user_agent or "setup-recommended" in user_agent.lower():
        return False

    return True
```

### MCP仕様準拠とプロトコル修正

#### Critical: Lifespan Context Manager修正
**問題**: FastMCPがlifespanコンテキストマネージャーに`app`引数を渡すが、実装が受け取っていなかった。
```
TypeError: _create_lifespan() takes 0 positional arguments but 1 was given
```

**実装済み解決策**:
- `_create_lifespan(app: FastMCP) -> AsyncIterator[None]` に修正
- FastMCPのlifespanプロトコルに準拠
- サーバーが正常にstdioモードで起動可能に

#### MCP Content型の構造化出力（Critical修正完了）
**問題**: ツールがMCP Content型を文字列に変換していた。また、ImageContentがMCP仕様に存在しない。

**実装済み解決策**:
- ツールが直接`list[TextContent | EmbeddedResource]`を返すように修正
- **ImageContent削除**: MCP仕様に存在しないため削除（v0.1.0破壊的変更）
- 画像データの代わりに画像URLをtext内に含める
- MCPプロトコル準拠の構造化データ出力
- `tests/integration/test_mcp_content_validation.py`で検証完了

#### FastMCP Context注入
**追加機能**:
- 全ツールに`Context`パラメータを追加
- `ctx.info()`: ログ出力
- `ctx.report_progress()`: 進捗報告
- `ctx.error()`: エラーログ
- より良い可観測性とユーザーフィードバック

#### Asynccontextmanagerベースのライフサイクル管理
**実装完了**:
```python
@asynccontextmanager
async def _create_lifespan(app: FastMCP) -> AsyncIterator[None]:
    """Lifecycle manager for the MCP server."""
    # Startup
    detected_locale = detect_and_set_locale()
    logger.info("Detected and set locale: %s", detected_locale)

    try:
        yield
    finally:
        # Shutdown/cleanup
        await close_client()
        logger.info("Scryfall MCP Server stopped")
```
- 起動/シャットダウンロジックの一元化
- リソースの適切なクリーンアップ
- FastMCPのlifespanプロトコルに準拠

#### Cache TTL Scryfall推奨値対応
**問題**: キャッシュTTLが30分/1時間（Scryfall推奨は最低24時間）

**実装済み解決策**:
- `cache_ttl_search`: 30分 → 86400秒（24時間）
- `cache_ttl_default`: 1時間 → 86400秒（24時間）
- Scryfall APIガイドライン準拠

#### RateLimiterのスレッドセーフ化
**問題**: 共有状態が保護されておらず、並行リクエストでレート制限違反の可能性。

**実装済み解決策**:
```python
def __init__(self):
    self._lock = asyncio.Lock()  # 共有状態を保護

async def acquire(self) -> None:
    async with self._lock:
        # レート制限ロジック
```

#### MCP統合テスト追加
**新規テスト**: `tests/integration/test_mcp_content_validation.py`
- TextContent構造検証（`type: "text"`, `text: str`）
- EmbeddedResource構造検証（`type: "resource"`, `resource: dict`）
- ImageContent非存在の検証（MCP仕様準拠確認）
- エラーレスポンスの検証
- 全389テスト成功、カバレッジ95%達成

### テストカバレッジの向上（2025-10-03）
**問題**: Codex分析により、リクエストモデルとバリデーション周りのテストカバレッジ不足が判明。

**実装済み解決策**:
- リクエストモデル（SearchCardsRequest、AutocompleteRequest）の包括的テストを追加
- バリデーションテスト追加:
  - URL検証（ImageUris、Card）
  - 境界値検証（max_results: 1-175）
  - ネストされた構造の検証
  - 必須フィールドの検証
- 全389テスト成功、カバレッジ向上

### 定数の分離
**問題**: settings.pyに実行時設定と静的な語彙データが混在し、モジュールの責務が不明瞭。

**実装済み解決策**:
- `src/scryfall_mcp/i18n/constants.py` を新規作成
- 分離した定数:
  - `SCRYFALL_KEYWORDS` - 検索構文キーワード
  - `MAGIC_COLORS` - 色コード (WUBRG)
  - `MAGIC_TYPES` - カードタイプとサブタイプ
  - `SEARCH_PATTERNS` - 正規表現パターン
- `settings.py` は実行時設定のみに集中
- モジュールの責務が明確化

## 設計課題と実装状況

### 1. 並行性の問題（完了）
**問題**: グローバルなロケール管理により、並行リクエスト間で言語設定が干渉。

**実装済み解決策**:
- `contextvars`を使用したコンテキストスコープのロケール管理
- `src/scryfall_mcp/i18n/locales.py` で実装完了
- `use_locale()` コンテキストマネージャーによるスレッドセーフな言語設定
```python
@contextmanager
def use_locale(locale_code: str):
    """Context manager for setting locale in current context."""
    token = _current_locale_context.set(locale_code)
    try:
        yield locale_code
    finally:
        _current_locale_context.reset(token)
```

### 2. 責任の混在（完了）
**問題**: `CardSearchTool.execute`メソッドに複数の責任が集中。

**実装済み解決策**:
- パーサー → クエリビルダー → プレゼンターのパイプライン分離
- `src/scryfall_mcp/search/` モジュールで実装完了
  - `parser.py`: 自然言語解析
  - `builder.py`: Scryfallクエリ構築
  - `presenter.py`: MCP出力フォーマット
  - `models.py`: データモデル定義

### 3. 未実装のキャッシュシステム（完了）
**以前の問題**: 設定にキャッシュ項目はあるが実装は空。

**実装済み解決策**:
- メモリ + Redis の2層キャッシュシステム実装完了
- `src/scryfall_mcp/cache/` モジュールで実装完了
  - `backends.py`: Memory/Redis/Composite cache実装
  - `manager.py`: キャッシュマネージャーとファクトリー
- 設定済みTTL（検索結果30分、カード詳細24時間、オートコンプリート15分）
- Redis接続失敗時のグレースフルフォールバック

### 4. 静的な日本語マッピング（完了）
**以前の問題**:
- 日本語カード名辞書は40カードのみ（全27000カードの0.15%）。
- 新カードへの対応が手動で困難。
- Scryfallのネイティブ多言語機能を活用していなかった。

**実装済み解決策**:
- カード名の事前翻訳を廃止し、日本語のまま Scryfall API に渡す方式に変更
- `lang:` パラメータによる言語フィルタリングを追加
- `include_multilingual=True` で多言語カードデータを取得
- Scryfallの `printed_name` フィールドとネイティブファジーマッチングを活用
- 完全なカードカバレッジ（全27000+カード対応）、メンテナンスフリー

### 5. MCP機能の未活用（完了）
**問題**: fastmcpの豊富なコンテンツタイプが文字列に変換される。

**実装済み解決策**:
- 構造化MCPレスポンスの実装完了
- `EmbeddedResource`によるメタデータ保持
- カスタムURIスキーマ（`card://scryfall/{id}`）による構造化データ
- TextContentとEmbeddedResourceの適切な使い分け
- **ImageContent削除**: MCP仕様に存在しないため削除（画像URLで代替）

### 6. エラーハンドリング強化（完了）
**実装済み解決策**:
- ステータス別詳細エラー情報（400/403/429/500+系）
- 日本語・英語両方での実行可能なガイダンス
- `src/scryfall_mcp/errors/` モジュールで実装完了
- クエリ固有の回復提案機能

### 7. MCPエラーハンドリングのベストプラクティス

#### エラーメッセージの簡潔性
**問題**: 長すぎるエラーメッセージがClaude Desktop側で適切に表示されない

**実装済み解決策**:
- User-Agent未設定エラーを簡潔なフォーマットに変更
- 冗長な説明を削除し、必要最小限の情報に絞る
- 箇条書きと明確なセクション分けで可読性向上

**MCPツールからのエラー返却の原則**:
```python
# ❌ 悪い例: 長すぎる説明
config_message = (
    "詳細な背景説明が何段落も続く...\n"
    "さらに追加の説明...\n"
    "なぜこれが必要か、さらに詳しく...\n"
    "歴史的な背景...\n"
    # 合計30行以上の説明
)

# 良い例: 簡潔で実用的、ポジティブなトーン
config_message = (
    "🔧 **Scryfall API 初回セットアップ**\n\n"
    "Scryfall APIをご利用いただくには、以下の設定を行ってください：\n\n"
    "**1. Claude Desktop設定ファイルを開く**\n"
    "- macOS/Linux: `~/Library/Application Support/Claude/claude_desktop_config.json`\n"
    "- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`\n\n"
    "**2. 以下の内容を追加**\n"
    "```json\n{...}\n```\n\n"
    "**3. プレースホルダーを実際の値に置き換え**\n"
    "**4. Claude Desktopを再起動**\n\n"
    "設定完了後、再度カード検索をお試しください。\n\n"
    "詳細情報: https://scryfall.com/docs/api"
)
```

#### メッセージトーンの重要性
**問題**: ⚠️マークや「必要です」などのエラートーンがClaude Desktop側で「ツールエラー」として認識され、チャットインターフェースに表示されない

**実装済み解決策**:
- エラートーン（⚠️、「〜が必要です」）→ セットアップガイドトーン（🔧、「〜を行ってください」）
- 「User-Agent設定が必要です」→ 「Scryfall API 初回セットアップ」
- ネガティブな表現を避け、ポジティブで前向きなガイドとして提示

**理由**:
- MCPクライアント（Claude Desktop）はメッセージのトーンから「エラー」か「正常な応答」かを判断
- エラーと判断されると、ツールレスポンスではなく汎用エラーメッセージが表示される
- セットアップガイドのトーンにすることで、正常な応答として認識され、チャットに表示される

#### TextContentの適切な使用
**実装内容**:
- すべてのエラーは`TextContent(type="text", text=message)`形式で返却
- エラーメッセージは必ず`list[TextContent]`として返す
- 例外をraiseせず、常に構造化レスポンスを返す

**理由**:
- MCPクライアント（Claude Desktop）は構造化レスポンスを期待
- 例外をraiseすると、クライアント側で「ツールの設定に問題があります」という一般的なエラーになる
- TextContentで返すことで、ユーザーに具体的なガイダンスを提供可能

#### ChatUI表示の問題と試したアプローチ
**問題**: ツールからTextContent返却しても、Claude Desktop ChatUIに表示されない

**試したアプローチ**:
1. **`ctx.info()` + TextContent** - 通知メッセージとツールレスポンスの両方を送信
   - 結果: MCPプロトコルレベルでは正しく送信されるが、ChatUIに表示されず
   - `ctx.info()`は`notifications/message`として送信される

2. **プレーン文字列の返却** - `list[TextContent]`の代わりに`str`を返却
   - FastMCPが自動的にTextContentに変換
   - 戻り値の型: `str | list[TextContent | ...]`
   - 実装: `return setup_guide` (文字列)
   - 統合テストでは正しく動作（"Received 1 content items"）

3. **MCPプロンプトの実装** - ツールではなくプロンプトとしてセットアップガイドを提供
   - ユーザーが明示的に呼び出す形式
   - `@app.prompt()`デコレーターを使用
   - ChatUIでプロンプトとして表示される（クライアント依存）
   - 実装: `_setup_prompts()`メソッドで`scryfall_setup`プロンプトを登録

**現在の実装**:
```python
# server.py - search_cards tool
if not is_user_agent_configured():
    setup_guide = "🔧 **Scryfall API 初回セットアップ**\n\n..."
    await ctx.info(setup_guide)  # 通知送信
    return setup_guide  # 文字列返却（FastMCPがTextContentに変換）

# server.py - scryfall_setup prompt
def _setup_prompts(self) -> None:
    """Set up MCP prompts using fastmcp decorators."""

    @self.app.prompt()
    def scryfall_setup() -> str:
        """Scryfall API setup guide for User-Agent configuration."""
        return (
            "🔧 **Scryfall API 初回セットアップ**\n\n"
            "Scryfall APIをご利用いただくには、以下の設定を行ってください：\n\n"
            # ... setup instructions ...
        )
```

4. **最終解決策: エラー + Resource** - エラーでChatUIに表示し、Resourceで詳細情報を提供
   - User-Agent未設定時にValueErrorを投げてChatUIに表示
   - MCP ResourceとしてセットアップガイドをResource URIで公開
   - エラーメッセージにResource URI `scryfall://setup-guide` への参照を含める

**最終実装** (2025-10-06):
```python
# server.py - _setup_resources()メソッド
@self.app.resource("scryfall://setup-guide")
def get_setup_guide() -> str:
    """Scryfall API setup guide for User-Agent configuration."""
    return "🔧 **Scryfall API 初回セットアップ**\n\n..."

# server.py - search_cards tool
if not is_user_agent_configured():
    error_message = (
        "❌ **User-Agent が設定されていません**\n\n"
        "詳細なセットアップガイド: MCP Resourcesから `scryfall://setup-guide` を参照\n"
        "または、以下の手順で設定してください：\n"
        # ... 簡潔なセットアップ手順 ...
    )
    await ctx.error(error_message)
    raise ValueError(error_message)  # エラーはChatUIに表示される
```

**アプローチの比較**:
- **ツールからの返却** (アプローチ1, 2): ツール実行時に自動表示されるが、ChatUIに表示されない
- **プロンプト** (アプローチ3): ユーザーが明示的に呼び出す必要あり、プロンプトUIで表示される
- **エラー + Resource** (アプローチ4): エラーはChatUIに確実に表示され、ResourceでUI非依存の詳細情報を提供

**テスト**:
- `test_search_cards_without_user_agent`: User-Agent未設定時にValueErrorが投げられることを確認
- `test_scryfall_setup_prompt_registration`: プロンプト登録の確認
- `test_scryfall_setup_prompt_execution`: プロンプト実行結果の検証
- `test_scryfall_setup_resource_registration`: Resource登録の確認
- `test_scryfall_setup_resource_execution`: Resource取得結果の検証

#### 参考情報
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP仕様: https://modelcontextprotocol.io/
- MCP Prompts仕様: https://modelcontextprotocol.io/specification/server/prompts
- FastMCP: https://github.com/jlowin/fastmcp

**レッスン**:
1. MCPツールの正常な返り値はClaude Desktop ChatUIに表示されない場合がある
2. エラー（例外）はChatUIに確実に表示される
3. MCP Resourcesは永続的な情報提供に適している（ドキュメント、設定ガイドなど）
4. **推奨パターン**: 設定必須項目が欠けている場合は、エラーを投げてChatUIに表示し、Resource URIで詳細情報へのアクセスを提供する

## 必要な追加技術・機能

### 観測可能性
- 構造化ログ、メトリクス、トレーシング
- API呼び出しとレート制限状態の監視
- 運用者がScryfall制限接近を把握可能

### Redis統合
- 現在は依存関係に含まれているが実装なし
- 設定検証とヘルスチェック追加
- または実装まで依存関係から削除

### エラーハンドリング強化
- ステータス別（429 vs 5xx）の詳細エラー情報
- 日本語・英語両方での実行可能なガイダンス
- 部分応答の回避

### 運用機能
- グレースフルシャットダウン
- レディネスプローブ
- キャッシュのウォームアップとリロード機能

## コード品質チェックリスト

### 必須実行コマンド
```bash
# リント・フォーマット
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# 型チェック（STRICT mode）
uv run mypy src/

# テスト（カバレッジ95%目標）
uv run pytest --cov=scryfall_mcp --cov-report=term-missing
```

### テスト方針
- Scryfall APIはモック化必須
- 非同期処理はpytest-asyncio使用
- 並行性テストを含む多言語検索の回帰テスト

## セキュリティガイドライン

- 環境変数で機密情報管理
- 入力値サニタイズ必須
- ログに個人情報・APIキー出力禁止
- Wizards of the Coastファンコンテンツポリシー遵守

## 開発優先順位

### 完了済み
**High Priority タスク（すべて完了）**
- 並行ロケール管理の修正（contextvarsベース）
- キャッシュシステムの実装（2層キャッシュ）
- 構造化MCPレスポンス対応（EmbeddedResource）
- 日本語カード名検索のアーキテクチャ改善（Scryfallネイティブサポート活用）

**Medium Priority タスク（すべて完了）**
- 検索ツールの責任分離（Parser → QueryBuilder → Presenter）
- エラーハンドリング強化（ステータス別多言語対応）

### 残存タスク

1. **Medium Priority**
   - 観測可能性の追加（構造化ログ、メトリクス、トレーシング）

2. **Low Priority**
   - 日本語NLP強化（トークナイザー統合、ベクター検索）
   - Redis統合完成（ヘルスチェック、設定検証）
   - 運用管理機能（グレースフルシャットダウン、レディネスプローブ）

このドキュメントは定期的に更新し、設計決定と技術的負債の現状を反映させること。