from __future__ import annotations

import pytest

from nexus_card.cards.store import CardNotFound, CardStore
from nexus_card.cards.vcard import render_vcard, vcard_filename
from nexus_card.models import Card


def test_seed_cards_parse(store: CardStore) -> None:
    slugs = store.slugs()
    assert "grantpan" in slugs
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
    card = store.get("grantpan")
    vcf = render_vcard(card, "en")

    assert vcf.startswith("BEGIN:VCARD\r\nVERSION:3.0")
    assert vcf.rstrip().endswith("END:VCARD")
    assert "FN:Grant Pan 潘青" in vcf
    assert "TITLE:CEO\\, Hong Kong · Group CFO" in vcf
    assert "grant.pan@nexus.ai" in vcf
    assert "wa.me/85200000000" in vcf


def test_unlicensed_vcard_has_no_regulatory_note(store: CardStore) -> None:
    vcf = render_vcard(store.get("grantpan"), "en")
    assert "SFC CE No." not in vcf
    assert "ADR;" not in vcf


def test_licensed_vcard_carries_regulatory_detail(licensed_card: Card) -> None:
    vcf = render_vcard(licensed_card, "en")

    assert "SFC CE No. AAA000" in vcf
    assert "Entity CE No. BBB111" in vcf
    assert "Type 1 Dealing in Securities" in vcf
    assert "ADR;TYPE=WORK" in vcf


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
    name = vcard_filename(store.get("grantpan"))
    assert name == "Grant-Pan.vcf"
    name.encode("ascii")
