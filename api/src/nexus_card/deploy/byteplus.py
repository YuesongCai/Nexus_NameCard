"""BytePlus / Volcengine OpenAPI request signing (Volc V4).

Written by hand rather than pulled from the SDK because the deploy path needs exactly one
thing — a signed HTTP request — and the signing scheme is fully specified. Hand-rolling it
keeps CI free of a large SDK dependency and makes the signer itself unit-testable against
fixed inputs, which is the part that silently breaks.

Credentials come from the environment (`BYTEPLUS_ACCESS_KEY` / `BYTEPLUS_SECRET_KEY`) and
are never logged, never written to disk, and never passed on a command line.

Endpoint convention (per BytePlus docs):
    regional  {service}.{region}.byteplusapi.com
    global    {service}.byteplusapi.com
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
from dataclasses import dataclass
from urllib.parse import quote


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _canonical_query(params: dict[str, str]) -> str:
    # Sorted by key, RFC-3986 encoded — the server rebuilds this string exactly.
    return "&".join(
        f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}" for k, v in sorted(params.items())
    )


@dataclass(frozen=True)
class SignedRequest:
    url: str
    headers: dict[str, str]
    body: bytes


class BytePlusSigner:
    """Signs one OpenAPI request with the Volc V4 scheme."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        *,
        service: str,
        region: str,
        host: str | None = None,
    ) -> None:
        if not access_key or not secret_key:
            raise ValueError(
                "BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY are not set. "
                "Get them from BytePlus Console → User Profile → IAM → Key Management."
            )
        self._access_key = access_key
        self._secret_key = secret_key
        self.service = service
        self.region = region
        # Regional services carry the region in the host; global ones do not.
        self.host = host or f"{service}.{region}.byteplusapi.com"

    def sign(
        self,
        *,
        action: str,
        version: str,
        body: bytes = b"",
        method: str = "POST",
        path: str = "/",
        now: _dt.datetime | None = None,
    ) -> SignedRequest:
        now = now or _dt.datetime.now(_dt.UTC)
        x_date = now.strftime("%Y%m%dT%H%M%SZ")
        short_date = x_date[:8]

        params = {"Action": action, "Version": version}
        canonical_query = _canonical_query(params)
        payload_hash = _sha256_hex(body)

        signed_headers = "content-type;host;x-content-sha256;x-date"
        content_type = "application/json; charset=utf-8"
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{self.host}\n"
            f"x-content-sha256:{payload_hash}\n"
            f"x-date:{x_date}\n"
        )

        canonical_request = "\n".join(
            [method, path, canonical_query, canonical_headers, signed_headers, payload_hash]
        )

        credential_scope = f"{short_date}/{self.region}/{self.service}/request"
        string_to_sign = "\n".join(
            [
                "HMAC-SHA256",
                x_date,
                credential_scope,
                _sha256_hex(canonical_request.encode("utf-8")),
            ]
        )

        signing_key = _hmac(
            _hmac(
                _hmac(self._secret_key.encode("utf-8"), short_date),
                self.region,
            ),
            self.service,
        )
        signing_key = _hmac(signing_key, "request")
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"HMAC-SHA256 Credential={self._access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return SignedRequest(
            url=f"https://{self.host}{path}?{canonical_query}",
            headers={
                "Content-Type": content_type,
                "Host": self.host,
                "X-Date": x_date,
                "X-Content-Sha256": payload_hash,
                "Authorization": authorization,
            },
            body=body,
        )
