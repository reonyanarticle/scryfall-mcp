#!/bin/bash

# MCPインスペクターをCLIモードで起動
echo "=========================================="
echo "Scryfall MCP Server Inspector"
echo "=========================================="
echo ""
echo "起動方法:"
echo "  npx @modelcontextprotocol/inspector --config .mcp.json --server scryfall"
echo ""
echo "または、CLIモード:"
echo "  npx @modelcontextprotocol/inspector --cli --transport stdio uv run scryfall-mcp"
echo ""
echo "=========================================="
echo ""
echo "インスペクターを起動します..."
echo ""

# 設定ファイルを使ってインスペクターを起動
npx @modelcontextprotocol/inspector --config .mcp.json --server scryfall
