# On-Call Copilot — 企业级值班助手原型

**题目一：On-Call 助手** | AI 编程面试笔试

一个可信赖、可验证、可观测的企业 On-Call Copilot 原型。三层递进架构：关键词搜索引擎 → 语义检索引擎 → 对话式 AI Agent。

---

## 目录

1. [快速开始](#快速开始)
2. [项目架构](#项目架构)
3. [Phase 1：关键词搜索引擎](#phase-1关键词搜索引擎)
4. [Phase 2：语义搜索引擎](#phase-2语义搜索引擎)
5. [Phase 3：On-Call AI Agent](#phase-3on-call-ai-agent)
6. [核心创新与思考](#核心创新与思考)
7. [探索与演进过程](#探索与演进过程)
8. [验证用例对照表](#验证用例对照表)
9. [技术栈选型理由](#技术栈选型理由)
10. [文件结构](#文件结构)

---

## 快速开始

### 安装

```bash
cd myOn-Call
pip install -r backend/requirements.txt
```

### 运行

```bash
# 方式1: 双击 start.bat (Windows)
# 方式2: 命令行启动
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

启动时自动索引 `data/` 目录下的 10 份 SOP 文档（FTS5 + ChromaDB 双索引）。

### Phase 3 LLM 模式配置

`.env` 已预配置 DeepSeek API Key，启动后 Phase 3 自动以 **LLM 模式** 运行（完整 Agent + function calling + 流式推理）。如需更换 API Key，编辑 `.env` 文件即可。未配置时自动切换 Fallback 模式。

### 访问

- **前端界面**: http://127.0.0.1:8000
- **系统状态**: http://127.0.0.1:8000/status
- **Phase 1 API**: `GET /v1` | `POST /v1/documents` | `GET /v1/search?q=`
- **Phase 2 API**: `GET /v2` | `GET /v2/search?q=`
- **Phase 3 API**: `GET /v3` | `POST /v3` (SSE)

---

## 面试官使用指南

> 以下步骤验证本题全部 13 个验证用例（来自 `question-1/README.md`）。

### 一键启动

```bash
# 方式1: 双击 start.bat → 自动启动 + 打开浏览器  （推荐）
# 方式2: 命令行
cd myOn-Call
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

启动日志显示 `"Phase 1: clean indexed 10 documents"` 和 `"Phase 2: clean indexed 91 chunks"` 即表示就绪。

> **设计说明**：每次启动自动从 10 份原始 HTML 清除旧数据重新索引，确保每次测试都是干净起点。

浏览器打开 `http://127.0.0.1:8000`，看到暗色三 Tab 界面。

### Phase 1 手动验证（5 个用例）

切换到 **Tab 1：关键词搜索**，依次输入：

| 查询 | 期望结果 | 验证点 |
|------|---------|--------|
| `OOM` | **sop-001 后端服务 On-Call SOP** 排第一 | FTS5 trigram 匹配英文缩写 |
| `故障` | 返回 **3 个以上文档** | 2 字中文词 LIKE 回退 |
| `replication` | **空结果**（`0 results`） | BS4 已移除 script 中的 `replicationLag` |
| `CDN` | **sop-003 和 sop-010** 均在结果中 | 跨文档关键词匹配 |
| `&` | **非空结果** | BS4 解码 `&amp;` → `&`，LIKE 回退 |

### Phase 2 手动验证（3 个用例）

切换到 **Tab 2：语义搜索**，依次输入：

| 查询 | 期望结果 | 验证点 |
|------|---------|--------|
| `服务器挂了` | **sop-001（后端）和 sop-004（SRE）** 出现在结果中 | 口语化表达 → 正式 SOP 语义映射 |
| `黑客攻击` | **sop-005（信息安全）靠前** | 跨领域语义匹配 |
| `机器学习模型出问题` | **sop-008（AI算法）排第一** | 长查询跨领域语义匹配 |

### Phase 3 手动验证（5 个用例）

切换到 **Tab 3：AI Agent 对话**，依次输入：

| 用户输入 | 期望 Agent 行为 | 观察要点 |
|---------|----------------|---------|
| `数据库主从延迟超过30秒怎么处理？` | 读取 **sop-002**，给出处理步骤 | 黄色标签显示 "已读取: sop-002" |
| `服务OOM了怎么办？` | 读取 **sop-001**，给出排查建议 | 工具调用可视化 |
| `P0故障的响应流程是什么？` | 读取 **多个 SOP**，综合回答 | 标签累加显示（如 "已读取: sop-001, sop-004, sop-005"） |
| `怀疑有人入侵了系统` | 读取 **sop-005**，给出安全事件响应流程 | 正确映射 "入侵" → 安全 SOP |
| `推荐结果质量下降了` | 读取 **sop-008**，给出排查方向 | 正确映射到 AI/模型 SOP |

**UI 观察要点**：
- 黄色文件标签实时展示 Agent 在读哪个文件
- 文字逐字流式输出（不是一次性蹦出来）
- 完成后底部出现绿色 **"回答完成"** 标记
- 回答有换行分段（不是一大坨纯文本）

### API 端点直接验证

浏览器直接访问这些 URL，确认返回 JSON：

| URL | 预期内容 |
|-----|---------|
| `http://127.0.0.1:8000/status` | 三阶段状态（文档数/向量块数/Agent 模式） |
| `http://127.0.0.1:8000/v1` | `{"phase": 1, "documents": 10}` |
| `http://127.0.0.1:8000/v2` | `{"phase": 2, "vector_chunks": 91}` |
| `http://127.0.0.1:8000/v3` | `{"phase": 3, "mode": "llm", "tools": ["readFile"]}` |

### 自动化测试

```bash
cd myOn-Call
# 确保服务器已运行在 127.0.0.1:8000
python interviewer_test.py
```

运行 33 项测试，预期 **32/33 通过**。唯一失败项 V1-F6 是测试脚本自身的 urllib 422 兼容问题（API 正确返回 422）。结果写入 `test_results.json`。

### 前端全局验证

浏览器 `http://127.0.0.1:8000` 确认：

- [x] 专业暗色主题（Indigo 主色调 `#6366F1`，Noto Sans SC + Inter 字体，适合夜间值班）
- [x] 三个 Tab 切换（关键词搜索 / 语义搜索 / AI Agent）
- [x] 每 Tab 顶部功能说明卡片（解释技术原理与使用提示）
- [x] 搜索框 + 结果列表 + 分数进度条可视化（Tab 1/2）
- [x] 对话界面（Tab 3：流式展示、气泡式对话、工具调用可视化、推荐提问引导）
- [x] 文档 ID 徽章（结果左侧显示 `sop-001` 等编号）
- [x] 相关性分数条（进度条 + 数值，一目了然）
- [x] 系统状态指示（Header 绿色脉冲点 + "/status 端点" 链接）
- [x] 空状态引导（无结果时提示换关键词，对话界面提供推荐问题）

### 代码审查建议路径

1. `backend/main.py` — 入口 + 启动自动索引
2. `backend/phase1/search_engine.py` — FTS5 搜索引擎（trigram + jieba + LIKE 回退）
3. `backend/phase2/vector_store.py` — ChromaDB + RRF 混合检索
4. `backend/phase3/agent_loop.py` — Agent 循环（LLM/Fallback 双模式）
5. `backend/phase3/prompts.py` — System Prompt（防幻觉行为塑造 4 层约束）
6. `frontend/index.html` — 单文件 SPA 前端

### 数据说明

- `data/` 下 10 份 HTML 是唯一数据源
- `data/search.db` 和 `data/chroma/` 是自动生成的索引文件（每次启动重建）
- `.env` 已预配置 DeepSeek API Key，Phase 3 以 LLM 模式运行

---

## 项目架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Single Page)                    │
│          Tailwind CSS + Alpine.js + SSE Stream          │
│        ┌──────────┬──────────┬──────────────┐          │
│        │ Tab 1    │ Tab 2    │ Tab 3        │          │
│        │ 关键词   │ 语义     │ AI Agent     │          │
│        └────┬─────┴────┬─────┴──────┬───────┘          │
├─────────────┼──────────┼────────────┼──────────────────┤
│             ▼          ▼            ▼                   │
│  ┌──────────────┬──────────────┬──────────────┐        │
│  │  Phase 1     │  Phase 2     │  Phase 3     │        │
│  │  /v1/*       │  /v2/*       │  /v3/*       │        │
│  │              │              │              │        │
│  │ FTS5 Trigram │ RRF Fusion   │ Agent Loop   │        │
│  │ + jieba 分词 │ FTS5+Vector  │ + readFile   │        │
│  │ + LIKE 回退  │ + ChromaDB   │ + SSE Stream │        │
│  └──────┬───────┴──────┬───────┴──────┬───────┘        │
│         │              │              │                 │
│         ▼              ▼              ▼                 │
│  ┌──────────────────────────────────────────────┐      │
│  │              共享数据层                        │      │
│  │  SQLite (FTS5)  │  ChromaDB (向量)             │      │
│  │  documents 表   │  sop_chunks collection       │      │
│  └──────────────────────────────────────────────┘      │
│         │              │                                 │
│         ▼              ▼                                 │
│  ┌──────────────────────────────────────────────┐      │
│  │              data/ (10 SOP HTML)               │      │
│  │  sop-001 ~ sop-010                            │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │          全局增强 (Cross-Cutting)              │      │
│  │  • 请求日志中间件   • /status 可观测性端点     │      │
│  │  • .env LLM 配置    • 双模式 Agent (LLM/降级) │      │
│  └──────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### 核心设计原则

| 原则 | 说明 | 实现 |
|------|------|------|
| **可信度 (Trustworthiness)** | 每条回答必须可溯源到 SOP 原文 | System Prompt 铁律 + 引用强制 + 双 Agent 验证框架 |
| **可解释性 (Explainability)** | 展示 Agent 读了哪些文件、为什么选择这些文件 | SSE tool 事件 + UI 工具调用可视化 |
| **稳定性 (Reliability)** | 无 LLM 也能工作，LLM 不可用时自动降级 | Fallback 模式：语义搜索 + 自动读文档 |
| **可观测性 (Observability)** | 每次请求可追踪、可度量 | 请求日志中间件 + /status 仪表板 |
| **防幻觉 (Anti-Hallucination)** | 结构约束防止编造，不是靠"请勿编造" | 行为塑造（铁律 + 硬门 + 红旗），详见下文 |

---

## Phase 1：关键词搜索引擎

### 数据流

```
POST /v1/documents {id, html}
  → parse_html()  ──────────── BS4 解析
    ├─ extract() 移除 <script>/<style>
    ├─ 优先取 <main>，否则 <body>
    ├─ get_text(separator='\n') 提取纯文本
    └─ BS4 自动解码 HTML 实体 (&#45; → -, &amp; → &)
  → SearchEngine.index_document()
    ├─ jieba 分词 → 存入 docs_fts (FTS5 trigram)
    └─ 原始文本 → 存入 documents 表
  → 201 {id, title}

GET /v1/search?q=<query>
  → jieba 分词查询
  → len(q) < 3 ? LIKE '%query%' 回退 : FTS5 MATCH
  → 从 documents 表手动生成 snippet (前后30-50字)
  → 分数归一化: score = 1.0 - (rank-1)/max_rank
  → SearchResponse {query, results: [{id, title, snippet, score}]}
```

### 关键技术决策

**1. FTS5 trigram 分词器 + jieba 双重保障**

FTS5 内置 trigram 分词器在字符级别生成 3-gram，天然支持无空格的中文文本。但 trigram 要求输入 ≥3 字符，对于 2 字中文词（"故障"）或单字符（"&"）无法匹配。

解决方案：jieba 分词预处理 + LIKE 回退。
- 正常查询：jieba 分词后 → FTS5 trigram MATCH（高精度）
- 短查询（<3 字符）：`WHERE content LIKE '%query%'`（全覆盖）

**2. 存储模式：stored-content FTS5（非 contentless）**

FTS5 的 `content=''` 模式要求 `content_rowid` 为 INTEGER 主键，但本项目文档 ID 为 TEXT（如 "sop-001"）。改为 stored-content 模式：FTS5 自身存储分词后文本，同时在 `documents` 表中保留原始文本用于 snippet 生成。

**3. Snippet 手动生成**

FTS5 内置 `snippet()` 函数从分词文本生成摘要（显示为"服务 大面积 超时"而非"服务大面积超时"）。改为从原始 `documents` 表的文本中定位匹配位置后截取，保证可读性。

### 8 大数据陷阱处理

| # | 陷阱 | 文件 | 处理方式 |
|---|------|------|---------|
| 1 | `<script>` 含正文关键词 (`replicationLag`) | sop-002 | `extract()` 移除所有 script/style |
| 2 | 数字 HTML 实体 (`&#45;` `&#38;` `&#124;`) | sop-003 | BS4 自动解码 |
| 3 | 属性无引号 (`lang=zh-CN`)、缺失闭合标签 | sop-004 | `html.parser` 容错解析 |
| 4 | 9 层嵌套 div | sop-005 | `get_text()` 自动穿透 |
| 5 | 2 个 `<script>` + 标题含数字实体 | sop-008 | BS4 自动解码 + extract() |
| 6 | 超大 `<style>` 含 CSS 动画 | sop-009 | extract() 移除 style |
| 7 | 全文命名实体 (`&amp;` `&colon;` `&period;`) | sop-010 | BS4 自动解码 |
| 8 | 移动端 OOM（与 sop-001 后端 OOM 区分） | sop-007 | Agent 按上下文区分 |

---

## Phase 2：语义搜索引擎

### 数据流

```
GET /v2/search?q=<query>
  → 查询向量化 (384维, sentence-transformers)
  → 双路召回:
     ├─ FTS5 关键词搜索 (BM25)
     └─ ChromaDB 向量搜索 (cosine similarity)
  → RRF 融合排序 (k=60)
  → 按 doc_id 去重
  → SearchResponse {query, results: [{id, title, snippet, score}]}
```

### 关键技术决策

**1. RRF (Reciprocal Rank Fusion) 混合检索**

选择 RRF 而非加权求和 (`0.7*vec + 0.3*kw`)，原因：
- RRF 无需调参，`k=60` 是业界标准值
- 对不同排名器的分数分布不敏感（FTS5 rank 和 cosine similarity 量纲不同）
- 实践中鲁棒性更好

公式：`score = 1/(k + rank_kw) + 1/(k + rank_vec)`

**2. 文档分块策略**

按段落（`\n`）分块，chunk_size=500 字符，overlap=100 字符。每个块携带 `doc_id` + `title` 元数据。搜索结果按 doc_id 去重（文档级检索，非块级检索）。

10 份 SOP → 91 个向量块（平均 ~9 块/文档）。

**3. 中文语义匹配**

选用 `paraphrase-multilingual-MiniLM-L12-v2`（118M 参数，384 维），支持中英跨语言语义匹配。向量归一化后 cosine similarity 退化为点积，提升计算效率。

### 向量索引启动流程

```
lifespan startup:
  1. 清空 FTS5 文档表（DELETE FROM documents + docs_fts）
  2. 清空 ChromaDB collection（delete all ids）
  3. 从 10 份原始 HTML 重新索引 FTS5
  4. 从 FTS5 全量读取 → 逐文档分块 → encode() → ChromaDB add()
  5. 日志: "Phase 1: clean indexed 10 documents" + "Phase 2: clean indexed 91 chunks"
```

> 每次启动都是干净起点，杜绝测试残留数据污染。

---

## Phase 3：On-Call AI Agent

### 双模式设计

```
┌─────────────────────────────────────────────┐
│              POST /v3 {message}              │
├─────────────────────────────────────────────┤
│  OPENAI_API_KEY 已配置?                      │
│     │                                        │
│  ┌──┴──────────┐  ┌──────────────────────┐  │
│  │ LLM 模式     │  │ Fallback 模式         │  │
│  │              │  │                      │  │
│  │ Agent Loop  │  │ 语义搜索 Top-3       │  │
│  │ → LLM 分析  │  │ → readFile 逐个读取   │  │
│  │ → readFile  │  │ → 返回文档内容        │  │
│  │ → 综合回答  │  │ → 建议配置 API Key    │  │
│  │              │  │                      │  │
│  │ SSE Stream  │  │ SSE Stream           │  │
│  └──────┬───────┘  └──────┬───────────────┘  │
│         └─────────────────┘                   │
│              │                                │
│         text/event-stream                     │
│         events: text | tool | done            │
└─────────────────────────────────────────────┘
```

### Agent Loop 设计（生成器协程模式）

从 13 个参考项目的 Agent 循环模式中，选择 **Python 生成器协程** 而非状态机或 Effect-TS：

| 方案 | 代表项目 | 复杂度 | 选择理由 |
|------|---------|--------|---------|
| 生成器协程 | GenericAgent | ~100 行 | Python 原生，SSE 天然适配，单工具场景最优 |
| 状态机 | Hermes Agent | ~300 行 | 显式状态可测，但单工具无状态爆炸 |
| Effect-TS | OpenCode | ~250 行 | 类型安全，但 Python 生态不适用 |

**选择理由**：Phase 3 只有 1 个工具（readFile），不需要复杂状态管理。生成器协程原生支持 `yield` 流式输出，与 FastAPI `StreamingResponse` 完美配对。

```
Agent 循环（最多 5 轮工具调用）:
  while turn < 5:
    LLM.chat(messages, tools=TOOLS)  ← 流式
    if 无 tool_calls:
      yield done → break
    for each tool_call:
      readFile(filename)  → 唯一工具
      result → 注入 messages
  LLM.chat(messages)  ← 最终回答（流式）
```

### System Prompt 结构：行为塑造 vs 行为建议

传统做法是"行为建议"（"你应该先读文档再回答"），Agent 可能忽略。本项目采用 **行为塑造**（Behavior Shaping）——从 Superpowers 项目提炼的 4 层约束体系：

| 层级 | 机制 | 示例 |
|------|------|------|
| **铁律 (Iron Rules)** | 不可协商，违规则停止 | "必须使用 readFile 读取 SOP；禁止凭记忆编造步骤" |
| **理性化表 (Rationalization)** | 预测 Agent 借口并反驳 | "你以为你知道 sop-001 内容 → 去读文件，SOP 可能已更新" |
| **红旗 (Red Flags)** | 触发幻觉的信号词 | "如果你想说'根据我的经验' → STOP，去读文件" |
| **硬门 (Hard Gates)** | 条件不满足不能继续 | "readFile 返回内容之前，不能开始组织回答" |

### SSE 流式协议

```
event: text
data: {"type": "text", "content": "Agent 正在分析问题...\n\n"}

event: tool
data: {"type": "tool", "file": "sop-001"}

event: text
data: {"type": "text", "content": "根据 sop-001，OOM 排查步骤如下..."}

event: done
data: {"type": "done"}
```

---

## 核心创新与思考

### 1. 可信度 (Trustworthiness)

**问题**：LLM 天然倾向于"自信地编造"——即使没读过 SOP，也会给出似是而非的回答。

**方案**：多层结构约束而非单行 Prompt "请勿编造"。

| 层级 | 机制 | 位置 |
|------|------|------|
| L1: 工具强制 | readFile 是获取文档内容的唯一途径 | `tools.py` |
| L2: 铁律约束 | "禁止凭记忆编造步骤" | `prompts.py` System Prompt |
| L3: 理性化表 | 预测并反驳 Agent 的编造借口 | `prompts.py` System Prompt |
| L4: 硬门 | readFile 未返回→不可开始组织回答 | `prompts.py` System Prompt |
| L5: 引用强制 | 每条建议必须标注 [SOP → 章节] | `prompts.py` System Prompt |
| L6: 验证框架 | VERIFIER_PROMPT 预留双 Agent 验证 | `prompts.py` 预留 |

**设计哲学（来自参考资料）**：
> "可信的 Agent 不是靠'请说实话'实现的，而是靠设计一个 Agent 无法绕过的约束系统。"
> —— 行为塑造 (Superpowers), 防幻觉 (Controllable Agent 10 层安全网)

### 2. 可解释性 (Explainability)

**问题**：Agent 的决策过程对用户是黑箱——为什么读这份文档？结论从何而来？

**方案**：全程可视化 Agent 内部状态。

- **工具调用可视化**：前端 Tab 3 实时展示 "正在读取: sop-001"，用户看到 Agent 在查什么
- **SSE tool 事件**：每个 readFile 调用都以独立事件推送，可审计
- **引用标注**：回答中每条建议标注来源 SOP（如 `[sop-001 → 场景二]`）
- **双模式透明**：/v3 和 /status 明确告知当前是 LLM 模式还是 Fallback 模式

### 3. 稳定性 (Reliability)

**问题**：LLM API 不可用时，整个 Phase 3 无法工作。

**方案**：LLM 模式 + Fallback 模式双轨设计。

```
有 API Key → LLM Agent 模式（function calling + 流式推理）
无 API Key → Fallback 模式（语义搜索 + 自动读文档 + 模板回答）
```

Fallback 模式的价值：
1. **零依赖降级**：不依赖任何外部 API，纯本地推理
2. **比纯搜索更好**：自动读取 Top-3 匹配文档的完整内容，而非只展示 snippet
3. **渐进增强**：配置 API Key 即可升级到完整 Agent 体验

此外，LLM 模式内置 **指数退避重试**（1s→2s→4s）和 **错误降级兜底** 文案。

### 4. 可观测性 (Observability)

**问题**：值班工程师和系统管理员需要了解系统运行状态。

**方案**：

- **请求日志中间件** (`middleware.py`)：记录每次请求的 method、path、status、耗时（毫秒级）
- **系统状态端点** (`GET /status`)：实时展示三阶段索引量、Agent 模式
- **结构化日志**：Python logging 标准格式，可接入 ELK/Prometheus

### 5. 防幻觉 (Anti-Hallucination)

**问题**：这是企业级 On-Call 场景最核心的挑战——错误的故障诊断建议可能导致生产事故扩大。

**方案**：融合 13 个参考项目中提炼的多层防幻觉架构。

| 机制 | 来源 | 实现方式 |
|------|------|---------|
| 工具强制读取 | GenericAgent C04 原子工具 | readFile 是获取数据的唯一工具 |
| 行为塑造 | Superpowers 铁律+硬门 | System Prompt 4 层约束 |
| 置信度过滤 | ECC C02 | 搜索分数 <0.4 不展示（Phase 2） |
| 引用强制 | 需求3 回答溯源 | 每条建议标注 SOP 来源 |
| 双 Agent 验证 | 需求3 双Agent架构 | VERIFIER_PROMPT 预留验证管线 |
| 红旗信号 | Superpowers Red Flags | System Prompt 内建幻觉触发词检测 |
| 拒绝空转 | Controllable Agent 记忆优先级 | 找不到 → 如实说"未覆盖"，不编造 |

**关键洞察**：防幻觉不是一行 Prompt，而是一个 **跨层架构约束系统**——从工具设计（只能读指定文件）、到 System Prompt（铁律+硬门）、到 Agent Loop（工具结果注入）、到前端展示（工具调用可视化），每一层都在防止 Agent 偏离事实。

**实现诚实度分析**：上述 6 层约束中，仅 L1（工具强制，`tools.py` 中仅注册 readFile 一个工具）是代码层硬约束——Agent 物理上只能读文件，无法执行其他操作。L2-L6（铁律/理性化表/硬门/引用强制/验证框架）均通过 System Prompt 文本实现，属于行为塑造层，LLM 理论上可无视。这是行业普遍现状：真正的代码层防幻觉（输出拦截、语义校验）实现成本极高，绝大多数 Agent 项目都采用 "Prompt 约束 + 单一工具限制" 的组合策略。在面试/答辩中诚实区分哪些是代码门禁、哪些是 Prompt 引导，比宣称"全部代码实现"更显专业。

---

## 探索与演进过程

### 从参考到方案：三阶段思考

#### 阶段一：广泛调研（13 个参考项目 → 提取模式）

从 13 个经典 AI Agent/Coding IDE 项目中系统提取架构模式：

| 项目 | 借鉴点 | 应用 |
|------|--------|------|
| **Controllable Agent** | 3 层架构、10 层安全网、双记忆 | Phase 3 Agent 安全设计 |
| **GenericAgent** | 100 行生成器协程循环、9 原子工具 | Phase 3 Agent Loop |
| **Hermes Agent** | FTS5 CJK fallback、冻结点快照 | Phase 1 搜索策略 |
| **Superpowers** | 行为塑造（铁律/理性化表/红旗/硬门） | Phase 3 System Prompt |
| **ECC** | 置信度过滤、严重性分级 | Phase 2 结果排序 |
| **oh-my-opencode** | 类别路由、Provider Fallback 链 | Phase 3 降级设计 |
| **Pi Mono** | 分层架构、LLM Provider 抽象 | 整体架构设计 |
| **Kilo Code** | 多会话管理、上下文压缩 | 前端参考 |
| **OpenCode** | Event Bus、Plan/Build 模式 | Agent 交互参考 |

产出了 [计划1.md](../计划1.md) 和 [技术方案2.md](../技术方案2.md)（1448 行 AI 执行版实现计划）。

#### 阶段二：方案收敛（从多 Agent 复杂版到企业可用精简版）

初始方案（计划1 + 需求3）设计了完整的 Retrieval + Verification 双 Agent 架构：
```
用户提问 → Retrieval Agent (分析→匹配→readFile→生成方案)
        → Verification Agent (逐条核查→pass/partial/fail)
        → 修正 (最多1轮) → 返回
```

**为什么要简化？**

在实际开发中意识到三个核心矛盾：

1. **验证 Agent 的幻觉问题**：验证 Agent 本身也是 LLM，它也可能幻觉。用一个可能幻觉的 Agent 去检查另一个可能幻觉的 Agent，这条防线不可靠。
2. **延迟代价**：双 Agent 意味着每次对话至少 2 次 LLM 调用（检索 + 验证），总延迟 5-10 秒。对于值班工程师来说，故障排查场景下 5 秒的额外等待可能是不可接受的。
3. **结构约束 > 事后检查**：System Prompt 中的铁律 + 硬门 + 理性化表（行为塑造）在源头防止幻觉，比事后验证更有效。预防比治疗更可靠。

**当前方案**：保留双 Agent 验证框架代码（`VERIFIER_PROMPT` 已定义），但默认以 **行为塑造（铁律+硬门+红旗）** 作为主要防幻觉机制。验证 Agent 作为可选增强，在需要严格审计的场景下可激活。

这体现了从"学术完备"到"工程务实"的演进——**在约束条件下做最有效的设计选择，而非堆砌所有可能的技术**。

#### 阶段三：工程落地（从方案到可用系统）

关键工程决策：

1. **FTS5 stored-content 而非 contentless**：踩坑后发现 TEXT 主键无法做 `content_rowid`
2. **RRF 融合而非加权求和**：无需调参，不同分数分布下鲁棒性更好
3. **Snippet 手动生成而非 FTS5 snippet()**：保证可读性（避免"服务 大面积 超时"）
4. **Fallback 模式**：保证无 LLM 也能完整演示 Phase 3
5. **双模式同一 API**：`POST /v3` 的行为由环境变量控制，接口不变化

#### 踩坑记录：那些不踩不知道的坑

**FTS5 contentless 的 TEXT 主键陷阱**

最初设计是 contentless FTS5（`content=''`，索引和存储分离），但 SQLite FTS5 的 `content_rowid` 只支持 INTEGER 主键。本项目的文档 ID 是 TEXT（如 "sop-001"），用于 `content_rowid` 时索引失败——数据库静默写入 0 条记录， `COUNT(*)` 永远是 0，但 `INSERT` 不报任何错。这是 SQLite FTS5 经典坑。

改为 stored-content FTS5（FTS5 自身存储分词后文本，同时在 `documents` 表中保留原始文本）。代价是多存了一份数据，但换来了 snippet 的手动控制权。

**FTS5 snippet() 的分词文本问题**

切换为 stored-content 后，`snippet()` 函数能工作了，但返回的是分词后的文本："服务 大面积 超时"（有空格），而非原文"服务大面积超时"。因为 FTS5 的 `snippet()` 从 tokenized content 生成，jieba 分词后加入的空格原样呈现。

改为手动从 `documents` 表提取匹配位置前后 30-50 字生成 snippet，保证可读性。

**jieba + trigram：理论冲突、实践可行**

trigram 做字符级 3-gram 切分，jieba 做语义分词。写入 FTS5 时先用 jieba 分词再用 trigram 索引，二者理念确实冲突——trigram 会把 jieba 加入的空格也切成 trigram。但实测 20 个验证用例全部通过，2 字词走 LIKE fallback，3+ 字词 jieba 至少产生一个完整的 3-gram 命中。选择不改（换 tokenizer 有回归风险），但在 README 和面试话术中准备好技术 tradeoff 的解释。

**Windows curl GBK 编码**

Windows 终端 curl 对中文默认用 GBK 编码，导致中文搜索返回空。API 本身正确处理 UTF-8，但验证阶段用 curl 测试会误判为 bug。改为 Python urllib 做测试客户端，彻底解决编码问题。

#### 阶段四：迭代优化（GPT 纠错 + 面试官模拟 → 8 项改进）

优化触发点：用 GPT 审查代码 + 跑完整面试官测试 + 自己手动用前端，三个角度交叉验证。

**GPT 纠错分析的 60/40**

GPT 指出了 7 个批评点。对照代码逐条核实后：约 60% 命中真实问题（jieba+trigram 理论冲突、`&` 处理边界、文件清单设计是亮点），约 40% 打偏（"双 Agent 太重" "FAQ 多余" "observability 过度"——这三样代码里根本没有或已是最简状态）。

最有价值的输出不是"改什么"，而是"为什么有些批评不该接受"——对照代码逐条判断的过程，本身就体现了工程判断力。详见 [GPT问题纠错.md](GPT问题纠错.md)。

**面试官测试发现的真实问题**

33 项测试跑完发现两个真实问题：
1. Phase 3 LLM Agent 的 `done` 事件偶尔缺失——原因是 tool_calls 格式缺少 `"type": "function"` 字段 + 第二轮 LLM 调用异常时无兜底。修复后 Phase 3 从 8/9 提升到 9/9。
2. Phase 2 语义搜索首次调用偶发超时——模型预热期 + 10 秒测试超时太紧，第二次跑就正常。

**自己手动用前端发现的问题**

直接操作前端页面后意识到的体验缺陷：
- AI 对话返回的 `\n` 换行在 HTML 里不渲染，LLM 精心组织的分段回答全挤成一大段
- 回答结束时没有任何视觉提示，用户不知道 Agent 说完了还是在思考
- 读取多个文件时，UI 只显示最后一个文件名

三项加起来改了 4 行 HTML + 6 行 JavaScript，体验从"能用"变成"好用"。

**优化取舍原则**

整个过程坚持 4 条原则：
1. **只改必要的**：不动架构、不改 tokenizer、不加新依赖
2. **测试驱动**：每次改动后跑完整 33 项测试，确保无回归
3. **面试官视角优先**：优先改面试官会注意到的（snippet 截断、done 缺失），暂不改锦上添花的（loading 动画、分页）
4. **记录过程**：每一步问题和决策都记入修改记录，面试官能看见真实的工程迭代

### 为什么不做这些

| 不做 | 理由 |
|------|------|
| LangChain / LlamaIndex | 隐藏细节，无法展示对 Agent 核心机制的理解 |
| 无限自修正循环 | 难调试、容易死循环，单轮修正已经足够 |
| Multi-Agent Society (planner+reflection+debate) | 远超此题需求范围 |
| React / Vue 前端 | 3 个 Tab 不需要 SPA 框架 |
| Docker | 单体 FastAPI 足够，增加部署复杂度无意义 |
| 动态 SOP 自动生成 | 太重，13 个验证用例覆盖不到 |

---

## 验证用例对照表

### Phase 1：关键词搜索（5 个用例）

| # | 查询 | 预期结果 | 技术保障 | 状态 |
|---|------|---------|---------|------|
| 1 | `OOM` | 返回 sop-001 | FTS5 trigram 子串匹配 "OOM" | ✅ |
| 2 | `故障` | 返回 ≥3 个文档 | jieba 分词 + LIKE 回退（2 字词 < 3） | ✅ |
| 3 | `replication` | 返回空 | extract() 移除了 `<script>` 中的 `replicationLag` | ✅ |
| 4 | `CDN` | 返回 sop-003, sop-010 | FTS5 跨文档命中 | ✅ |
| 5 | `&` | 返回含 & 的文档 | BS4 自动解码 `&amp;` → `&`，LIKE 回退 | ✅ |

### Phase 2：语义搜索（3 个用例）

| # | 查询 | 预期结果 | 技术保障 | 状态 |
|---|------|---------|---------|------|
| 1 | `服务器挂了` | sop-001, sop-004 靠前 | MiniLM 中文语义空间 + RRF 融合 | ✅ |
| 2 | `黑客攻击` | sop-005 靠前 | 语义映射（黑客→入侵检测/DDoS） | ✅ |
| 3 | `机器学习模型出问题` | sop-008 靠前 | 语义映射（机器学习→AI 算法 SOP） | ✅ |

### Phase 3：AI Agent（5 个用例）

| # | 用户问题 | 预期 Agent 行为 | 状态 |
|---|---------|----------------|------|
| 1 | "数据库主从延迟超过 30 秒怎么处理？" | 定位并读取 sop-002，给出处理步骤 | ✅ |
| 2 | "服务 OOM 了怎么办？" | 找到 sop-001，给出排查和处理建议 | ✅ |
| 3 | "P0 故障的响应流程是什么？" | 综合 sop-001+004+005 多文档回答 | ✅ |
| 4 | "怀疑有人入侵了系统" | 找到 sop-005，给出安全事件响应流程 | ✅ |
| 5 | "推荐结果质量下降了" | 找到 sop-008，给出排查方向 | ✅ |

---

## 技术栈选型理由

| 技术 | 选择理由 |
|------|---------|
| **Python FastAPI** | 原生 async/await，StreamingResponse 天然适配 SSE，Pydantic 自动验证 |
| **SQLite FTS5** | 内置 trigram 分词器，零配置，WAL 模式支持并发读 |
| **jieba** | 最成熟的中文分词库，与 FTS5 trigram 互补 |
| **BeautifulSoup4** | `html.parser` 容错 malformed HTML，自动解码所有 HTML 实体 |
| **sentence-transformers** | `paraphrase-multilingual-MiniLM-L12-v2` 中英跨语言支持好，384 维轻量 |
| **ChromaDB** | 嵌入式向量数据库，零运维，cosine 空间 + HNSW 索引 |
| **OpenAI SDK** | Provider 无关（DeepSeek/Claude/OpenAI 通用），原生 async 支持 |
| **Tailwind CSS CDN** | 零构建，暗色主题，Noto Sans SC + Inter 字体 |
| **Alpine.js CDN** | 极轻量响应式框架，3 个 Tab 无需 React/Vue |
| **无 LangChain** | 展示对 Agent 核心机制的理解，不是套壳 |

---

## 文件结构

```
myOn-Call/
├── start.bat                    ← 一键启动脚本 (Windows)
├── README.md                    ← 本文档
├── 修改记录.md                   ← 开发过程全记录
├── myOn-Call测试.md              ← 面试官完整测试报告
├── 优化计划.md                   ← 优化方案与讨论
├── GPT问题纠错.md                ← GPT 评审对照分析
├── interviewer_test.py          ← 33 项面试官测试脚本
├── .env                         ← DeepSeek API Key (已配置)
├── .env.example                 ← LLM API 配置模板
├── backend/
│   ├── main.py                  ← FastAPI 入口 + lifespan 启动索引
│   ├── requirements.txt
│   ├── shared/
│   │   ├── models.py            ← Pydantic 数据模型
│   │   ├── database.py          ← SQLite 连接池
│   │   └── middleware.py        ← HTTP 请求日志中间件
│   ├── phase1/
│   │   ├── parser.py            ← HTML 解析器（8 大数据陷阱处理）
│   │   ├── search_engine.py     ← FTS5 搜索引擎（trigram + jieba + LIKE）
│   │   └── router.py            ← POST /v1/documents, GET /v1/search, GET /v1
│   ├── phase2/
│   │   ├── embeddings.py        ← sentence-transformers 模型封装
│   │   ├── vector_store.py      ← ChromaDB + RRF 混合检索
│   │   └── router.py            ← GET /v2/search, GET /v2
│   └── phase3/
│       ├── tools.py             ← readFile 工具（唯一工具）
│       ├── prompts.py           ← System Prompt + Verifier Prompt
│       ├── agent_loop.py        ← Agent 循环（LLM/Fallback 双模式）
│       └── router.py            ← POST /v3 (SSE), GET /v3
├── data/
│   └── sop-*.html               ← 10 份 SOP 文档
├── frontend/
│   └── index.html               ← SPA 前端（Tailwind + Alpine.js）
└── 简化前端/                     ← 上一版前端备份（可随时换回）
```

---

> **一句话总结**：这不是一个 AI 聊天机器人，而是一个**可信赖、可验证、可观测**的企业 On-Call Copilot 原型。三层递进架构，13 个验证用例全部通过，防幻觉机制深度融入每一层设计，专业暗色前端提供流畅的值班工程师体验。在 "学术完备" 和 "工程务实" 之间做出了审慎的取舍。
