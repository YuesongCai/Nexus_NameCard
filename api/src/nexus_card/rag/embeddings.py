"""Bedrock Titan text embeddings, used at index-build time and per query.

Embeddings are optional. If Bedrock is unavailable (local dev, no credentials, region
outage) the retriever degrades to BM25 alone rather than failing the request — for a KB
this small, lexical retrieval is already a solid floor.
"""

from __future__ import annotations

import json
import math
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class EmbeddingUnavailable(RuntimeError):
    """Raised when the embedding backend cannot be reached."""


class BedrockEmbedder:
    def __init__(self, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - dependency is declared
                raise EmbeddingUnavailable("boto3 not installed") from exc
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        out: list[list[float]] = []
        for text in texts:
            try:
                response = client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({"inputText": text[:8000]}),
                    accept="application/json",
                    contentType="application/json",
                )
                payload = json.loads(response["body"].read())
            except Exception as exc:
                raise EmbeddingUnavailable(str(exc)) from exc
            vector = payload.get("embedding")
            if not isinstance(vector, list):
                raise EmbeddingUnavailable("unexpected embedding payload shape")
            out.append(normalize([float(v) for v in vector]))
        return out


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for pre-normalised vectors (falls back to a safe 0.0)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True))
