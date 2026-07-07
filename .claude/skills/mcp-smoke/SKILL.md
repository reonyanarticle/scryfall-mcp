---
name: mcp-smoke
description: Scryfall MCPサーバーのスモークテスト。「スモークテスト」「MCPの動作確認」「サーバー動く？」で起動、またはserver.py/tools/を変更した仕上げに積極的に使う。3ツール(search_cards/autocomplete_card_names/get_latest_expansion_set)を代表入力で呼び、応答・該当なしメッセージ・日本語検索を確認してPASS/FAILで報告する。
model: sonnet
allowed-tools: Bash(uv run:*), Bash(npx:*), Read, Grep
---

# /mcp-smoke — MCPサーバー スモークテスト

実装後のサーバーが「Claude Desktop から使える状態か」を最短で確認する。pytest の単体テストとは別に、**MCP プロトコル越しの実挙動**を見る。

## 前提

- `SCRYFALL_MCP_USER_AGENT` が設定されているか確認する（`echo` はせず存在チェックのみ。値をログ・出力に貼らない）。未設定なら「未設定時のエラーガイダンスが返ること」自体をテストケースとして扱う。
- 本セッションに dev サーバーが接続済み（`mcp__scryfall__*` ツールが見える）ならそれを直接呼ぶ。未接続なら `uv run python` で in-process クライアント（fastmcp の Client）から呼ぶ。

## テストケース（代表入力）

| # | 呼び出し | 期待 |
|---|---|---|
| 1 | `search_cards("Lightning Bolt")` | カード情報（名前・マナコスト・タイプ・オラクルテキスト）が返る |
| 2 | `search_cards("稲妻", language="ja")` | 日本語検索が機能し `printed_name` 優先で表示される |
| 3 | `search_cards("zzz_not_a_card_zzz")` | **エラーでなく**「見つからない」旨の分かりやすいメッセージ |
| 4 | `autocomplete_card_names("Light")` | 候補リストが返る |
| 5 | `get_latest_expansion_set()` | 最新エキスパンションの情報が返る |

- Scryfall を叩くケースは連続実行せず、レート制限（75–100ms 間隔）が実装で守られていることをログ/実装で確認する。ネットワーク不通時は SKIP と報告。
- レスポンスの annotations（ユーザー向けは `audience=["user", "assistant"]`）と、`ImageContent` が含まれないことも1ケースで確認する。
- 対話デバッグが必要なら MCP Inspector を案内する：`./run_mcp_inspector.sh` または `npx @modelcontextprotocol/inspector uv run scryfall-mcp`

## 出力

ケースごとに PASS / FAIL / SKIP の表。FAIL は再現コマンドと原因の当たり（1行）を添える。
最後に「Claude Desktop 登録可否」の判定を一言で述べる。
