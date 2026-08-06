"""Starter questions shown as chips under the assistant's greeting.

Curated rather than generated: on a card the first tap decides whether the visitor engages
at all, so these are the four questions a prospect actually asks in the first minute — and
each one is answerable from the KB, so the first answer is never a miss.
"""

from __future__ import annotations

from nexus_card.models import Card, Lang, Suggestion

_EN: list[tuple[str, str, str]] = [
    ("what", "What is Nexus?", "What is Nexus, in one paragraph?"),
    ("who", "Who is it for?", "Who is Nexus built for?"),
    ("different", "How is it different?", "How is Nexus different from other wealth platforms?"),
    ("cost", "What does it cost?", "What does Nexus cost to use?"),
    ("data", "Is my data safe?", "How does Nexus handle client data and compliance?"),
    ("start", "How do I start?", "How do I get started with Nexus?"),
]

_ZH: list[tuple[str, str, str]] = [
    ("what", "Nexus 是什么？", "用一段话讲清楚 Nexus 是什么？"),
    ("who", "服务哪些人？", "Nexus 是为谁做的？"),
    ("different", "和别家有什么不同？", "Nexus 和其他财富管理平台有什么不同？"),
    ("cost", "怎么收费？", "使用 Nexus 需要多少费用？"),
    ("data", "数据安全吗？", "Nexus 如何处理客户数据与合规？"),
    ("start", "怎么开始？", "如何开始使用 Nexus？"),
]

_MAX = 4


def suggestions_for(card: Card | None, lang: Lang) -> list[Suggestion]:
    source = _ZH if lang == "zh" else _EN
    picked = source[:_MAX]

    items = [Suggestion(id=i, label=label, question=q) for i, label, q in picked]

    # Licensed cards get one extra, on-brand prompt the visitor is likely to have.
    if card is not None and card.licence is not None:
        items[-1] = Suggestion(
            id="licence",
            label="持牌怎么看？" if lang == "zh" else "What licences?",
            question=(
                "Nexus 和 Ark 持有哪些牌照？" if lang == "zh" else "What licences does Nexus hold?"
            ),
        )
    return items


def greeting_for(card: Card | None, lang: Lang) -> str:
    name = ""
    if card is not None:
        name = card.name.zh if lang == "zh" else card.name.en

    if lang == "zh":
        if name and name != "Nexus":
            return (
                "你好 —— 我是 Nexus 助手。关于 Nexus 是什么、服务谁、怎么合作，问我就行；"
                f"{name}本人的联系方式就在上面。"
            )
        return "你好 —— 我是 Nexus 助手。关于 Nexus 是什么、服务谁、怎么合作，问我就行。"

    if name and name != "Nexus":
        return (
            f"Hi — I'm the Nexus assistant. Ask me what Nexus does, who we serve, or how we "
            f"work together. {name}'s own details are up top."
        )
    return (
        "Hi — I'm the Nexus assistant. Ask me what Nexus does, who we serve, "
        "or how we work together."
    )
