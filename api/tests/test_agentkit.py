"""AgentKit provider — event parsing and configuration guards.

The SSE payload shape is not contractually pinned by the runtime, and this machine has no
AgentKit credentials, so the parser is the part worth pinning down in tests: it has to read
several plausible event shapes and, critically, must not print the answer twice when a
runtime streams cumulative text instead of deltas.
"""

from __future__ import annotations

import pytest

from nexus_card.config import Settings
from nexus_card.llm.agentkit import AgentKitProvider, _extract_text
from nexus_card.llm.base import LlmError
from nexus_card.llm.providers import build_provider
from nexus_card.models import ChatMessage


class TestExtractText:
    def test_adk_content_parts(self) -> None:
        event = {"content": {"parts": [{"text": "你好"}, {"text": "世界"}]}}
        assert _extract_text(event) == "你好世界"

    def test_flat_delta(self) -> None:
        assert _extract_text({"delta": "abc"}) == "abc"

    def test_flat_text(self) -> None:
        assert _extract_text({"text": "abc"}) == "abc"

    def test_bare_parts(self) -> None:
        assert _extract_text({"parts": [{"text": "a"}, {"text": "b"}]}) == "ab"

    def test_string_content(self) -> None:
        assert _extract_text({"content": "hi"}) == "hi"

    def test_unknown_shape_is_empty_not_crash(self) -> None:
        assert _extract_text({"role": "model", "usage": {"tokens": 5}}) == ""
        assert _extract_text(None) == ""
        assert _extract_text(42) == ""

    def test_parts_without_text_are_skipped(self) -> None:
        # Tool-call and thought parts carry no `text`; they must not blow up the join.
        event = {"content": {"parts": [{"functionCall": {"name": "x"}}, {"text": "ok"}]}}
        assert _extract_text(event) == "ok"

    def test_error_event_raises(self) -> None:
        with pytest.raises(LlmError, match="rate limited"):
            _extract_text({"error": "rate limited"})


class TestConfiguration:
    def test_missing_config_names_every_missing_var(self) -> None:
        with pytest.raises(LlmError) as exc:
            AgentKitProvider("", "", "")
        message = str(exc.value)
        assert "BASE_URL" in message
        assert "APP_NAME" in message
        assert "API_KEY" in message

    def test_scheme_is_validated(self) -> None:
        with pytest.raises(LlmError, match="http"):
            AgentKitProvider("runtime.example.com", "app", "key")

    def test_backticks_and_trailing_slash_are_stripped(self) -> None:
        # The console renders the URL inside backticks often enough to be worth handling.
        provider = AgentKitProvider("`https://rt.example.com/`", "app", "key")
        assert provider.base_url == "https://rt.example.com"

    def test_model_id_identifies_the_app(self) -> None:
        provider = AgentKitProvider("https://rt.example.com", "my_agent", "key")
        assert provider.model_id == "agentkit:my_agent"

    def test_factory_builds_agentkit(self) -> None:
        settings = Settings(
            llm_provider="agentkit",
            agentkit_base_url="https://rt.example.com",
            agentkit_app_name="app",
            agentkit_api_key="key",
        )
        provider = build_provider(settings)
        assert provider.name == "agentkit"

    def test_factory_reports_unconfigured_agentkit_clearly(self) -> None:
        settings = Settings(llm_provider="agentkit")
        with pytest.raises(LlmError, match="not configured"):
            build_provider(settings)


class TestStreamDeduplication:
    """A runtime that streams cumulative text must not make the page repeat itself."""

    @pytest.mark.asyncio
    async def test_cumulative_stream_yields_only_new_text(self, monkeypatch) -> None:
        import httpx

        frames = [
            'data: {"content":{"parts":[{"text":"Nexus"}]}}',
            'data: {"content":{"parts":[{"text":"Nexus 是"}]}}',
            'data: {"content":{"parts":[{"text":"Nexus 是诺亚"}]}}',
            "data: [DONE]",
        ]

        class FakeResponse:
            status_code = 200

            async def aiter_lines(self):
                for frame in frames:
                    yield frame

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, *a, **kw):
                return httpx.Response(200)

            def stream(self, *a, **kw):
                return FakeResponse()

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())

        provider = AgentKitProvider("https://rt.example.com", "app", "key")
        out = [
            piece
            async for piece in provider.stream(
                "ctx", [ChatMessage(role="user", content="Nexus 是什么")],
                max_tokens=100, temperature=0.2, session_id="s1",
            )
        ]
        assert "".join(out) == "Nexus 是诺亚"
        assert out == ["Nexus", " 是", "诺亚"]
