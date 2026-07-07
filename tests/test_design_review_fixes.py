"""Behavior tests for the design-review fixes.

Covers the security / robustness behaviors introduced by the architecture
review: ASGI 401 responses, JWT audience verification, request-input
allowlists, per-card validation skipping, TTL-preserving cache write-back,
and the single-probe circuit breaker.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from scryfall_mcp.models import Card, SearchCardsRequest
from scryfall_mcp.settings import Settings


def _make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "user_agent": "Test/1.0 (test@example.com)",
        "oauth_enabled": True,
        "jwt_secret_key": "x" * 32,
        "oauth_client_id": "test-client",
        "oauth_authorization_url": "https://auth.example.com/oauth/authorize",
        "oauth_token_url": "https://auth.example.com/oauth/token",
    }
    base.update(overrides)
    return Settings(**base)


class _SendRecorder:
    """Minimal ASGI send callable that records messages."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int | None:
        for message in self.messages:
            if message["type"] == "http.response.start":
                return int(message["status"])
        return None

    @property
    def body(self) -> bytes:
        return b"".join(
            m.get("body", b"")
            for m in self.messages
            if m["type"] == "http.response.body"
        )

    def header(self, name: bytes) -> bytes | None:
        for message in self.messages:
            if message["type"] == "http.response.start":
                for key, value in message["headers"]:
                    if key.lower() == name:
                        return bytes(value)
        return None


class TestMiddleware401Responses:
    """Auth failures must produce real 401 responses, not exceptions."""

    @pytest.mark.asyncio
    async def test_jwt_missing_header_sends_401(self) -> None:
        from scryfall_mcp.auth.middleware import JWTValidationMiddleware

        downstream = AsyncMock()
        middleware = JWTValidationMiddleware(downstream, _make_settings())
        send = _SendRecorder()

        scope = {"type": "http", "headers": []}
        await middleware(scope, AsyncMock(), send)

        assert send.status == 401
        assert b"Authorization" in send.body
        downstream.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_jwt_invalid_token_sends_401_generic_detail(self) -> None:
        from scryfall_mcp.auth.middleware import JWTValidationMiddleware

        downstream = AsyncMock()
        middleware = JWTValidationMiddleware(downstream, _make_settings())
        send = _SendRecorder()

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer not-a-jwt")],
        }
        await middleware(scope, AsyncMock(), send)

        assert send.status == 401
        detail = json.loads(send.body)["detail"]
        # Generic message only — no internal error details leak to clients
        assert detail == "Invalid or expired token"
        downstream.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_email_missing_header_sends_401_with_challenge(self) -> None:
        from scryfall_mcp.auth.middleware import EmailAuthMiddleware

        downstream = AsyncMock()
        settings = Settings(
            user_agent="Test/1.0 (test@example.com)",
            email_auth_enabled=True,
            email_auth_credentials={"real@example.net": "hash"},
        )
        middleware = EmailAuthMiddleware(downstream, settings)
        send = _SendRecorder()

        scope = {"type": "http", "headers": []}
        await middleware(scope, AsyncMock(), send)

        assert send.status == 401
        assert send.header(b"www-authenticate") is not None
        downstream.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self) -> None:
        from scryfall_mcp.auth.middleware import JWTValidationMiddleware

        downstream = AsyncMock()
        middleware = JWTValidationMiddleware(downstream, _make_settings())

        scope = {"type": "lifespan"}
        await middleware(scope, AsyncMock(), AsyncMock())

        downstream.assert_awaited_once()


class TestJWTAudienceVerification:
    """Tokens minted for other audiences must be rejected."""

    def _make_token(self, settings: Settings, **claims: Any) -> str:
        from jose import jwt

        now = datetime.now(UTC)
        payload = {
            "sub": "user",
            "iat": now,
            "exp": now + timedelta(hours=1),
            **claims,
        }
        return jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )

    @pytest.mark.asyncio
    async def test_token_with_correct_audience_accepted(self) -> None:
        from scryfall_mcp.auth.middleware import JWTValidationMiddleware

        settings = _make_settings(jwt_audience="scryfall-mcp-api")
        downstream = AsyncMock()
        middleware = JWTValidationMiddleware(downstream, settings)
        token = self._make_token(settings, aud="scryfall-mcp-api")

        scope: dict[str, Any] = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        await middleware(scope, AsyncMock(), AsyncMock())

        downstream.assert_awaited_once()
        assert scope["user"]["sub"] == "user"

    @pytest.mark.asyncio
    async def test_token_with_wrong_audience_rejected(self) -> None:
        from scryfall_mcp.auth.middleware import JWTValidationMiddleware

        settings = _make_settings(jwt_audience="scryfall-mcp-api")
        downstream = AsyncMock()
        middleware = JWTValidationMiddleware(downstream, settings)
        token = self._make_token(settings, aud="some-other-service")
        send = _SendRecorder()

        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        await middleware(scope, AsyncMock(), send)

        assert send.status == 401
        downstream.assert_not_awaited()


class TestRequestInputAllowlists:
    """format_filter/language must not allow Scryfall operator injection."""

    def test_valid_format_normalized(self) -> None:
        request = SearchCardsRequest(query="bolt", format_filter=" Modern ")
        assert request.format_filter == "modern"

    def test_format_operator_injection_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SearchCardsRequest(query="bolt", format_filter="standard or t:land")

    def test_valid_language_normalized(self) -> None:
        request = SearchCardsRequest(query="bolt", language="JA")
        assert request.language == "ja"

    def test_language_injection_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SearchCardsRequest(query="bolt", language="ja or c:r")


class TestCardModelResilience:
    """One unusual card must not fail a whole search page."""

    def _minimal_card(self, **overrides: Any) -> dict[str, Any]:
        card = {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Test Card",
            "released_at": "2024-01-01",
            "uri": "https://api.scryfall.com/cards/x",
            "scryfall_uri": "https://scryfall.com/card/x",
            "layout": "normal",
            "type_line": "Instant",
            "set": "tst",
            "set_name": "Test Set",
            "set_type": "expansion",
            "collector_number": "1",
            "rarity": "common",
        }
        card.update(overrides)
        return card

    def test_card_without_optional_nested_fields_parses(self) -> None:
        card = Card(**self._minimal_card())
        # Missing oracle_id / prices / related_uris / legalities get defaults
        assert card.oracle_id is None
        assert card.prices.usd is None
        assert card.legalities.standard == "not_legal"

    def test_parse_search_result_skips_invalid_card(self) -> None:
        from scryfall_mcp.api.client import ScryfallAPIClient

        data = {
            "object": "list",
            "total_cards": 2,
            "has_more": False,
            "data": [
                self._minimal_card(),
                {"object": "card", "name": "Broken Card"},  # missing required
            ],
        }
        result = ScryfallAPIClient._parse_search_result(data)

        assert len(result.data) == 1
        assert result.data[0].name == "Test Card"


class TestToolSchemaMatchesRequestModel:
    """Guard against drift between the tool signature and SearchCardsRequest.

    The MCP tool schema is derived from the ``search_cards`` closure
    signature in server.py, while validation happens via
    SearchCardsRequest. This test fails if the two contracts diverge
    (field added/removed on one side only, or defaults drifting).
    """

    @pytest.mark.asyncio
    async def test_search_cards_schema_matches_request_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scryfall_mcp.server import ScryfallMCPServer

        monkeypatch.setenv("SCRYFALL_MCP_USER_AGENT", "Test/1.0 (test@example.com)")
        server = ScryfallMCPServer()
        tools = await server.app.get_tools()
        tool_props = tools["search_cards"].parameters["properties"]

        model_schema = SearchCardsRequest.model_json_schema()
        model_props = model_schema["properties"]

        assert set(tool_props.keys()) == set(model_props.keys())

        # Defaults must match wherever both sides declare one
        for name, model_prop in model_props.items():
            if "default" in model_prop and "default" in tool_props[name]:
                assert tool_props[name]["default"] == model_prop["default"], (
                    f"Default drift for parameter {name!r}"
                )


class TestToolPipelinePlaceholderResolution:
    """The tool pipeline must resolve __LATEST_SET__ via the I/O layer."""

    @pytest.mark.asyncio
    async def test_pipeline_resolves_latest_set_placeholder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import patch

        from scryfall_mcp.i18n import set_current_locale
        from scryfall_mcp.tools.search import CardSearchTool

        monkeypatch.setenv("SCRYFALL_MCP_USER_AGENT", "Test/1.0 (test@example.com)")
        set_current_locale("ja")
        try:
            request = SearchCardsRequest(query="最新のセット", language="ja")

            async def fake_resolve(query: str) -> str:
                assert "__LATEST_SET__" in query
                return query.replace("__LATEST_SET__", "spm")

            # Patch at the tools module so the test fails if the pipeline
            # stops calling the resolver (wiring regression guard)
            with patch(
                "scryfall_mcp.tools.search.resolve_latest_set_placeholder",
                side_effect=fake_resolve,
            ) as mock_resolve:
                _, _, built = await CardSearchTool._build_query_pipeline(request)

            mock_resolve.assert_awaited_once()
            assert "__LATEST_SET__" not in built.scryfall_query
            assert "spm" in built.scryfall_query
        finally:
            set_current_locale("en")


class TestConfigFileAtomicWrite:
    """PII config writes must be atomic with 0o600 from creation."""

    def test_write_config_file_permissions_and_content(self, tmp_path) -> None:
        from scryfall_mcp.setup_wizard import _write_config_file

        config_file = tmp_path / "config.json"
        _write_config_file(config_file, {"user_agent": "X/1.0 (a@b.c)"})

        assert config_file.exists()
        assert (config_file.stat().st_mode & 0o777) == 0o600
        assert json.loads(config_file.read_text())["user_agent"] == "X/1.0 (a@b.c)"
        # No temp file left behind (atomic rename)
        assert list(tmp_path.glob("*.tmp")) == []

    def test_write_config_file_overwrites_existing(self, tmp_path) -> None:
        from scryfall_mcp.setup_wizard import _write_config_file

        config_file = tmp_path / "config.json"
        _write_config_file(config_file, {"user_agent": "old"})
        _write_config_file(config_file, {"user_agent": "new"})

        assert json.loads(config_file.read_text())["user_agent"] == "new"
        assert (config_file.stat().st_mode & 0o777) == 0o600


class TestCompositeCacheTTLWriteBack:
    """L2->L1 promotion must preserve the remaining TTL."""

    @pytest.mark.asyncio
    async def test_write_back_uses_remaining_ttl(self) -> None:
        from scryfall_mcp.cache.backends import CompositeCache, MemoryCache

        memory = MemoryCache(max_size=10, default_ttl=86400)
        redis_cache = AsyncMock()
        redis_cache.get_with_ttl = AsyncMock(return_value=({"v": 1}, 42))

        cache = CompositeCache(memory, redis_cache)
        value = await cache.get("key")

        assert value == {"v": 1}
        entry = memory._cache["key"]
        # Promotion must carry the remaining 42s, not the 24h default
        assert entry.expires_at is not None
        assert entry.expires_at - entry.created_at == pytest.approx(42, abs=2)


class TestCircuitBreakerSingleProbe:
    """half_open must admit exactly one concurrent recovery probe."""

    @pytest.mark.asyncio
    async def test_half_open_second_concurrent_call_rejected(self) -> None:
        from scryfall_mcp.api.rate_limiter import (
            CircuitBreaker,
            CircuitBreakerOpenError,
        )

        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)

        async def fail() -> None:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await breaker.call(fail)
        assert breaker.state == "open"

        # Force the recovery window to have elapsed (avoid clock-resolution
        # flakiness with recovery_timeout=0)
        breaker._last_failure_time -= 1.0

        probe_started = asyncio.Event()
        release_probe = asyncio.Event()

        async def slow_success() -> str:
            probe_started.set()
            await release_probe.wait()
            return "ok"

        probe_task = asyncio.create_task(breaker.call(slow_success))
        await asyncio.wait_for(probe_started.wait(), timeout=5)

        # While the probe is in flight, a second request must be rejected
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(slow_success)

        release_probe.set()
        assert await probe_task == "ok"
        assert breaker.state == "closed"
