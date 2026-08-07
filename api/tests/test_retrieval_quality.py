"""Retrieval regression: real visitor questions must land on the right chapter.

Adding knowledge should never cost recall on what already worked. Without a check like
this, "the KB got bigger and the answers got worse" is only discoverable by a person
noticing a bad answer in production — which is exactly how it was found last time.

Each case is a question a stranger might actually type, paired with the chapter that should
answer it. Colloquial and formal phrasings both appear on purpose: BM25 is keyword matching,
so the chapter that answers "what can the AI do" has to literally contain the words people
use to ask it. That vocabulary gap — not the size of the KB — is what put an audit chapter
at the top of "Nexus 的 AI 可以干啥".

If a case fails, the fix is usually one of:
  * the chapter is missing the vocabulary the question uses (add it to the prose or `tags:`)
  * a supporting chapter carries a weight meant for a headline chapter
"""

from __future__ import annotations

import pytest

from nexus_card.config import get_settings
from nexus_card.rag.retriever import Retriever

# question -> one of these doc_ids must appear in the top 2 hits.
# Some questions genuinely have more than one right home ("要花多少钱" is answered both in
# the commercials chapter and in the FAQ), so the expectation is a set, not a single id.
# Narrowing it further would fail the suite on answers that are correct.
CASES: list[tuple[str, tuple[str, ...]]] = [
    # --- what Nexus is -----------------------------------------------------
    ("Nexus 是什么", ("what-is-nexus",)),
    ("What is Nexus?", ("what-is-nexus", "modules")),
    ("你们是做什么的", ("what-is-nexus", "what-you-can-do", "modules")),
    # --- what the AI does (the case that regressed) -------------------------
    ("Nexus的AI可以干啥", ("what-you-can-do", "modules")),
    ("AI 有什么用", ("what-you-can-do", "modules")),
    ("你们的 AI 能帮我做什么", ("what-you-can-do", "modules")),
    ("六大模块是哪六个", ("modules",)),
    # --- who it serves ------------------------------------------------------
    ("服务哪些人", ("who-its-for",)),
    ("我是做 EAM 的，适合我吗", ("who-its-for", "what-is-nexus")),
    # --- commercials --------------------------------------------------------
    ("怎么收费", ("commercials", "commitments-and-faq")),
    ("要花多少钱", ("commercials", "commitments-and-faq")),
    # --- FCN ----------------------------------------------------------------
    ("FCN 是什么", ("fcn-explained",)),
    ("FCN 如果股票跌了会怎么样", ("fcn-explained",)),
    ("执行价是什么意思", ("fcn-explained",)),
    # --- account opening ----------------------------------------------------
    ("开户要多久", ("account-opening",)),
    ("开户需要什么材料", ("account-opening",)),
    ("PI 800万包括房子吗", ("account-opening",)),
    ("内地客户能开户吗", ("account-opening",)),
    ("钱打到哪里", ("account-opening",)),
    # --- fund shelf ---------------------------------------------------------
    ("一级和二级有什么区别", ("fund-shelf",)),
    ("为什么要买私募", ("fund-shelf",)),
    # --- compliance / licensing --------------------------------------------
    ("你们有牌照吗", ("compliance", "noah-and-ark")),
    ("Are you licensed?", ("compliance", "noah-and-ark")),
    # --- trust / data -------------------------------------------------------
    ("客户数据安全吗", ("trust-and-audit", "compliance", "commitments-and-faq")),
    ("AI 会不会自己下单", ("trust-and-audit",)),
    # --- surfaces -----------------------------------------------------------
    ("能在 WhatsApp 上用吗", ("entry-points-and-memory", "connect")),
    # --- commitments --------------------------------------------------------
    ("你们会抢我的客户吗", ("commitments-and-faq",)),
]


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(get_settings())


@pytest.mark.parametrize(("question", "expected_docs"), CASES, ids=[c[0] for c in CASES])
def test_question_lands_on_the_right_chapter(
    retriever: Retriever, question: str, expected_docs: tuple[str, ...]
) -> None:
    hits = retriever.search(question, top_k=2)
    assert hits, f"no hit at all for {question!r}"
    found = [h.chunk.doc_id for h in hits]
    assert set(found) & set(expected_docs), (
        f"{question!r} → {found}, expected one of {list(expected_docs)} in the top 2.\n"
        f"Either that chapter lacks the words this question uses, or another chapter is "
        f"over-weighted."
    )


def test_out_of_scope_question_scores_low(retriever: Retriever) -> None:
    """Nothing in the KB should confidently answer an unrelated question.

    A low top score is what lets the bot say "not covered here" instead of stretching an
    unrelated passage into an answer.
    """
    hits = retriever.search("比特币现在多少钱")
    top = hits[0].score if hits else 0.0
    assert top < 1.0, f"out-of-scope question scored {top:.2f} — too confident"
