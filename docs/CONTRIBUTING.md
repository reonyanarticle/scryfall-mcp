# コントリビューションガイドライン

Scryfall MCP Serverへのコントリビューションをご検討いただきありがとうございます。
このドキュメントでは、プルリクエスト（PR）の作成方法と受け付けルールを説明します。

## 目次

- [プルリクエストの受け付けルール](#プルリクエストの受け付けルール)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [コーディング規約](#コーディング規約)
- [プルリクエストの作成手順](#プルリクエストの作成手順)
- [レビュープロセス](#レビュープロセス)

## プルリクエストの受け付けルール

### 必須要件

プルリクエストが受け付けられるためには、以下の要件を満たす必要があります。

#### 1. テストの合格

- **全テストが合格していること**: `uv run pytest` で全389テストがパスすること
- **カバレッジ要件**: 新規コードのテストカバレッジは最低90%以上
- **型チェック**: `uv run mypy src` がエラーなく完了すること
- **リンター**: `uv run ruff check src tests` がエラーなく完了すること

#### 2. コード品質

- **型アノテーション**: すべての関数・メソッドに型ヒントが必須
- **Docstring**: NumPy styleのdocstringが必須
- **コーディング規約**: `CLAUDE.md` のコーディング規約に準拠すること

#### 3. ドキュメント

- **機能追加**: 新機能の場合は `docs/` 配下に詳細ドキュメントを追加
- **README更新**: ユーザー向け機能の場合はREADME.mdを更新
- **AGENT.md更新**: 開発者向け設計変更の場合はAGENT.mdを更新

#### 4. コミットメッセージ

- **簡潔で明確**: 変更内容を1行で要約
- **詳細説明**: コミットボディに変更理由と影響範囲を記載
- **日本語または英語**: どちらでも可

例:
```
Add environment variable configuration for User-Agent

Implements Scryfall API requirement for contact information.
Users configure contact info via SCRYFALL_MCP_USER_AGENT environment variable.

Features:
- Environment variable configuration in Claude Desktop config
- Tools prompt for configuration when not set
- Validation and helpful error messages

All 389 tests passing ✅ (94% coverage)
```

#### 5. CI/CDの合格

- **GitHub Actions**: すべてのワークフローがパスすること
  - Tests (Python 3.11, 3.12, 3.13)
  - MCP Integration Tests
  - MCP Inspector Compatibility
  - Security Scan

### 推奨事項

以下は必須ではありませんが、推奨される項目です。

- **小さなPR**: 1つのPRで1つの機能または修正に集中
- **説明的なPR**: PRの説明欄に変更内容、動機、テスト方法を記載
- **Issue参照**: 関連するIssueがある場合は `Fixes #123` の形式で参照
- **スクリーンショット**: UIや出力に変更がある場合はスクリーンショットを添付

## 開発環境のセットアップ

### 前提条件

- Python 3.11以上
- uv (パッケージマネージャー)
- Git

### セットアップ手順

```bash
# リポジトリのクローン
git clone https://github.com/reonyanarticle/scryfall-mcp.git
cd scryfall-mcp

# 依存関係のインストール
uv sync

# 開発ブランチの作成
git checkout -b feature/your-feature-name

# User-Agent設定（環境変数）
export SCRYFALL_MCP_USER_AGENT="DevApp/1.0 (your-email@example.com)"
```

### 開発ツールの実行

```bash
# テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=scryfall_mcp

# 型チェック
uv run mypy src

# リント
uv run ruff check src tests

# フォーマット
uv run ruff format src tests
```

## コーディング規約

詳細は [`CLAUDE.md`](../CLAUDE.md) を参照してください。

### Python

- **型アノテーション**: PEP 585準拠、`str | None` 形式を使用
- **Docstring**: NumPy style必須
- **命名規則**:
  - クラス: `PascalCase`
  - 関数/変数: `snake_case`
  - 定数: `UPPER_SNAKE_CASE`
  - プライベート: `_prefix`

### 非同期処理

- I/O処理はすべて `async/await`
- 外部API呼び出しには必ずタイムアウトを設定
- CPU boundな処理は `ProcessPoolExecutor` を使用

### テスト

- Scryfall APIはモック化必須
- `pytest-asyncio` を使用
- カバレッジ目標: 95%以上

## プルリクエストの作成手順

### 1. ブランチ作成

```bash
# mainブランチから最新を取得
git checkout main
git pull origin main

# 機能ブランチを作成
git checkout -b feature/your-feature-name
```

ブランチ名の規則:
- `feature/` - 新機能
- `fix/` - バグ修正
- `docs/` - ドキュメントのみの変更
- `refactor/` - リファクタリング
- `test/` - テストの追加・修正

### 2. 変更の実装

```bash
# コードの変更
# ... 実装 ...

# テストの作成・更新
# ... テスト追加 ...

# ローカルでテスト
uv run pytest
uv run mypy src
uv run ruff check src tests
```

### 3. コミット

```bash
# 変更をステージング
git add .

# コミット（詳細なメッセージを記載）
git commit -m "タイトル

詳細な説明:
- 変更内容1
- 変更内容2

テスト結果:
- All 389 tests passing ✅ (95% coverage)
"
```

### 4. プッシュとPR作成

```bash
# リモートにプッシュ
git push origin feature/your-feature-name

# GitHub上でPRを作成
# タイトル: 簡潔で明確な変更内容
# 説明: 以下のテンプレートを使用
```

### PRテンプレート

```markdown
## 概要
<!-- このPRで何を変更するのか -->

## 変更内容
<!-- 具体的な変更内容をリスト形式で -->
-
-

## 動機・背景
<!-- なぜこの変更が必要なのか -->

## テスト方法
<!-- どのようにテストしたか -->
- [ ] ローカルでテスト実行
- [ ] 型チェック合格
- [ ] リント合格
- [ ] カバレッジ確認

## 影響範囲
<!-- この変更が影響する範囲 -->

## スクリーンショット
<!-- 必要に応じて -->

## 関連Issue
<!-- 関連するIssueがあれば -->
Fixes #

## チェックリスト
- [ ] テストを追加・更新した
- [ ] ドキュメントを更新した
- [ ] CLAUDE.mdの規約に準拠している
- [ ] コミットメッセージが明確
```

## レビュープロセス

### レビュー基準

レビュアーは以下の観点でレビューを行います。

1. **機能性**: 変更が意図した通りに動作するか
2. **コード品質**: コーディング規約に準拠しているか
3. **テスト**: 十分なテストが書かれているか
4. **パフォーマンス**: パフォーマンス上の問題がないか
5. **セキュリティ**: セキュリティ上の問題がないか
6. **ドキュメント**: 適切なドキュメントが書かれているか

### フィードバック対応

- レビューコメントには48時間以内に返信してください
- 修正が必要な場合は、同じブランチにコミットを追加してください
- 議論が必要な場合は、PRのコメント欄で建設的に議論してください

### マージ条件

以下の条件を満たした場合にマージされます。

- [ ] 少なくとも1人のレビュアーの承認
- [ ] すべてのCIチェックが合格
- [ ] レビューコメントがすべて解決済み
- [ ] コンフリクトがない

## よくある質問

### Q: テストが失敗します

A: 以下を確認してください。

```bash
# 依存関係の再インストール
uv sync

# テストを個別に実行して原因特定
uv run pytest tests/path/to/failing_test.py -v

# キャッシュのクリア
find . -type d -name __pycache__ -exec rm -r {} +
find . -type d -name .pytest_cache -exec rm -r {} +
```

### Q: 型チェックエラーが出ます

A: 型ヒントを追加してください。

```python
# 悪い例
def search_cards(query):
    return results

# 良い例
def search_cards(query: str) -> list[Card]:
    return results
```

### Q: PRのサイズが大きくなりすぎました

A: 複数の小さなPRに分割することを推奨します。

1. 基盤となる変更を先にPR
2. その上に機能追加のPRを作成
3. 各PRは独立してレビュー可能にする

### Q: ドキュメントはどこに書けばいいですか？

A: 変更の種類によって場所が異なります。

- **ユーザー向け**: `README.md`
- **API仕様**: `docs/API-REFERENCE.md`
- **開発者向け**: `AGENT.md`
- **設定方法**: `docs/CONFIGURATION.md`
- **多言語対応**: `docs/INTERNATIONALIZATION.md`
- **テスト方法**: `docs/MCP-TESTING.md`

## サポート

質問や問題がある場合は、以下の方法でお問い合わせください。

- [GitHub Issues](https://github.com/reonyanarticle/scryfall-mcp/issues) - バグ報告、機能リクエスト
- [GitHub Discussions](https://github.com/reonyanarticle/scryfall-mcp/discussions) - 一般的な質問、アイデア

---

**貢献していただきありがとうございます！**

あなたの貢献がScryfall MCP Serverをより良いものにします。
