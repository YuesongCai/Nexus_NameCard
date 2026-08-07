"""Volc V4 signing — pinned against fixed inputs.

The signer is the part of the deploy path that fails silently: a wrong canonical string
produces a valid-looking request that the server rejects with an opaque error. Fixing the
clock and the keys makes the signature deterministic, so a regression shows up here rather
than in CI against a live account.
"""

from __future__ import annotations

import datetime as dt
import json

import pytest

from nexus_card.deploy.byteplus import BytePlusSigner, _canonical_query

FIXED_NOW = dt.datetime(2026, 8, 6, 12, 0, 0, tzinfo=dt.UTC)


@pytest.fixture
def signer() -> BytePlusSigner:
    return BytePlusSigner("AKTEST", "SKTEST", service="agentkit", region="ap-southeast-1")


class TestSigner:
    def test_missing_credentials_explain_where_to_get_them(self) -> None:
        with pytest.raises(ValueError, match="IAM"):
            BytePlusSigner("", "", service="agentkit", region="ap-southeast-1")

    def test_regional_host_convention(self, signer: BytePlusSigner) -> None:
        assert signer.host == "agentkit.ap-southeast-1.byteplusapi.com"

    def test_explicit_host_wins(self) -> None:
        s = BytePlusSigner(
            "a", "b", service="agentkit", region="r", host="custom.byteplusapi.com"
        )
        assert s.host == "custom.byteplusapi.com"

    def test_signature_is_deterministic(self, signer: BytePlusSigner) -> None:
        body = json.dumps({"Id": "rt-1"}).encode()
        first = signer.sign(action="GetRuntime", version="2024-01-01", body=body, now=FIXED_NOW)
        second = signer.sign(action="GetRuntime", version="2024-01-01", body=body, now=FIXED_NOW)
        assert first.headers["Authorization"] == second.headers["Authorization"]

    def test_body_change_changes_signature(self, signer: BytePlusSigner) -> None:
        a = signer.sign(action="X", version="v", body=b'{"a":1}', now=FIXED_NOW)
        b = signer.sign(action="X", version="v", body=b'{"a":2}', now=FIXED_NOW)
        assert a.headers["Authorization"] != b.headers["Authorization"]
        assert a.headers["X-Content-Sha256"] != b.headers["X-Content-Sha256"]

    def test_required_headers_present(self, signer: BytePlusSigner) -> None:
        signed = signer.sign(action="ListRuntimes", version="2024-01-01", now=FIXED_NOW)
        for header in ("Authorization", "X-Date", "X-Content-Sha256", "Host", "Content-Type"):
            assert header in signed.headers
        assert signed.headers["X-Date"] == "20260806T120000Z"

    def test_credential_scope_shape(self, signer: BytePlusSigner) -> None:
        signed = signer.sign(action="ListRuntimes", version="2024-01-01", now=FIXED_NOW)
        assert "Credential=AKTEST/20260806/ap-southeast-1/agentkit/request" in (
            signed.headers["Authorization"]
        )
        assert "SignedHeaders=content-type;host;x-content-sha256;x-date" in (
            signed.headers["Authorization"]
        )

    def test_secret_never_appears_in_output(self, signer: BytePlusSigner) -> None:
        signed = signer.sign(action="ListRuntimes", version="2024-01-01", now=FIXED_NOW)
        blob = signed.url + json.dumps(signed.headers)
        assert "SKTEST" not in blob

    def test_action_and_version_in_query(self, signer: BytePlusSigner) -> None:
        signed = signer.sign(action="ListRuntimes", version="2024-01-01", now=FIXED_NOW)
        assert "Action=ListRuntimes" in signed.url
        assert "Version=2024-01-01" in signed.url

    def test_query_is_sorted_and_encoded(self) -> None:
        assert _canonical_query({"B": "2", "A": "1 2"}) == "A=1%202&B=2"

    def test_empty_body_hashes_to_sha256_of_empty(self, signer: BytePlusSigner) -> None:
        signed = signer.sign(action="ListRuntimes", version="v", now=FIXED_NOW)
        assert signed.headers["X-Content-Sha256"] == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
