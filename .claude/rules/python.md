---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Python モダン開発 Rules（Scryfall MCP Server）

Scryfall MCP Server の Python 実装の細則。**人間と Claude の両方**が従う。プロジェクト固有の方針（Scryfall API 制約・MCP 出力仕様・セキュリティ）は [coding.md](coding.md) が正本で、本書は**言語・ツール・設計の細則**を担う（重複させない）。

> 出典：Astral公式（docs.astral.sh）、Real Python、PEP 484/526/585、Effective Python（Brett Slatkin）。📘 印は Effective Python 由来の Pythonic な設計原則。

## 0. このプロジェクトの確定事項（参考文献より優先）

- **lint＋整形＝Ruff 一本**（決定）。`ruff check`（lint・import順の整列を含む）と `ruff format`（整形）。Black / isort は導入しない（Ruff と重複するため）。lint ルールの選択・除外は `pyproject.toml` の `[tool.ruff.lint]` が正本。
- **型チェッカ＝mypy --strict**（決定）。`pyproject.toml` の `[tool.mypy]` で strict 有効。basedpyright / pyright は不採用。
- **Python 3.12**（`requires-python >= 3.12`）。`target-version = "py312"`。
- **パッケージ構成＝`src/scryfall_mcp/`（src layout）**（決定）。PyPA の src layout に従い、エントリポイントは `[project.scripts]` の `scryfall-mcp`。テストは最上位 `tests/`。内部の層分けはパッケージ内サブパッケージ（`api/` `auth/` `cache/` `search/` `i18n/` `tools/` `resources/` `errors/`）で行う。
- **設定は `settings.py`（pydantic-settings）に集約**。env（`SCRYFALL_MCP_*`）／デフォルトを型付きで統合。静的な語彙定数（キーワード・色・タイプ・正規表現）は `i18n/constants.py` に分離し、settings は実行時設定のみに集中する。**可変のグローバル変数（`global` 文）は原則禁止**（シングルトンファクトリ `get_settings()` 等の遅延初期化は許容）。
- **データモデルは各層の `models.py` が正本**（`api/models.py`＝Scryfall エンティティ、`search/models.py`＝パイプライン DTO、`i18n/models.py`＝言語マッピング、`cache/models.py`）。ルート `models.py` は MCP 境界のリクエストモデル＋後方互換の再エクスポート façade で、新しいモデルは所属する層に定義する。層内からは `.models`（層相対）で import し、ルート façade を経由しない（循環防止）。

## 1. ツールチェーン

- **パッケージ・環境管理は `uv` を単一の真実の源**。pip / virtualenv / poetry を混在させない。
  - 依存追加 `uv add <pkg>`、開発依存 `uv add --dev <pkg>`、実行 `uv run <cmd>`（手動 activate 不要）。
  - `uv.lock` はコミットし手動編集しない。
  - オプショナル依存（redis / aws）は `[project.optional-dependencies]` で管理し、通常依存に混ぜない。import は遅延＋フォールバック（Redis 未導入でもメモリキャッシュで動く）。
- **lint**：`uv run ruff check src/ tests/ --fix`
- **整形**：`uv run ruff format src/ tests/`
- **型**：`uv run mypy src/`（strict）
- **テスト**：`uv run pytest --cov=scryfall_mcp --cov-report=term-missing`（カバレッジ95%目標）
- **セキュリティ**：`uv run bandit -c pyproject.toml -r src/`（セキュリティが関わる変更＝認証・設定・ログ出力のときに回す。CI では毎回実行）

## 2. プロジェクト構成

- **設定は `pyproject.toml` に集約**（setup.py / setup.cfg / mypy.ini を新設しない）：`[project]` / `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]` / `[tool.coverage.*]`。
- ディレクトリ構造・モジュール責務の詳細は [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md)。

## 3. 型ヒント（必須）

- 公開API・重要ロジックには**必ず型ヒント**。型はドキュメントでなく補完・静的解析・実行時検証の基盤。
  - 注：強制手段は **mypy --strict（対象は `src/` のみ）**。ruff の ANN 系ルールは大半を ignore しているため、lint では型ヒント欠落を検出しない。`tests/` は型チェック対象外だが型ヒントを推奨。
- **モダン記法**：`X | None`（`Optional` 不可）、`list[int]` / `dict[str, int]`（`typing.List` 等不可）、ユニオンは `int | str`。必要に応じ `from __future__ import annotations`。
- **循環インポート回避**：`TYPE_CHECKING` ブロックでクラス間の相互参照を解決。
- **構造的部分型は `Protocol`**（継承を強制しない）。継承を強制したいときのみ ABC。
- **`Any` は最小限**。動的データ（Scryfall JSON 等）は早期に Pydantic モデルへナローイング。
- **構造化データ**：TypedDict → dataclass → Pydantic を用途で使い分け、実行時バリデーション（外部API応答・ツールI/O）が要るなら Pydantic。
- 📘 辞書ネストやタプル多用で複雑化したら、その場しのぎをやめ **dataclass 等にリファクタ**して意図と型を明示。
- **ハンガリアン記法禁止**：変数名に型情報を含めない（`str_name` / `list_items` 不可）。例外：ビジネスロジック上で型が意味を持つ場合（`json_data`, `html_content`）は許容されるが型ヒントは必須。

## 4. アーキテクチャ・設計

- **コアを純粋に保つ（Ports & Adapters）**。中核ロジック（クエリ構築・結果整形・言語判定）は**純粋関数＋データクラス**に閉じ、フレームワークや I/O を知らないこと。副作用（HTTP・Redis・ファイル）は外側のシェル層へ。
  - 本プロジェクトでは検索パイプライン Parser → QueryBuilder → Presenter を決定論的に保ち、Scryfall / キャッシュへの I/O（`api/` `cache/`）と分離する。
- **責務でモジュール分割**。巨大モジュールを避ける（api / auth / cache / search / i18n / tools / resources / errors）。
- **単一責任の原則**：1つの関数は1つの責任のみ。複数の責任を持つ長大な関数は、責任ごとにヘルパーメソッドへ分割し、メイン関数はオーケストレーションのみを行う（実例：`tools/search.py` の `execute` = 90行 → 26行＋8ヘルパー）。
- 📘 **戻り値設計**：戻り値が4つ以上なら**専用の結果オブジェクト（dataclass 等）**を返す。**特殊状態を `None` で表さず例外**を送出。ただし MCP ツールの「該当なし」は例外でなく**分かりやすいメッセージ**で返す（→ [coding.md](coding.md)）。
- 📘 **例外は階層設計**：ルート独自例外（`errors/`）から派生させる。呼び出し側が対処できる粒度で投げる。
- 📘 **リソースは必ず `with` / `async with`（コンテキストマネージャ）**。
- **並行性セーフな状態管理**：リクエスト毎に変わる状態（ロケール等）はグローバル変数でなく **`contextvars`** で持つ（実例：`i18n/locales.py` の `use_locale()`）。

## 5. FastMCP（サーバー層の規約）

> 「フレームワークを使う外側のシェル層」の規約。§4「コアはフレームワークを知らない」を破らない。

- **ツール関数は薄く**：受付・バリデーション・整形に専念し、検索ロジックは `search/` のサービス層へ。
- **ライフサイクルは lifespan**：起動時の初期化（ロケール検出）・終了時のクリーンアップ（`close_client()`）は `@asynccontextmanager` の lifespan に集約。FastMCP のプロトコルに従い **`app` 引数を受け取る**（`_create_lifespan(app: FastMCP)`）。
- **Pydantic v2 を全面活用**：ツール I/O・設定・バリデーション。
- **`async` を惰性で全付与しない**：`await` する非同期 I/O（Scryfall 呼び出し等）がある時だけ `async def`。同期ブロッキングはイベントループを止めない（`asyncio.to_thread` 等）。
- **共有状態の保護**：レートリミッタ等、並行リクエストが触る共有状態は `asyncio.Lock` で守る。
- **stdio transport では stdout に print しない**（プロトコルが壊れる）。ログは標準 `logging`（`logger = logging.getLogger(__name__)`）で stderr へ。
- MCP 出力の型・エラーの返し方は [coding.md](coding.md)、表示フィールド・annotations・priority の正本は [docs/CARD-DISPLAY-SPEC.md](../../docs/CARD-DISPLAY-SPEC.md)。
- ⚠ AI 支援は全ツールを安易に `async` 化／グローバル変数での依存持ち回し／Pydantic v1 記法を生成しがち。明示的に矯正する。

## 6. コーディング規約

### 基本スタイル

- **PEP 8**（4スペース、関数 snake_case、クラス PascalCase、定数 UPPER、private は `_` 前置）。整形は Ruff formatter に任せ人手で議論しない。
- **f-string を標準**（`%` / `.format()` 不可）。デバッグは `f"{value=}"`。
- **`pathlib.Path`**（`os.path` 不可）。
- **データ保持は `dataclass` / Pydantic**（`__init__` / `__repr__` / `__eq__` を手書きしない）。
- **import 順は Ruff(isort) に従う**。パッケージ内は既存コードの流儀（相対 import）に合わせて一貫させる。
- **docstring は NumPy style**。各公開関数・クラス・モジュールに必須。型表記は `type | None, optional (default: value)` 形式。
- **自己文書化を優先**：命名と構造で意図を表す。コメントは「why」を書き「what」を繰り返さない。

### 可読性

- **関数は50行以内**を目安に分割（超えたら単一責任の原則でヘルパーへ）。linter による強制はない（PLR0912/PLR0915 は ignore 済み）ため、レビューで確認する**目安（advisory）**。既存の長大関数は触るときに分割を検討する。
- **早期リターンでネストを減らす**。ネストは最大3レベル（`for` / `if` / `with` / `match` を合算）。
- **明確な変数名**：省略形は一般的な慣習（`db`, `id`, `url`, `api`, `http`）を除き避ける。単一文字はループカウンタ `i`, `j` のみ。ブール値は `is_` / `has_` / `can_` 接頭辞。

### 📘 Pythonic な書き方（Effective Python)

- 複雑な式を1行に詰めない（ヘルパーへ抽出）。`match` は分割代入を伴う分岐に限る。
- 手動インデックスより `enumerate`、複数イテラブルは `zip`。
- 辞書の欠損キーは `get` / `setdefault` / `defaultdict` を使い分け。
- `map` / `filter` より内包表記。ただし3段以上ネストする内包表記は通常ループに展開。
- **可変デフォルト引数の罠**：デフォルトに `[]` / `{}` を使わず `None` を番兵に。
- 単純なインターフェースはクラスより関数を受け取る（第一級オブジェクト）。多重継承は慎重に。

## 7. 並行性・性能（📘 Effective Python）

- **用途で使い分け**：ブロッキング I/O は `asyncio`（Scryfall は httpx async）、CPU バウンドはイベントループ外へ（`asyncio.to_thread`）。GIL で計算はスレッド並列化されない。
- **推測でなく計測**：`cProfile` でホットスポット特定 → 改善 → 再計測。

## 8. 運用・品質

- **テストは pytest のフィクスチャ**で前提を整え、外部依存（Scryfall・Redis）を**必ずモック分離**（実 API を叩かない）。非同期テストは pytest-asyncio（`asyncio_mode = "auto"`）。
- 多言語検索（日本語カード名・全角半角・表記ゆれ）と並行性（contextvars ロケール）の回帰テストを維持する。
- **ログを入れる**（どのクエリで・何件返し・何 ms かかったか）。機密情報（User-Agent の連絡先・Redis 認証情報）はログに出さない（→ [coding.md](coding.md)）。
- **CI でリント・型チェック・テストを必須化**（基準未達はマージ不可）。

## 9. 一次情報

- uv: https://docs.astral.sh/uv/ ／ Ruff: https://docs.astral.sh/ruff/ ／ mypy: https://mypy.readthedocs.io/
- FastMCP: https://gofastmcp.com/ ／ MCP仕様: https://modelcontextprotocol.io/
- Scryfall API: https://scryfall.com/docs/api
- PEP 484 / PEP 526 / PEP 585 ／ Effective Python: https://effectivepython.com/
