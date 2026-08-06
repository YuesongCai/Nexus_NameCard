"""Wire models shared by the API and the frontend (`web/src/types.ts` mirrors these)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Lang = Literal["en", "zh"]


class Localized(BaseModel):
    en: str
    zh: str


class Phone(BaseModel):
    label: Localized
    value: str


class LicenceType(BaseModel):
    code: str
    en: str
    zh: str


class Licence(BaseModel):
    """SFC licensing block — only present on B-version (licensed) cards."""

    ce_number: str = Field(alias="ceNumber")
    entity_ce_number: str | None = Field(default=None, alias="entityCeNumber")
    entity: Localized
    regulator: Localized
    types: list[LicenceType] = Field(default_factory=list)
    address: Localized | None = None

    model_config = {"populate_by_name": True}


class Contacts(BaseModel):
    whatsapp: str | None = None
    phones: list[Phone] = Field(default_factory=list)
    email: str | None = None
    linkedin: str | None = None
    website: str | None = None


class Card(BaseModel):
    slug: str
    variant: Literal["standard", "licensed"] = "standard"
    co_brand: Literal["ark"] | None = Field(default=None, alias="coBrand")
    name: Localized
    title: Localized
    org: Localized
    location: Localized | None = None
    contacts: Contacts
    licence: Licence | None = None
    member_line: Localized | None = Field(default=None, alias="memberLine")

    model_config = {"populate_by_name": True}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    lang: Lang = "en"
    slug: str | None = None
    session_id: str | None = Field(default=None, alias="sessionId")
    history: list[ChatMessage] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v


class Source(BaseModel):
    id: str
    title: str
    score: float


class Suggestion(BaseModel):
    id: str
    label: str
    question: str


class AnalyticsEvent(BaseModel):
    name: Literal[
        "card_view",
        "contact_tap",
        "vcard_save",
        "chat_ask",
        "chat_error",
        "lang_switch",
    ]
    slug: str | None = None
    detail: str | None = None
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}
