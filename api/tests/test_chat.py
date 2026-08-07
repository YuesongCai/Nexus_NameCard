"""Chat stream and provider behaviour.

The Bedrock path can't be exercised without AWS credentials, so it is tested against a
stubbed boto3 client — which is the piece most likely to break silently in production
(delta extraction from the ConverseStream event shape, and error normalisation).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from nexus_card.cards.store import CardStore
from nexus_card.chat.events import EventStream
from nexus_card.chat.prompt import build_system_prompt
from nexus_card.chat.service import ChatService
from nexus_card.config import Settings, get_settings
from nexus_card.llm.base import LlmError
from nexus_card.llm.providers import BedrockProvider
from nexus_card.models import Card, ChatMessage, ChatRequest
from nexus_card.rag.retriever import Retriever


class _StubProvider:
    name = "stub"
    model_id = "stub-1"

    def __init__(self, chunks: list[str] | None = None, fail: bool = False) -> None:
        self.chunks = chunks or ["Nexus ", "is ", "a platform."]
        self.fail = fail
        self.system: str | None = None

    async def stream(
        self, system: str, messages: list[ChatMessage], **_: Any
    ) -> AsyncIterator[str]:
        self.system = system
        if self.fail:
            raise LlmError("boom")
        for chunk in self.chunks:
            yield chunk


async def _collect(service: ChatService, request: ChatRequest, card: Any) -> list[dict[str, Any]]:
    return [json.loads(frame) async for frame in service.stream(request, card)]


# ----------------------------------------------------------------- event stream


def test_event_envelope_shape() -> None:
    events = EventStream(run_id="run_1", model="m")
    created = events.created()
    assert created["type"] == "response.created"
    assert created["seq"] == 1
    assert created["runId"] == "run_1"

    first = events.delta("a")
    assert "ttftMs" in first and "firstTokenAt" in first
    second = events.delta("b")
    assert "ttftMs" not in second  # timing fields appear on the first delta only
    assert second["seq"] == 3

    assert events.completed()["type"] == "response.completed"
    assert events.failed("nope", code="x")["code"] == "x"


# ------------------------------------------------------------------ chat service


async def test_stream_emits_protocol_order(
    settings: Settings, retriever: Retriever, store: CardStore
) -> None:
    provider = _StubProvider()
    service = ChatService(settings, retriever, provider)
    request = ChatRequest(question="What is Nexus?", lang="en", slug="grantpan")

    frames = await _collect(service, request, store.get("grantpan"))
    types = [f["type"] for f in frames]

    assert types[0] == "response.created"
    assert types[1] == "response.sources"
    assert types[-1] == "response.completed"
    assert [f["seq"] for f in frames] == list(range(1, len(frames) + 1))

    answer = "".join(f["delta"] for f in frames if f["type"] == "response.output_text.delta")
    assert answer == "Nexus is a platform."


async def test_sources_are_deduped_and_localised(
    settings: Settings, retriever: Retriever, store: CardStore
) -> None:
    service = ChatService(settings, retriever, _StubProvider())
    request = ChatRequest(question="Nexus 收费吗？", lang="zh", slug="grantpan")

    frames = await _collect(service, request, store.get("grantpan"))
    sources = next(f for f in frames if f["type"] == "response.sources")["sources"]

    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids))
    # Chinese request → Chinese half of the "English / 中文" doc title, no separator left.
    assert all(" / " not in s["title"] for s in sources)


async def test_llm_failure_degrades_to_handoff(
    settings: Settings, retriever: Retriever, store: CardStore
) -> None:
    service = ChatService(settings, retriever, _StubProvider(fail=True))
    request = ChatRequest(question="What is Nexus?", lang="zh", slug="grantpan")

    frames = await _collect(service, request, store.get("grantpan"))
    assert frames[-1]["type"] == "response.completed"

    answer = "".join(f["delta"] for f in frames if f["type"] == "response.output_text.delta")
    # The visitor gets a route to a human, not an empty bubble or a stack trace — and the
    # route is to a role, never to the card holder by name.
    assert "客户代表" in answer
    assert "潘青" not in answer


async def test_history_is_trimmed(retriever: Retriever) -> None:
    provider = _StubProvider()
    trimmed = get_settings().model_copy(update={"max_history_turns": 2})
    service = ChatService(trimmed, retriever, provider)

    history = [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"m{i}")
        for i in range(20)
    ]
    messages = service._messages(
        ChatRequest(question="latest", lang="en", slug="nexus", history=history)
    )
    assert len(messages) == 5  # 2 turns * 2 messages + the new question
    assert messages[-1].content == "latest"


# ---------------------------------------------------------------------- prompt


def test_prompt_carries_guardrails_and_context(licensed_card: Card) -> None:
    prompt = build_system_prompt(licensed_card, "en", "[1] some context")

    assert "No investment advice" in prompt
    assert "[1] some context" in prompt
    # A licensed card still may not answer as a licensed representative.
    assert "may still not give advice" in prompt


def test_prompt_flags_unlicensed_holder(store: CardStore) -> None:
    prompt = build_system_prompt(store.get("grantpan"), "en", "")
    assert "not an SFC-licensed representative" in prompt
    # No retrieved context → the prompt must forbid guessing.
    assert "Do not guess" in prompt


def test_prompt_never_leaks_the_holder_identity(
    licensed_card: Card, store: CardStore
) -> None:
    """The bot speaks as Nexus. The holder's name, title and contact details are on the
    page above the chat; putting them in the prompt only invites "go ask <name>", which
    reads as presumptuous to a stranger who just scanned a card."""
    for card in (licensed_card, store.get("grantpan")):
        for lang in ("en", "zh"):
            prompt = build_system_prompt(card, lang, "[1] ctx")
            for leaked in (
                card.name.en,
                card.name.zh,
                card.title.en,
                card.contacts.email or "\x00",
                (card.licence.ce_number if card.licence else "\x00"),
            ):
                assert leaked not in prompt, f"{leaked!r} leaked into the {lang} prompt"


# --------------------------------------------------------------------- bedrock


class _FakeBedrockClient:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.kwargs: dict[str, Any] | None = None

    def converse_stream(self, **kwargs: Any) -> dict[str, Any]:
        self.kwargs = kwargs
        return {"stream": iter(self.events)}


async def test_bedrock_extracts_deltas() -> None:
    client = _FakeBedrockClient(
        [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Nex"}}},
            {"contentBlockDelta": {"delta": {"text": "us"}}},
            {"contentBlockDelta": {"delta": {}}},  # tolerated: no text key
            {"messageStop": {"stopReason": "end_turn"}},
        ]
    )
    provider = BedrockProvider("ap-southeast-1", "model-x")
    provider._client = client

    out = [
        chunk
        async for chunk in provider.stream(
            "sys", [ChatMessage(role="user", content="hi")], max_tokens=10, temperature=0.1
        )
    ]
    assert "".join(out) == "Nexus"

    assert client.kwargs is not None
    assert client.kwargs["modelId"] == "model-x"
    assert client.kwargs["system"] == [{"text": "sys"}]
    assert client.kwargs["messages"] == [{"role": "user", "content": [{"text": "hi"}]}]


async def test_bedrock_stream_error_becomes_llm_error() -> None:
    provider = BedrockProvider("ap-southeast-1", "model-x")
    provider._client = _FakeBedrockClient(
        [
            {"contentBlockDelta": {"delta": {"text": "partial"}}},
            {"internalServerException": {"message": "kaboom"}},
        ]
    )

    with pytest.raises(LlmError):
        async for _ in provider.stream(
            "sys", [ChatMessage(role="user", content="hi")], max_tokens=10, temperature=0.1
        ):
            pass
