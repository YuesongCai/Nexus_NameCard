"""Concrete LLM providers: Bedrock Converse, Anthropic Messages, and a test echo."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from nexus_card.config import Settings
from nexus_card.llm.agentkit import AgentKitProvider
from nexus_card.llm.base import LlmError, LlmProvider
from nexus_card.models import ChatMessage

log = structlog.get_logger(__name__)


class BedrockProvider:
    """`ConverseStream` — works for both Claude and Nova model ids on Bedrock."""

    name = "bedrock"

    def __init__(self, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover
                raise LlmError("boto3 not installed") from exc
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        payload = {
            "modelId": self.model_id,
            "system": [{"text": system}],
            "messages": [
                {"role": m.role, "content": [{"text": m.content}]} for m in messages
            ],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }

        queue: asyncio.Queue[str | Exception | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def pump() -> None:
            try:
                response = client.converse_stream(**payload)
                for event in response["stream"]:
                    block = event.get("contentBlockDelta")
                    if block:
                        text = block.get("delta", {}).get("text")
                        if text:
                            loop.call_soon_threadsafe(queue.put_nowait, text)
                    if "internalServerException" in event or "modelStreamErrorException" in event:
                        loop.call_soon_threadsafe(
                            queue.put_nowait, LlmError("bedrock stream error")
                        )
                        return
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, LlmError(str(exc)))
                return
            loop.call_soon_threadsafe(queue.put_nowait, None)

        task = asyncio.get_running_loop().run_in_executor(None, pump)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    return
                if isinstance(item, Exception):
                    raise LlmError(str(item)) from item
                yield item
        finally:
            task.cancel()


class AnthropicProvider:
    """Direct Anthropic Messages API — the local-dev / non-AWS path."""

    name = "anthropic"

    def __init__(self, api_key: str, model_id: str) -> None:
        if not api_key:
            raise LlmError("NEXUS_CARD_ANTHROPIC_API_KEY is not set")
        self.api_key = api_key
        self.model_id = model_id

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        body = {
            "model": self.model_id,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            async with (
                httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client,
                client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    json=body,
                    headers=headers,
                ) as response,
            ):
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", "replace")[:400]
                    raise LlmError(f"anthropic {response.status_code}: {detail}")
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    event = json.loads(chunk)
                    if event.get("type") == "content_block_delta":
                        text = event.get("delta", {}).get("text")
                        if text:
                            yield text
        except httpx.HTTPError as exc:
            raise LlmError(str(exc)) from exc


class EchoProvider:
    """Deterministic provider for tests and offline demos — never calls out."""

    name = "echo"
    model_id = "echo"

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        last = messages[-1].content if messages else ""
        for word in f"[echo] {last}".split(" "):
            await asyncio.sleep(0)
            yield word + " "


def build_provider(settings: Settings) -> LlmProvider:
    provider = settings.llm_provider.lower()
    if provider == "bedrock":
        return BedrockProvider(settings.aws_region, settings.bedrock_model_id)
    if provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model_id)
    if provider == "agentkit":
        return AgentKitProvider(
            settings.agentkit_base_url,
            settings.agentkit_app_name,
            settings.agentkit_api_key,
            connect_timeout=settings.agentkit_connect_timeout,
            read_timeout=settings.agentkit_read_timeout,
        )
    if provider == "echo":
        return EchoProvider()
    raise LlmError(f"unknown llm provider: {settings.llm_provider}")
