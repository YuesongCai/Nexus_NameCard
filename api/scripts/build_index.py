#!/usr/bin/env python3
"""Build the dense KB index.

Run after editing anything under `kb/`:

    python scripts/build_index.py

Needs AWS credentials with `bedrock:InvokeModel` on the Titan embeddings model. Without
them the service still runs — the retriever falls back to BM25 — but recall on paraphrased
questions is noticeably worse, so this should be part of the release step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.config import get_settings
from nexus_card.rag.documents import load_chunks
from nexus_card.rag.embeddings import BedrockEmbedder, EmbeddingUnavailable


def main() -> int:
    settings = get_settings()
    chunks = load_chunks(settings.kb_dir)
    if not chunks:
        print(f"No markdown found under {settings.kb_dir}", file=sys.stderr)
        return 1

    print(f"Embedding {len(chunks)} chunks with {settings.bedrock_embed_model_id} …")
    embedder = BedrockEmbedder(settings.aws_region, settings.bedrock_embed_model_id)

    vectors: dict[str, list[float]] = {}
    for i, chunk in enumerate(chunks, start=1):
        try:
            vectors[chunk.id] = embedder.embed(chunk.embed_text)
        except EmbeddingUnavailable as exc:
            print(f"\nFailed on {chunk.id}: {exc}", file=sys.stderr)
            return 2
        print(f"\r  {i}/{len(chunks)}", end="", flush=True)
    print()

    settings.index_path.parent.mkdir(parents=True, exist_ok=True)
    settings.index_path.write_text(
        json.dumps(
            {
                "model": settings.bedrock_embed_model_id,
                "dim": len(next(iter(vectors.values()))),
                "count": len(vectors),
                "vectors": vectors,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {settings.index_path} ({len(vectors)} vectors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
