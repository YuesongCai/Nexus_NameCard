"""Retrieval quality guards.

These are the tests that actually matter for a RAG bot: if someone edits the knowledge
base and the top hit for "what does it cost" stops being the commercials doc, the answer
quality falls off a cliff with no other signal.
"""

from __future__ import annotations

import pytest

from nexus_card.config import get_settings
from nexus_card.rag.documents import load_chunks
from nexus_card.rag.lexical import tokenize
from nexus_card.rag.retriever import Retriever


def test_kb_loads() -> None:
    chunks = load_chunks(get_settings().kb_dir)
    assert len(chunks) > 20
    assert all(chunk.text.strip() for chunk in chunks)
    assert len({chunk.id for chunk in chunks}) == len(chunks)


def test_tokenizer_handles_cjk() -> None:
    tokens = tokenize("客户数据安全吗")
    assert "客户" in tokens
    assert "数据" in tokens
    # Latin still tokenizes as words, and stopwords drop out.
    assert tokenize("what is the FCN") == ["fcn"]


# The contract of a top-k retriever is that the right passage reaches the prompt, not that
# it ranks first — every hit in `retrieval_top_k` is concatenated into the context window.
# So membership is asserted for every query, and rank-1 only where the lexical signal is
# unambiguous (BM25 alone can be beaten by a short passage that happens to share two query
# terms; the dense index fixes that in production, and the suite must not depend on AWS).
@pytest.mark.parametrize(
    ("query", "expected_doc"),
    [
        ("What does Nexus cost?", {"commercials", "commitments-and-faq"}),
        ("Nexus 收费吗", {"commercials", "commitments-and-faq"}),
        ("how many FCN issuers", {"product-shelf", "modules"}),
        ("who is Nexus built for", {"who-its-for"}),
        ("客户数据安全吗", {"compliance", "commitments-and-faq"}),
        ("what licences do you hold", {"compliance", "noah-and-ark"}),
        ("怎么开户", {"onboarding"}),
        ("can I use it from WhatsApp", {"connect"}),
        ("who owns the client relationship", {"commitments-and-faq", "who-its-for"}),
        ("诺亚控股是什么", {"noah-and-ark"}),
    ],
)
def test_expected_doc_reaches_the_prompt(
    retriever: Retriever, query: str, expected_doc: set[str]
) -> None:
    hits = retriever.search(query)
    assert hits, f"no hits for {query!r}"
    found = {hit.chunk.doc_id for hit in hits}
    assert found & expected_doc, f"{query!r} → {[h.chunk.doc_id for h in hits]}"


@pytest.mark.parametrize(
    ("query", "expected_doc"),
    [
        ("What does Nexus cost?", {"commercials", "commitments-and-faq"}),
        ("how many FCN issuers", {"product-shelf"}),
        ("who is Nexus built for", {"who-its-for"}),
        ("客户数据安全吗", {"compliance", "commitments-and-faq"}),
        ("怎么开户", {"onboarding"}),
    ],
)
def test_top_hit_is_relevant(retriever: Retriever, query: str, expected_doc: set[str]) -> None:
    hits = retriever.search(query, top_k=3)
    assert hits[0].chunk.doc_id in expected_doc, (
        f"{query!r} → {[h.chunk.doc_id for h in hits]}"
    )


def test_tags_lift_the_on_topic_passage(retriever: Retriever) -> None:
    """The `whatsapp` tag must pull the Connect doc above unrelated passages."""
    ranked = [hit.chunk.doc_id for hit in retriever.search("can I use it from WhatsApp")]
    assert "connect" in ranked[:2]


def test_off_topic_query_returns_little(retriever: Retriever) -> None:
    hits = retriever.search("what is the weather in reykjavik tomorrow")
    # The prompt handles the refusal, but retrieval should not confidently hand over
    # unrelated context either.
    assert len(hits) <= 2


def test_context_is_numbered(retriever: Retriever) -> None:
    hits = retriever.search("What is Nexus?", top_k=2)
    context = Retriever.as_context(hits)
    assert context.startswith("[1]")
    assert "[2]" in context
