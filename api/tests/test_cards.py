from __future__ import annotations

import pytest

from nexus_card.cards.store import CardNotFound, CardStore
from nexus_card.cards.vcard import render_vcard, vcard_filename
from nexus_card.models import Card


def test_seed_cards_parse(store: CardStore) -> None:
    slugs = store.slugs()
    assert "frankxiao" in slugs
    for slug in slugs:
        store.get(slug)


def test_unknown_slug_raises(store: CardStore) -> None:
    with pytest.raises(CardNotFound):
        store.get("nobody")


@pytest.mark.parametrize("evil", ["../secrets", "a/b", "UPPER!", "", "-leading"])
def test_slug_traversal_rejected(store: CardStore, evil: str) -> None:
    with pytest.raises(CardNotFound):
        store.get(evil)


def test_vcard_carries_the_essentials(store: CardStore) -> None:
    card = store.get("frankxiao")
    vcf = render_vcard(card, "en")

    assert vcf.startswith("BEGIN:VCARD\r\nVERSION:3.0")
    assert vcf.rstrip().endswith("END:VCARD")
    assert "FN:Frank Xiao 肖程元" in vcf
    assert "TITLE:R&D Director - Nexus" in vcf
    assert "chengyuanxiao@arkwealth.hk" in vcf
    assert "wa.me/85200000000" in vcf


def test_unlicensed_vcard_has_no_regulatory_note(store: CardStore) -> None:
    """An A-version card shows 不展示持牌信息, full stop."""
    vcf = render_vcard(store.get("nexus"), "en")
    assert "SFC CE No." not in vcf
    assert "Ark Group Holdings" not in vcf
    assert "ADR;" not in vcf


def test_licensed_vcard_carries_regulatory_detail(licensed_card: Card) -> None:
    vcf = render_vcard(licensed_card, "en")

    assert "SFC CE No. AAA000" in vcf
    assert "Entity CE No. BBB111" in vcf
    assert "ADR;TYPE=WORK" in vcf
    # Descriptions, not codes. The approved 8/10 card dropped the 1/4/9 numbering, and a
    # vCard note is the one place it could sneak back into someone's phone unnoticed.
    assert "Dealing in Securities" in vcf
    assert "Type 1" not in vcf
    assert "第 1 类" not in vcf


def test_multiple_numbers_keep_their_labels(licensed_card: Card) -> None:
    vcf = render_vcard(licensed_card, "zh")
    assert vcf.count("TEL;TYPE=WORK") == 4  # two numbers, each with an item label line
    assert "X-ABLabel:香港手机" in vcf
    assert "X-ABLabel:内地手机" in vcf


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_vcard_lines_respect_the_fold(licensed_card: Card, lang: str) -> None:
    vcf = render_vcard(licensed_card, lang)  # type: ignore[arg-type]
    for line in vcf.split("\r\n"):
        assert len(line.encode("utf-8")) <= 76, line


def test_vcard_filename_is_ascii(store: CardStore) -> None:
    name = vcard_filename(store.get("frankxiao"))
    assert name == "Frank-Xiao.vcf"
    name.encode("ascii")


# ------------------------------------------------------- compliance guardrails
#
# Rules from compliance (Gino, 2026-08-10). They are combination rules — a licence block
# next to the wrong logo, or next to the wrong email domain — so nothing catches them
# field-by-field, and nothing catches them by eye months later. Failing at load time means
# a bad card cannot reach a printer or a QR code.


def _licensed_payload(**overrides: object) -> dict:
    payload = {
        "slug": "compliance-probe",
        "variant": "licensed",
        "coBrand": "ark",
        "name": {"en": "Probe", "zh": "探针"},
        "title": {"en": "RM", "zh": "客户经理"},
        "org": {"en": "Ark Group Holdings (Hong Kong) Limited", "zh": "Ark"},
        "contacts": {"email": "probe@arkwealth.hk", "phones": []},
        "licence": {
            "entity": {
                "en": "Ark Group Holdings (Hong Kong) Limited",
                "zh": "Ark Group Holdings (Hong Kong) Limited",
            },
            "regulator": {"en": "SFC", "zh": "香港证监会"},
        },
    }
    payload.update(overrides)  # type: ignore[arg-type]
    return payload


def test_licensed_card_must_carry_the_ark_mark() -> None:
    with pytest.raises(ValueError, match="Ark mark is mandatory"):
        Card.model_validate(_licensed_payload(coBrand=None))


def test_licensed_card_rejects_a_nexus_email_domain() -> None:
    with pytest.raises(ValueError, match="licensed corporation's domain"):
        Card.model_validate(
            _licensed_payload(contacts={"email": "someone@nexus.ai", "phones": []})
        )


@pytest.mark.parametrize(
    "wrong",
    ["Ark International (Hong Kong) Limited", "Nexus (Hong Kong) Limited"],
)
def test_licensed_entity_must_be_the_actual_licensee(wrong: str) -> None:
    with pytest.raises(ValueError):
        Card.model_validate(
            _licensed_payload(
                licence={
                    "entity": {"en": wrong, "zh": wrong},
                    "regulator": {"en": "SFC", "zh": "香港证监会"},
                }
            )
        )


def test_a_correct_licensed_card_validates() -> None:
    card = Card.model_validate(_licensed_payload())
    assert card.licence is not None
    assert card.licence.ce_number is None  # optional: unconfirmed shows nothing
    assert card.licence.types == []


def test_licensed_card_without_a_ce_number_still_names_the_licensee() -> None:
    """"有则完整呈现，无则删除" in one assertion: the unconfirmed personal number renders as
    nothing, while the licensed corporation — which is confirmed — still appears."""
    vcf = render_vcard(Card.model_validate(_licensed_payload()), "en")
    assert "SFC CE No." not in vcf
    assert "Ark Group Holdings (Hong Kong) Limited" in vcf
