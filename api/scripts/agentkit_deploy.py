#!/usr/bin/env python3
"""Push the agent definition to AgentKit over the BytePlus OpenAPI.

The pipeline this closes:

    api/kb/*.md  →  build_agentkit_yaml.py  →  agentkit_deploy.py  →  live agent

Credentials come from the environment and are never printed:

    BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY   (Console → User Profile → IAM → Key Management)

Start by discovering what your account actually has — this one call proves the credentials,
the region and the service name all line up before anything is changed:

    python scripts/agentkit_deploy.py list

Then:

    python scripts/agentkit_deploy.py update \
        --runtime-id <id> --yaml ../nexus_namecard_faq_assistant.yaml
    # add --dry-run to print the signed request instead of sending it

## What is verified and what is not

The signing scheme (Volc V4) is fully specified and unit-tested, and the endpoint
convention `{service}.{region}.byteplusapi.com` is from the BytePlus SDK docs. What no
public document pinned down for us is the **service name** AgentKit registers under and the
exact request body of `UpdateRuntime`. Both are flags with sensible defaults rather than
hardcoded guesses:

    --service   (default: agentkit)     override if `list` returns 404/UnknownService
    --region    (default: ap-southeast-1)

Run `list` first. If it returns runtimes, everything else is correct. If it fails, the error
body from BytePlus names what is wrong — paste it and the flags get corrected in one edit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.deploy.byteplus import BytePlusSigner


def call(
    signer: BytePlusSigner, action: str, version: str, payload: dict[str, Any], dry_run: bool
) -> dict[str, Any] | None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else b""
    request = signer.sign(action=action, version=version, body=body)

    if dry_run:
        print(f"POST {request.url}")
        # Authorization carries a derived signature, not the secret, but there is no reason
        # to put it on a terminal or in CI logs.
        for key, value in request.headers.items():
            print(f"  {key}: {'<signed>' if key == 'Authorization' else value}")
        print(f"  body: {body.decode('utf-8') or '(empty)'}")
        return None

    response = httpx.post(
        request.url, headers=request.headers, content=body, timeout=60.0
    )
    text = response.text
    try:
        data = response.json()
    except ValueError:
        print(f"HTTP {response.status_code}, 非 JSON 返回:\n{text[:600]}", file=sys.stderr)
        raise SystemExit(2) from None

    # BytePlus wraps errors inside a 200 as often as it uses a 4xx.
    error = (data.get("ResponseMetadata") or {}).get("Error")
    if error or response.status_code >= 400:
        print(f"HTTP {response.status_code}", file=sys.stderr)
        print(json.dumps(error or data, ensure_ascii=False, indent=2)[:900], file=sys.stderr)
        raise SystemExit(2)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["list", "get", "update"])
    parser.add_argument("--service", default=os.getenv("AGENTKIT_SERVICE", "agentkit"))
    parser.add_argument("--region", default=os.getenv("AGENTKIT_REGION", "ap-southeast-1"))
    parser.add_argument("--api-version", default=os.getenv("AGENTKIT_API_VERSION", "2024-01-01"))
    parser.add_argument("--runtime-id", default=os.getenv("AGENTKIT_RUNTIME_ID", ""))
    parser.add_argument("--yaml", type=Path, help="Agent YAML from build_agentkit_yaml.py")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        signer = BytePlusSigner(
            os.getenv("BYTEPLUS_ACCESS_KEY", ""),
            os.getenv("BYTEPLUS_SECRET_KEY", ""),
            service=args.service,
            region=args.region,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"endpoint: {signer.host}  ·  service={args.service}  region={args.region}")

    if args.command == "list":
        data = call(signer, "ListRuntimes", args.api_version, {}, args.dry_run)
        if data:
            print(json.dumps(data.get("Result", data), ensure_ascii=False, indent=2)[:2000])
        return 0

    if not args.runtime_id:
        print("--runtime-id 必填（先跑 list 拿到）", file=sys.stderr)
        return 1

    if args.command == "get":
        data = call(
            signer, "GetRuntime", args.api_version, {"Id": args.runtime_id}, args.dry_run
        )
        if data:
            print(json.dumps(data.get("Result", data), ensure_ascii=False, indent=2)[:2000])
        return 0

    # update
    if not args.yaml or not args.yaml.is_file():
        print("--yaml 必填，且文件要存在（先跑 build_agentkit_yaml.py）", file=sys.stderr)
        return 1
    definition = args.yaml.read_text(encoding="utf-8")
    print(f"agent 定义 {len(definition):,} 字符 ← {args.yaml.name}")

    data = call(
        signer,
        "UpdateRuntime",
        args.api_version,
        {"Id": args.runtime_id, "Definition": definition},
        args.dry_run,
    )
    if data:
        print("✓ 已提交")
        print(json.dumps(data.get("Result", data), ensure_ascii=False, indent=2)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
