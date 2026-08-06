"""Hybrid retrieval: BM25 + (optional) dense cosine, fused by normalised score."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import structlog

from nexus_card.config import Settings
from nexus_card.rag.documents import Chunk, load_chunks
from nexus_card.rag.embeddings import BedrockEmbedder, EmbeddingUnavailable, cosine
from nexus_card.rag.lexical import Bm25, tokenize

log = structlog.get_logger(__name__)

_DENSE_WEIGHT = 0.55
_LEXICAL_WEIGHT = 0.45
# Small, deliberately: tags disambiguate between passages that mention a term in passing
# and passages that are *about* it, but they must never outrank the body signal.
_TAG_BONUS = 0.22


@dataclass(slots=True)
class Hit:
    chunk: Chunk
    score: float


def _min_max(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


class Retriever:
    """Loads the KB once at startup and answers top-k queries in-process.

    The dense vectors come from a build-time index (`scripts/build_index.py`). If that file
    is missing or stale relative to the KB, the retriever runs lexical-only and says so in
    the logs — it never blocks startup.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunks: list[Chunk] = load_chunks(settings.kb_dir)
        self._bm25 = Bm25.build([c.embed_text for c in self.chunks])
        self._tag_tokens: list[set[str]] = [
            {token for tag in c.tags for token in tokenize(tag)} for c in self.chunks
        ]
        self._vectors: dict[str, list[float]] = {}
        self._embedder: BedrockEmbedder | None = None
        self._dense_ok = False

        if settings.embeddings_enabled:
            self._load_vectors(settings.index_path)
            if self._vectors:
                self._embedder = BedrockEmbedder(
                    settings.aws_region, settings.bedrock_embed_model_id
                )
                self._dense_ok = True

        log.info(
            "retriever.ready",
            chunks=len(self.chunks),
            dense=self._dense_ok,
            kb_dir=str(settings.kb_dir),
        )

    # ------------------------------------------------------------------ index

    def _load_vectors(self, index_path: Path) -> None:
        if not index_path.exists():
            log.warning("retriever.index_missing", path=str(index_path))
            return
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("retriever.index_unreadable", error=str(exc))
            return

        vectors = payload.get("vectors", {})
        known = {c.id for c in self.chunks}
        matched = {k: v for k, v in vectors.items() if k in known}
        coverage = len(matched) / len(known) if known else 0.0
        if coverage < 0.9:
            log.warning("retriever.index_stale", coverage=round(coverage, 3))
            return
        self._vectors = matched

    # -------------------------------------------------------------- retrieval

    def search(self, query: str, top_k: int | None = None) -> list[Hit]:
        top_k = top_k or self.settings.retrieval_top_k
        if not self.chunks:
            return []

        lexical = _min_max(self._bm25.scores(query))

        dense: list[float] = [0.0] * len(self.chunks)
        dense_active = False
        if self._dense_ok and self._embedder is not None:
            try:
                q_vec = self._embedder.embed(query)
            except EmbeddingUnavailable as exc:
                log.warning("retriever.embed_failed", error=str(exc))
                self._dense_ok = False
            else:
                dense = _min_max(
                    [cosine(q_vec, self._vectors.get(c.id, [])) for c in self.chunks]
                )
                dense_active = True

        query_tokens = set(tokenize(query))

        hits: list[Hit] = []
        for i, chunk in enumerate(self.chunks):
            if dense_active:
                score = _DENSE_WEIGHT * dense[i] + _LEXICAL_WEIGHT * lexical[i]
            else:
                score = lexical[i]

            matches = len(query_tokens & self._tag_tokens[i])
            if matches:
                score += _TAG_BONUS * min(matches, 2) / 2

            hits.append(Hit(chunk=chunk, score=score * chunk.weight))

        hits.sort(key=lambda h: h.score, reverse=True)
        return [h for h in hits[:top_k] if h.score >= self.settings.retrieval_min_score]

    @staticmethod
    def as_context(hits: list[Hit]) -> str:
        blocks = []
        for i, hit in enumerate(hits, start=1):
            head = f"[{i}] {hit.chunk.title}"
            if hit.chunk.heading:
                head += f" — {hit.chunk.heading}"
            blocks.append(f"{head}\n{hit.chunk.text}")
        return "\n\n---\n\n".join(blocks)
