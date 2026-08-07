---
id: compliance
title: Compliance, licensing and audit / 合规、牌照与审计
tags: [compliance, sfc, mas, sec, hkma, audit, licence, regulatory, data, are you licensed, licensed, licence, 有没有牌照, 持牌吗, 合法吗, 正规吗]
weight: 1.05
---

## Licensing

Regulated where the clients are:

- **Hong Kong — SFC**, Type 1 (dealing in securities), Type 4 (advising on securities),
  Type 9 (asset management)
- **Singapore — MAS**, aligned to the Technology Risk Management guidelines
- **United States — SEC**, registered

Three licences, three booking centres, multi-custodian by default, and one compliance layer
under every workflow.

## How the AI stays compliant

Human-in-the-loop by design.

- Every AI decision is logged with inputs, reasoning trace and confidence score on an
  immutable audit trail.
- Pre-trade suitability and complex-product gating run automatically before any order
  leaves the system.
- AI drafts; the recommendation and the signature stay with the licensed advisor.
- Aligned with the HKMA GenAI framework, SFC Type 1/4/9 guidelines, MAS Technology Risk
  Management, and the SFC circular on generative AI language models, **SFO/IS/036/2024**.
- Any conversation exports as an audit pack — signed PDF plus JSON, sealed to WORM,
  retained seven years — with a SHA-256 hash chain a regulator can recompute independently.

## Data and security

- Per-tenant data isolation; client data does not cross firm boundaries.
- The client relationship and the data belong to the advisor, permanently, by contract.
- Nexus does not take over, contact or profile the advisor's clients; the client-facing
  surface carries the advisor's brand only.
- Channels (including WhatsApp) are gated by a firm-managed allowlist.

## 合规与牌照（中文）

**牌照**：香港 SFC 第 1 类（证券交易）、第 4 类（就证券提供意见）、第 9 类（资产管理）；
新加坡 MAS，对齐 TRM 指引；美国 SEC 已注册。三地牌照、三地 Booking Center、默认多托管，
所有工作流底下是同一层合规。

**AI 如何保持合规**：人在环内是设计前提。每一个 AI 判定都带输入、推理链与置信度写入不可篡改
审计留痕；交易前适当性与复杂产品闸门自动运行；AI 只起草，最终建议与签署由持牌顾问决定；
对齐 HKMA 生成式 AI 框架、SFC 第 1/4/9 类指引、MAS TRM，以及 SFC 生成式 AI 语言模型通函
SFO/IS/036/2024。任何对话都可导出审计包（签名 PDF + JSON，WORM 封存，保留 7 年），
SHA-256 哈希链监管可独立复算。

**数据与安全**：租户级数据隔离，客户数据不跨机构边界；客户关系与数据永久归属顾问并写入合同；
Nexus 不接管、不接触、不分析顾问的客户；客户端面仅呈现顾问品牌；渠道由公司管理的白名单把关。
