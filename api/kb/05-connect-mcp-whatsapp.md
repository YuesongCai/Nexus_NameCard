---
id: connect
title: Nexus Connect — MCP and WhatsApp / 入口层
tags: [connect, mcp, whatsapp, claude, chatgpt, manus, kimi, integration]
weight: 1.0
---

## Nexus Connect

Not another platform. One infrastructure, any entry point.

You already have your AI tools and your messaging apps. Nexus does not replace them — it
powers them. One shared data layer, one compliance gate, reachable from Claude, ChatGPT,
Manus, Kimi or WhatsApp. Same brain, wherever you work.

### Path A — AI tools (MCP)

Two ways in, one server: add Nexus as a custom MCP connector, or install it from your
tool's plugin store. One Nexus-account login and your AI has real client data, the product
shelf, and compliance-checked workflows.

MCP server endpoint: `https://mcp.noahnexus.ai/mcp` (Nexus login required)

| Tool | Route | Status |
|---|---|---|
| Claude | Custom connector + plugin store | Supported — recommended route |
| ChatGPT | Custom connector (needs paid workspace + developer mode) | Supported |
| Manus | MCP server / custom connector | Supported |
| Kimi | Plugin store install | Supported |
| Gemini | — | Not yet — no connector/plugin system to hook into |

### Path B — WhatsApp

RMs already live in WhatsApp. Nexus AI runs directly inside it — no extra app, no context
switching. Type it or say it: a voice note is transcribed and answered like any other
message. Ask questions, pull client data, build an RFQ, draft proposals. Same AI, same data,
same compliance gate as the full platform.

Only whitelisted identities get a reply — every channel is gated by a firm-managed allowlist
tied to the WhatsApp ID. Conversations are logged and audited. Per-tenant data isolation:
no client data crosses firm boundaries.

### Surfaces
Platform (web) · Connect (WhatsApp) · MCP clients · Mobile app (coming soon).

## Nexus Connect（中文）

不是又一个平台。一套底座，入口随你选。

你已经有自己的 AI 工具和常用聊天应用。Nexus 不替代它们，而是为它们提供底座。一套共享数据层、
一道合规闸门，从 Claude、ChatGPT、Manus、Kimi 或 WhatsApp 接入都是同一个大脑。

**路径 A —— AI 工具（MCP）**：两种接法同一个服务器 —— 作为自定义 MCP connector 添加，或从
工具的 plugin 商店安装。MCP 地址 `https://mcp.noahnexus.ai/mcp`，需 Nexus 账号登录。
Claude 体系最完整（推荐）；ChatGPT 需付费工作区并开启开发者模式；Manus 以 connector 为主；
Kimi 只有 plugin 商店；Gemini 暂不支持（其体系尚未开放）。

**路径 B —— WhatsApp**：RM 本来就在 WhatsApp 里工作，Nexus AI 直接在里面跑，无需额外安装。
打字或语音都行，语音会转成文字照常处理。提问、拉客户数据、建询价、起草方案。只有白名单身份
才会收到回复，对话全程留痕审计，租户级数据隔离。

### 四层架构 / Four-layer architecture

- **Layer 01 入口层 Entry points**（可替换）：Nexus Web、WhatsApp、任何 MCP 客户端
- **Layer 02 Harness 层**（竞争核心）：Agent 编排、62 个金融 skill、审计留痕
- **Layer 03 MCP 工具层**（薄接口）：产品域、客户域、交易域
- **Layer 04 底层能力**（护城河）：合规引擎、集成托管、清结算

最上面一层本来就该可替换 —— 价值在下面三层。
