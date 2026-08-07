---
id: entry-points-and-memory
title: Where you use it, and how it remembers / 三个入口与记忆
tags: [entry-points, whatsapp, mcp, memory, context, surfaces, WhatsApp, 微信里能用吗, 手机上能用吗, 在哪里用, 入口]
weight: 1.0
---

## Three ways in, one brain

| Entry point | What it is |
|---|---|
| **Ask Nexus (web)** | The main surface inside the platform. The conversation *is* the product — it sits on every page rather than in a separate chat window. |
| **External MCP** | `mcp.noahnexus.ai/mcp`. An RM connects Nexus from inside their own AI client — Claude, Manus and others — without logging into our web app at all. |
| **WhatsApp** | Bind by scanning a code and accepting the terms, then talk to the bot directly. It covers most of what the platform does. Conversations flow back into the platform history, tagged as WhatsApp. |

The point is not "we have integrations". It is that the same data, the same permissions and
the same audit trail sit under all three. A conversation that starts in WhatsApp is as
traceable as one that starts in the web app.

## 三个入口，一颗大脑（中文）

- **Ask Nexus 网页端** —— 平台内主入口，对话即产品，嵌在每一个页面里，而不是另开一个聊天窗。
- **外部 MCP** —— `mcp.noahnexus.ai/mcp`，RM 在自己的 Claude、Manus 等 AI 客户端里直接连，
  完全不用登录我们的网页。
- **WhatsApp** —— 扫码绑定 + 同意条款后直接对话，覆盖平台大部分功能；对话会回流到平台历史记录
  并带 WhatsApp 标识。

重点不是"我们有很多集成"，而是**三个入口底下是同一份数据、同一套权限、同一条审计链路**。
从 WhatsApp 发起的对话，和从网页发起的一样可追溯。

## How it gets to know you

Two kinds of memory, kept deliberately separate so they cannot contaminate each other.

**Long-term memory (automatic)** — during idle hours the system reviews the day's active
conversations, summarises them, and decides what is worth keeping. What it keeps falls into
four kinds: **facts, key points, preferences, and reflections**. Next time a related topic
comes up, the relevant memory is recalled and shapes the answer.

**Your own notes (manual)** — say "remember this" in any channel and it gets written down.
The AI guesses which client it belongs to and offers a confidence, but **a human decides**
before it is linked to a client. These notes deliberately stay out of the main memory store:
they are a notebook, and keeping them separate keeps them true.

## 记忆：越用越懂你（中文）

两套并行，刻意隔开，互不污染。

**长期记忆（AI 自动）** —— 空闲时段回顾当天的活跃对话、做摘要、判断哪些值得留下。留下来的分四类：
**事实 / 要点 / 喜好 / 反思**。下次触发相关话题时自动召回，用来修正答案。

**随手记（人手动）** —— 在任何渠道说「帮我记住 xxx」就会落库。AI 会猜它属于哪个客户并给出置信度，
但**必须由人拍板**才真正绑定到某个客户。这类笔记刻意**不进**大记忆库 —— 它就是个备忘录，隔开才
保证真实、不污染主记忆。
