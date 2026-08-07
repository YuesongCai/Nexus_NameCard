---
id: trust-and-audit
title: Trust, audit and data protection / 信任、留痕与数据保护
tags: [audit, security, pii, permissions, trail, write-operation, safety]
weight: 1.3
---

## Only one thing can write

Across everything the AI can reach, **exactly one action writes back to a business system**:
submitting an FCN request-for-quote. Everything else is read-only.

And even that one is deliberately two-step: the AI builds a **draft** for a human to look at,
and only after the human confirms does anything real get submitted. The draft tool does not
create an RFQ at all — it assembles terms locally and reads reference dictionaries.

**Design intent**: an AI that cannot move money, cannot place an order and cannot change an
account is a much smaller problem to govern than one that can.

## 唯一的写操作（中文）

AI 能触达的所有能力里，**只有一个动作会写回业务系统**：提交 FCN 询价单。其余全部只读。

而且这一个也刻意做成两步：AI 先出**草稿**给人看，人确认之后才真提交。草稿工具本身连询价单都
不会创建，只做本地条款组装和只读字典查询。

**设计意图**：一个不能动钱、不能下单、不能改账户的 AI，治理难度远小于一个能做这些事的 AI。

## Two hard gates on client data

**Object-level ownership gate** — the AI can only read clients belonging to the RM who is
asking. A request for someone else's client is refused outright, not filtered afterwards.
This is what stops horizontal privilege escalation.

**Output masking** — personally identifiable fields (phone, email) are stripped from tool
results *before* the model ever sees them. The model cannot leak what it was never given.

## 客户数据的两道硬闸（中文）

**对象级归属门** —— AI 只能读到当前 RM 名下的客户。跨客户取数直接拒绝，而不是取回来再过滤。
这是防止横向越权（IDOR）的那道门。

**出参统一脱敏** —— 手机、邮箱等 PII 在工具结果返回给模型**之前**就被抹掉。模型没拿到的东西，
它泄不出去。

## The audit trail

Every conversation can be exported as an audit pack: JSON plus a signed PDF, packed into a
zip, sealed with a chunked hash chain and archived to object storage. Old sessions can be
packed too, not just new ones.

There is an inspector panel where the trail is reviewable and downloadable, an operations log
that records who did what, and end-to-end timing broken down by thinking, tool calls and
gateway.

## 审计留痕（中文）

每一段对话都可以导出为审计包：JSON + 签名 PDF 打成 zip，用分块哈希链封印并归档到对象存储。
老会话也能补出包，不是只有新的才行。

配套有监察面板（可查看可下载）、操作日志（记录操作人）、以及端到端耗时拆分（思考 / 工具 / 网关）。

## Why this is the moat, not decoration

A regulated firm cannot adopt an AI it cannot explain after the fact. The trail is what makes
the answer defensible in an inspection — not the model, and not the interface.

## 为什么这是护城河而不是装饰

受监管机构不能用一个事后解释不清的 AI。监管现场检查时，能拿出来的是留痕，不是模型，也不是界面。
