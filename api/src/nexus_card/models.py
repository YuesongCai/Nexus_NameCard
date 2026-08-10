"""Wire models shared by the API and the frontend (`web/src/types.ts` mirrors these)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

#: Domains that belong to the Nexus brand rather than to the licensed corporation.
#: A card that shows licensing may not pair it with one of these — compliance's reading is
#: that a Nexus address next to an SFC number implies Nexus is the licensee, which it is not.
_BRAND_EMAIL_DOMAINS = ("nexus.ai", "noahnexus.ai")

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
    """SFC licensing block — only present on B-version (licensed) cards.

    Compliance (Gino, 2026-08-10) set the shape of this block:

    * The licensed corporation is **Ark Group Holdings (Hong Kong) Limited** — not Nexus,
      and not "Ark International". Nexus is a brand inside the group, not a licensee, so a
      page that shows licensing must name the entity that actually holds the licence.
    * The individual licence **types are not printed** any more. The SFC central entity
      number identifies the person; spelling out Type 1 / 4 / 9 adds regulatory surface for
      no reader benefit and has to be re-approved whenever someone's permissions change.
      `types` stays in the model because the footer still renders it when a card genuinely
      carries it — it is simply no longer the default.
    * "有则完整呈现，无则删除" — every field here is optional except the entity itself, so a
      card shows exactly what has been verified for that person and silently omits the rest.
      This is why `ce_number` is nullable: a person whose CE number we have not confirmed
      shows no personal SFC line at all, rather than a placeholder that reads as a claim.
    """

    ce_number: str | None = Field(default=None, alias="ceNumber")
    entity_ce_number: str | None = Field(default=None, alias="entityCeNumber")
    entity: Localized
    regulator: Localized
    types: list[LicenceType] = Field(default_factory=list)
    address: Localized | None = None

    model_config = {"populate_by_name": True}

    @field_validator("entity")
    @classmethod
    def _entity_is_the_licensee(cls, v: Localized) -> Localized:
        """Reject the two entity names compliance specifically ruled out.

        Both were live mistakes on the 8/10 draft, and neither is visible as wrong to
        someone editing a JSON file months from now — so the rule lives here rather than in
        a review checklist.
        """
        for text in (v.en, v.zh):
            lowered = text.lower()
            if "international" in lowered:
                raise ValueError(
                    "licensed entity must be 'Ark Group Holdings (Hong Kong) Limited' — "
                    "'Ark International' is not the licensee"
                )
            if "nexus" in lowered:
                raise ValueError(
                    "Nexus is a brand, not a licensed corporation; name the licensee "
                    "(Ark Group Holdings (Hong Kong) Limited)"
                )
        return v


class WeChat(BaseModel):
    """WeChat has no add-friend URL, so the card carries the two things that do work:
    an ID to copy and a personal QR image to long-press inside WeChat."""

    id: str | None = None
    qr: str | None = None


class Contacts(BaseModel):
    whatsapp: str | None = None
    wechat: WeChat | None = None
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

    @model_validator(mode="after")
    def _licensed_cards_obey_compliance(self) -> Card:
        """Two rules that only bind once a card shows licensing.

        Neither is enforceable field-by-field, because both are about the *combination*:
        a licence block plus the wrong logo, or a licence block plus the wrong email domain.
        Failing at load time means a bad card never reaches a printer or a QR code.
        """
        if self.licence is None:
            return self

        if self.co_brand != "ark":
            raise ValueError(
                f"card {self.slug!r} shows licensing, so the Ark mark is mandatory "
                '(coBrand must be "ark") — compliance allows it to be scaled down, '
                "never omitted"
            )

        email = (self.contacts.email or "").lower()
        domain = email.rpartition("@")[2]
        if domain in _BRAND_EMAIL_DOMAINS:
            raise ValueError(
                f"card {self.slug!r} shows licensing, so the email must be on the licensed "
                f"corporation's domain (@arkwealth.hk), not {domain!r}"
            )
        return self


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
