#!/bin/bash
set -e

echo "🚀 Running Scryfall MCP Test Suite"
echo "=================================="

# Change to project directory
cd "$(dirname "$0")/.."

echo "📦 Installing dependencies..."
uv sync --dev

echo "🔍 Running linter..."
uv run ruff check src tests scripts

echo "🔧 Running type checker..."
uv run mypy src

echo "🧪 Running unit tests with coverage..."
uv run pytest --cov=scryfall_mcp --cov-report=term-missing tests/

echo "🌐 Running MCP integration tests..."
uv run python scripts/mcp_test.py

echo "🔒 Running security checks..."
uv run bandit -r src/ || true
uv run safety check || true

echo "✅ All tests completed successfully!"