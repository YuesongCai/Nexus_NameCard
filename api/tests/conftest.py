"""Shared fixtures.

The licensed (B-version) card path is exercised against a synthetic fixture built in code
rather than a seeded profile. Regulatory identifiers belong to real, named individuals, so
the repo ships exactly one real person's card and no test data that could be mistaken for
someone's actual SFC registration.
"""

from __future__ import annotations

import pytest

from nexus_card.cards.store import CardStore
from nexus_card.config import Settings, get_settings
from nexus_card.models import Card
from nexus_card.rag.retriever import Retriever


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def lexical_settings(settings: Settings) -> Settings:
    """Force BM25-only so the suite never depends on AWS credentials."""
    return settings.model_copy(update={"embeddings_enabled": False})


@pytest.fixture(scope="session")
def retriever(lexical_settings: Settings) -> Retriever:
    return Retriever(lexical_settings)


@pytest.fixture(scope="session")
def store(settings: Settings) -> CardStore:
    return CardStore(settings.cards_dir)


@pytest.fixture(scope="session")
def licensed_card() -> Card:
    """A fictional licensed representative — placeholder identifiers throughout."""
    return Card.model_validate(
        {
            "slug": "licensed-example",
            "variant": "licensed",
            "coBrand": "ark",
            "name": {"en": "Test Advisor", "zh": "测试顾问"},
            "title": {"en": "Relationship Manager", "zh": "客户经理"},
            "org": {"en": "Example Licensed Entity", "zh": "示例持牌法团"},
            "contacts": {
                "whatsapp": "+85200000000",
                "phones": [
                    {"label": {"en": "HK-M", "zh": "香港手机"}, "value": "+852 0000 0000"},
                    {"label": {"en": "CN-M", "zh": "内地手机"}, "value": "+86 000 0000 0000"},
                ],
                "email": "advisor@example.test",
                "linkedin": "https://www.linkedin.com/company/noah-nexus",
                "website": "https://noahnexus.ai",
            },
            "licence": {
                "ceNumber": "AAA000",
                "entityCeNumber": "BBB111",
                "entity": {"en": "Example Licensed Entity", "zh": "示例持牌法团"},
                "regulator": {"en": "SFC", "zh": "香港证监会"},
                "types": [
                    {"code": "1", "en": "Dealing in Securities", "zh": "证券交易"},
                    {"code": "4", "en": "Advising on Securities", "zh": "就证券交易提供意见"},
                ],
                "address": {"en": "1 Example Street, Hong Kong", "zh": "香港示例街 1 号"},
            },
            "memberLine": {
                "en": "A member firm of Noah (US: NOAH · HK: 6686)",
                "zh": "诺亚成员企业（美股 NOAH · 港股 6686）",
            },
        }
    )
