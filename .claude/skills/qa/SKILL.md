---
name: qa
description: 品質ゲートを一括実行する。「QAして」「チェック回して」「品質ゲートを通して」で起動、または実装作業の仕上げに積極的に使う。Ruff(lint)→Ruff format→mypy --strict(型)→pytest(カバレッジ付き)の順に実行し、失敗があれば修正して再実行、全部通るまで繰り返してから結果を表で報告する。
model: sonnet
allowed-tools: Bash(uv run:*), Read, Edit, Grep, Glob
---

# /qa — 品質ゲート一括実行

`.claude/rules/python.md` のツールチェーンを一括で回す。CI に出す前・コミット前・実装の区切りで使う。
実行だけでよいなら軽量な `/test` を使う。本 skill は**修正まで含めて**完了させる。

## 手順（この順で。前段が失敗したら直してから次へ）

1. `uv run ruff check src/ tests/ --fix` — lint。autofix 後の差分は意味を変えていないか確認する。
2. `uv run ruff format src/ tests/` — 整形。
3. `uv run mypy src/` — 型チェック（strict）。エラーは握りつぶさず（`# type: ignore` の安易な追加禁止）、型を直す。
4. `uv run pytest --cov=scryfall_mcp --cov-report=term-missing -q` — テスト（カバレッジ95%目標）。
   失敗したら原因を特定して修正（テストを弱める方向の修正は理由を明示）。Scryfall の実 API を叩くテストを書かない（モック必須）。

- 修正を入れたら**必ず全段を再実行**する（部分実行で緑と報告しない）。
- セキュリティが関わる変更（認証・設定・ログ出力）では `uv run bandit -c pyproject.toml -r src/` も追加で回す。

## 出力

| 項目 | 結果 | 備考 |
|---|---|---|
| ruff check / ruff format / mypy / pytest | PASS / FAIL→修正→PASS | 修正内容の1行要約 |

最後に「全て PASS」か「未解決の FAIL（理由と提案）」を明言する。カバレッジが95%未満なら不足箇所（file:line）を列挙する。
