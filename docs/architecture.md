# 名片系统架构：两条数据线，各自可插拔

## 这个 RAG 到底在干什么

名片机器人只有一个任务：

> **让扫码的人在 30 秒内知道 Nexus 是什么、正不正规、跟自己有没有关系，然后去找名片上那个人。**

它是**记性好的前台**，不是销售，也不是合规挡箭牌。

由此推出四条内容判准，KB 的每一段都要过：

| 判准 | 含义 | 反例 |
|---|---|---|
| **具体，但只用公开信息** | 官网上有的全都能说 | 「面向跨境财富管理需求客户的连接平台」—— 什么都没说，读起来像在回避 |
| **可验证的要讲透** | 牌照、上市代码、地址，藏起来只显得心虚 | 不敢讲 ARK 持 SFC 1/4/9 —— 这是公众记录册能查的 |
| **边界干脆，但不当万能挡箭牌** | 不给投资建议/报价/承诺，说一次说清 | 每个问题都答「看情况，问顾问」 |
| **终点是真人** | 答案落到名片主人 | 答完就结束，不给下一步 |

### 三个知识库，不要搞混

| KB | 读者 | 能讲什么 | 存放 |
|---|---|---|---|
| **名片 KB** | 扫码的陌生人 | 只讲官网已公开的：定位、货架、牌照、商业模式、怎么开始 | `api/kb/` |
| **展业 KB** | 自己人 / 合作机构 | 分润结构、合规实操、异议处理、话术红线 | 飞书文档，**不进名片** |
| 内部经济账 | BD / 顾问 | 票面空间分成测算 | 内部材料，**两个 KB 都不进** |

名片 KB 现约 22k 字符 ≈ **8.7k tokens** —— 这个量级**整个塞进模型上下文即可，不需要向量检索**。
涨到 3–5 万字符再考虑上检索或 AgentKit 企业知识库。

---

## 两条数据线

系统里只有两样东西会变，各自一条独立的线，互不影响：

```
① 知识线  api/kb/*.md ──build──> AgentKit Agent 的 instruction
② 名片线  企微智能表格 ──sync──> api/data/cards/*.json ──> 页面 + vCard + 二维码
```

**关键设计：两条线都是单向的，都有唯一源头。**
不存在「线上改一处、仓库改一处」然后两边打架的情况。

### ① 知识线：改 KB → 一条命令重建

源头是 `api/kb/` 下的 markdown，按 `##` 分章节，中英双语同段。

```bash
# 改完 kb/*.md 后
python api/scripts/build_agentkit_yaml.py --out nexus_namecard_faq_assistant.yaml
```

产出可直接在 AgentKit 控制台「导入 YAML」的文件。要增删知识，就是增删 `kb/` 下的 md，
**不用碰 YAML、不用碰代码**。

加一个新主题 = 新建一个 md；下线一个主题 = 删掉那个 md。这就是「干净插拔」。

### ② 名片线：改企微表 → 一条命令同步

源头是企业微信智能表格（同事自己填的那张）。

```bash
python api/scripts/sync_wecom.py            # 空跑，只报告
python api/scripts/sync_wecom.py --write    # 写入 card profiles
python api/scripts/export_static.py         # 重新导出页面数据
python api/scripts/gen_qr.py --png          # 重新生成每人二维码
```

`sync_wecom.py` 直接走企微 API 读表，**不需要手动导出 CSV**。
校验不通过（邮箱格式、电话非国际格式、持牌类别越界、slug 重复、本人未确认）就拒绝写入。

飞书那张表和本地 CSV 也支持，走 `import_sheet.py`。

---

## 运行时：AgentKit 只做「生成」，检索留在自己这边

```
浏览器
  → 我们的 FastAPI（/api/chat）
      ├─ 从 api/kb/ 取相关段落（BM25 + 可选向量）
      └─ 把「问题 + 检索到的段落」发给 AgentKit /run_sse
  ← SSE 流式回传
```

**为什么不把 KB 塞进 AgentKit 的 prompt：**
塞进去也能跑（8.7k tokens 完全够），但那样 KB 就有了两个源头 —— 仓库一份、控制台一份，
迟早不一致。让检索留在自己这边，**KB 永远只有 `api/kb/` 一个源头**，AgentKit 就是个模型端点。

两种模式都支持，用 `--mode` 切换生成哪种 YAML：

| 模式 | Agent 的 instruction | 适用 |
|---|---|---|
| `thin`（默认，推荐） | 只有角色与规则，知识每轮随问题传入 | 生产。KB 单一源头 |
| `baked` | 角色规则 + 整个 KB | 无后端的纯 AgentKit demo（如字节给的那个 zip） |

---

## 换成自己的 AgentKit 账号

字节给的 POC 里，Agent 建在他们的租户下，所以 `.env` 里那三个值指向他们那边。换成自己的：

1. 用自己的账号进 AgentKit 控制台 → 创建 Agent → **导入 YAML**（`build_agentkit_yaml.py` 产出的那份）
2. 拿到自己的 Runtime URL / App Name / API Key
3. 填进 `.env`：

```dotenv
NEXUS_CARD_LLM_PROVIDER=agentkit
NEXUS_CARD_AGENTKIT_BASE_URL=https://<你的-runtime>
NEXUS_CARD_AGENTKIT_APP_NAME=<你的-agent-应用名>
NEXUS_CARD_AGENTKIT_API_KEY=<你的-key>
```

这样 Agent、模型调用与账单全在自己名下。

---

## 迁到 AgentKit + BytePlus：现在缺什么

目标是整套（不只是对话）都跑在字节的服务上。下面是每一块对应什么，以及**我需要你给什么**才能动手。

### 已经就位

| 能力 | 现状 |
|---|---|
| 对话生成 | ✅ `agentkit` provider 已写好并测过（58 个测试）。填 `.env` 即用 |
| 知识库 | ✅ `api/kb/` → 一条命令生成 Agent YAML |
| 名片数据源 | ✅ 企微智能表格 → 一条命令同步（已连通你那张真表） |
| 前端 | ✅ 已上线，per-slug、vCard、微信、双语 |

### 还需要决策 / 需要你给的东西

| 系统组件 | 当前 | 迁到 BytePlus 的候选 | 我需要什么 |
|---|---|---|---|
| **Agent 运行时** | 字节租户上的 POC | AgentKit（你自己的账号） | Runtime URL / App Name / API Key |
| **名片数据** | 仓库里的 JSON 文件 | 表格服务或对象存储 | 你们能用哪个（veDB / RDS / TOS？）+ 连接方式 |
| **二维码图片、微信码** | 仓库 / 本地 | 对象存储 TOS + CDN | TOS bucket 与 AK/SK |
| **前端托管** | GitHub Pages | 静态托管 / veFaaS / CDN | 用哪个 |
| **后端 API** | 本地 / Docker | veFaaS 或容器服务 | 用哪个 |
| **知识库存储** | 仓库 markdown | 保持在仓库（推荐）或 AgentKit 企业知识库 | 见下 |

### 我的建议：分两步，别一次全搬

**第一步（现在就能做完）** —— 对话上 AgentKit，其余不动。
风险最小，能立刻验证 AgentKit 在真实流量下的表现。只需要你给三个环境变量。

**第二步（等第一步稳了）** —— 数据与托管迁 BytePlus。
这一步要改的是「名片数据从哪读」，代码里已经是一个 `CardStore` 抽象，换成读数据库或对象
存储是替换一个类，不是重写。

### 知识库放哪：建议仍留在仓库

AgentKit 有企业知识库能力（现在 YAML 里是关掉的）。但名片 KB 只有 **8.7k tokens**，
够小到可以整个进上下文 —— 上检索反而增加一个会漂移的副本。

建议：**知识留在 `api/kb/`（git 里可 review、可回滚），AgentKit 只当模型端点。**
等 KB 涨到 3–5 万字符再评估要不要上企业知识库。
