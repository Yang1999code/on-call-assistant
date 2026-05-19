# GPT 问题纠错

> 原文：某 AI 模型对 `myOn-Call` 方案的评审意见
> 分析日期：2026-05-15
> 分析者：基于实际代码对照

---

## 原文（保留）

> 你的方案整体已经不是"能做出来"的级别了，而是：
>
> **已经接近「高级工程师面试展示方案」**
>
> 尤其：Phase 分层、HTML parsing、FTS5、semantic retrieval、Agent loop、tool calling、hallucination verification、SSE、observability —— 这些都已经远超普通校招/初级候选人。
>
> 但你问的核心问题非常对："第一个问题（Phase1）到底这样处理对不对？"
>
> 这里我给你一个非常严格、面试官视角的分析。

---

### 一、你的 Phase1 最大问题

> 不是：BeautifulSoup、FTS5、jieba、trigram
>
> 这些都没问题。
>
> 真正的问题是：你现在的实现"理论上"有 bug，而且 bug 正好可能打在题目测试点上。

---

### 二、问题核心：FTS5 tokenizer 逻辑冲突

> 你现在写的是：
>
> ```
> tokenize='trigram'
> ```
>
> 然后：
>
> ```
> tokenized = ' '.join(jieba.cut(content))
> ```
>
> 这两个其实：**理念冲突**
>
> 因为 trigram tokenizer 会：
>
> ```
> CDN节点故障
> ↓
> CDN
> DN节
> N节点
> 节点故
> 点故障
> ```
>
> 它是：**字符级 3-gram**
>
> 而你又提前 jieba：
>
> ```
> CDN 节点 故障
> ```
>
> 写入 FTS。
>
> 于是 trigram 实际看到的是：
>
> ```
> C D N _ 节 点 _ 故 障
> ```
>
> 会生成：
>
> ```
> "CDN"
> "DN "
> "N 节"
> " 节点"
> ...
> ```
>
> 这会导致：**tokenizer 行为不可预测**

#### 对照代码 [search_engine.py:26-30](backend/phase1/search_engine.py#L26-L30)

实际代码：
```python
# Line 26: FTS5 表定义
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
USING fts5(id, title, content, tokenize='trigram')

# Line 30: 索引时
tokenized = ' '.join(jieba.cut(content))
# 存入: INSERT OR REPLACE INTO docs_fts(id, title, content) VALUES (?, ?, ?)
# 第三个参数是 tokenized（jieba分词后的文本）
```

**判定：此批评针对的代码真实存在。** `tokenize='trigram'` + `jieba.cut()` 确实同时出现在 [search_engine.py](backend/phase1/search_engine.py) 中。

**但实际影响需要精确分析：**

当 jieba 输出 `"CDN 节点 故障"` 存入 trigram FTS5 后：
- Trigram 产生：`"CDN"`, `"DN "`, `"N 节"`, `" 节点"`, `"节点 "`, `"点 故"`, `" 故障"`
- 查询 `"CDN 节点 故障"`（也经 jieba 切分后 MATCH）：同样 trigram 切分
- `"CDN"` 命中——匹配成功

当查询是 `"数据库"` (3字词，jieba 不拆分)：
- 查询 trigram：`"数据库"`（恰好 3 字符）
- 如果索引中 jieba 保留了 `"数据库"` 且位置恰好在 3-gram 窗口内 → 匹配
- 如果 `"数据库"` 前后有空格（如 `" 数据库 "`），trigram 产生 `" 数据"`, `"数据库"`, `"据库 "` → `"数据库"` 命中

当查询是 `"节点故障"` (不经过 jieba 的手输查询)：
- `len("节点故障")` = 4 ≥ 3 → 进入 FTS5 MATCH 分支
- jieba 切 "节点故障" → `"节点 故障"`
- 查询 trigram：`"节点 "`, `"点 故"`, `" 故障"`
- 索引中有 `"节点 "` 和 `" 故障"` → FTS5 OR 语义 → **匹配成功**

**结论：虽有理论冲突，但实际 20/20 测试全部通过。** 原因是 jieba 分词对 3+ 字查询至少产生一个完整的 3-gram 词，2 字查询走 LIKE fallback。冲突存在于"如果查询恰好是 jieba 无法切分的 3 字符组合"的边界情况，但不影响现有测试用例。

---

### 三、最严重的问题：&

> 题目专门给了：
>
> ```
> GET /v1/search?q=&
> ```
>
> 这是故意卡人的。
>
> 而：FTS5 MATCH 对特殊字符极不友好
>
> 例如：
>
> ```sql
> WHERE docs_fts MATCH '&'
> ```
>
> 很容易：syntax error / empty result / tokenizer ignore symbol
>
> 你虽然写了：
>
> ```python
> if len(query.strip()) < 3:
>     LIKE fallback
> ```
>
> 这个方向是对的。
>
> 但：这里真正应该做的是——

#### 对照代码 [search_engine.py:45-46](backend/phase1/search_engine.py#L45-L46)

实际代码：
```python
if len(q) < 3:
    # 短查询（如 & 或两字中文）：trigram 需要 3+ 字符 → LIKE 回退
    rows = self.conn.execute("""
        SELECT d.id, d.title,
               substr(d.content, max(1, instr(d.content, ?)-30), 80) as snippet,
               1 as rank
        FROM documents d
        WHERE d.content LIKE '%' || ? || '%'
        LIMIT ?
    """, (q, q, limit)).fetchall()
```

**判定：此批评部分成立，但现有防御已覆盖当前测试点。**

- `len("&") = 1 < 3` → 走 LIKE fallback → `LIKE '%&%'` → 匹配 `sop-003` 中的 `&#38;` → **测试通过**
- **但批评真正命中的边界是：** `"A&B"`（len=3≥3）→ 进 FTS5 MATCH → FTS5 的 trigram 处理 `&` 可能产生语法错误或静默忽略
- **更精确的防御：** 应改为特殊字符正则检测，而非仅靠长度 < 3

```python
# 推荐的更健壮方案（未实现）
SPECIAL_QUERY_RE = r'[&%_\\/\-]'
if len(q) < 3 or re.search(SPECIAL_QUERY_RE, q):
    # LIKE fallback
```

当前代码使用的 `len(q) < 3` 对 `&` 有效（长度1），但对 `A&B`（长度3）无效。不过 `A&B` 不在题目测试用例中。

---

### 四、真正推荐的高分 Phase1 方案

> 其实应该是：**"双通道搜索"** 而不是："FTS5 万能处理"
>
> **推荐结构：**
>
> 1. **主搜索：FTS5 BM25** — 负责中文词、英文词、普通检索（例如 `MATCH 'OOM'`、`MATCH '故障'`、`MATCH 'CDN'`）
> 2. **特殊字符 fallback：LIKE** — 专门处理 `&`、`%`、`_`、单字符、特殊符号
>
> 例如：`SPECIAL_QUERY_RE = r'^[^\w一-鿿]+$'`
>
> 如果 query 是 `&`：直接 `WHERE content LIKE '%&%'`
>
> 3. **不要"jieba + trigram 混合"** — 这是你当前最大技术债。

#### 对照分析

**批评成立。** 当前代码的方案不是"双通道"而是"长度分流"：

| 查询 | 长度 | 走什么 | 是否正确 |
|------|------|--------|----------|
| `&` | 1 | LIKE | ✓ |
| `故障` | 2 | LIKE | ✓ |
| `OOM` | 3 | FTS5 trigram | ✓ |
| `数据库` | 3 | FTS5 trigram | ✓ |
| `A&B` | 3 | FTS5 trigram | ⚠️ 可能异常 |
| `N/A` | 3 | FTS5 trigram | ⚠️ 可能异常 |

改为"特殊字符检测 + 长度"双条件后会更稳健。

---

### 五、你应该怎么改（重要）

> **方案 A（最稳）：**
>
> 直接：`tokenize='unicode61'`
>
> 然后：Python 自己做 query preprocessing
>
> 例如：
>
> ```python
> query_tokens = list(jieba.cut(query))
> fts_query = ' OR '.join(query_tokens)
> ```
>
> 为什么更好？因为：tokenizer 行为可控、中文明确、英文明确、ranking 稳定、面试官容易理解

#### 对照分析

**这个建议有道理但需要验证。** `unicode61` 是 FTS5 默认 tokenizer，对 CJK 字符按 Unicode 边界切分（每个汉字一个 token）。结合 `jieba.cut(query)` → `OR` 连接的 FTS5 查询，理论上是更干净的方案。

但需要注意：`unicode61` 对英文按空格/Punct 切分，对中文逐字切分。`jieba` 分出的多字中文词（如"数据库"）在 `unicode61` 中被拆成"数"/"据"/"库"，MATCH 时需要用 phrase query `"数据库"` 来匹配相邻 token。这需要额外处理。

**当前方案（trigram+jieba）的实际表现已验证 20/20 通过**，换方案需要重新跑全部测试。从"面试稳定性"角度看，改还是不改取决于：
- 改：更干净的架构，面试时好解释
- 不改：已通过全部验证用例，改动有引入新 bug 的风险

**倾向于暂不改，但面试时准备好解释 jieba+trigram 的 tradeoff。**

---

### 六、你当前 trigram 的问题（面试官可能追问）

> 面试官很可能问："既然用了 trigram，为什么还要 jieba？"
>
> 这是非常危险的问题。因为你现在：**很难逻辑自洽**

#### 对照分析

**这个批评精准。** 确实不好回答。一个可能的回答思路：

> "trigram 提供字符级的模糊匹配能力（容忍拼写差异），而 jieba 提供语义上有意义的分词边界。分开用各有问题：纯 trigram 无法理解中文词边界，纯 jieba + unicode61 无法处理未登录词。结合使用虽然理论不完美，但在实践中对中文短文档搜索效果最好。"

这个回答不完美，但比"没想过"强。

---

### 七、实际上你现在有点"过度工程化"

> 尤其：
> - **双 Agent 验证** — 非常加分，但可能太重了。题目重点是 retrieval + tool usage + agent reasoning，不是 AI safety research。
> - **FAQ cache** — 也有点重。
> - **observability** — 很好，但可能不如把时间花在 retrieval quality 上。

#### 对照代码

**批评在此项目代码上不成立。** 逐一对照：

**双 Agent 验证：** [prompts.py:26-34](backend/phase3/prompts.py#L26-L34) 定义了 `VERIFIER_PROMPT`，但在 [agent_loop.py](backend/phase3/agent_loop.py) 中**从未被调用**。README 和修改记录明确标注为"预留"。批评假设它在运行，实际上没有。

**FAQ cache：** 代码中**完全不存在** FAQ 缓存功能。批评基于 README 中的设计描述，而非实际实现。

**observability：** [middleware.py](backend/shared/middleware.py) 仅有 13 行的请求日志中间件（method + path + status + 耗时）+ [main.py:73-86](backend/main.py#L73-L86) 中的 `/status` 端点。这是最小极简的 observability，不存在"过度"。

**结论：批评的"过度工程化"观点针对的是 README 和设计文档中描述的"完整方案"，而非实际代码。实际代码相当精简。**

---

### 八、Phase3 其实你有一个真正的大亮点

> 就是：**文件清单 + 路由 hint**
>
> 这个特别好。因为题目限制：不能 list dir。很多人会让 Agent 瞎猜文件名、疯狂 hallucinate。而你主动给 Agent "已知文件清单"——符合限制、提高成功率、降低 token、更像真实生产系统。
>
> 这一点我会认为：是你整个方案里最专业的设计之一。

#### 对照代码 [prompts.py:3-13](backend/phase3/prompts.py#L3-L13)

```python
SYSTEM_PROMPT = """You are an On-Call Assistant AI...
You have access to these SOP documents:
- sop-001: 后端服务 On-Call SOP — backend service troubleshooting, OOM, latency
- sop-002: 数据库DBA On-Call SOP — database issues, connection pools, slow queries
...（10 份文件清单 + 一句话描述）
"""
```

**判定：此夸奖完全成立。** 代码确实在 System Prompt 中内嵌了文件清单 + 路由提示（每个文件一行描述），Agent 可以据此判断该读哪个文件。这是可控、高效、且符合题目约束的设计。值得保留并强调。

---

### 九、真正建议你删掉的东西

> 为了"更像一个优秀面试者"而不是"AI 堆料工程"：
>
> **建议删减：**
> - 删除：双 Agent verifier — 太重、latency 高、成本高、面试时间不够展示。改成"answer grounding check"即可（例如 `if not cited_sources: reject_answer()`）
> - 删除：FAQ cache — 没必要。100 个文档而已。
> - 简化：observability — 保留 `/status` 即可。别做太复杂。

#### 对照分析

| 建议删除 | 实际代码状态 | 处理 |
|----------|-------------|------|
| 双 Agent verifier | `VERIFIER_PROMPT` 定义但**未调用**，已是"预留"状态 | 保留删除 `VERIFIER_PROMPT` 定义即可，或者保留作为设计文档证据 |
| FAQ cache | **不存在** | 无需处理 |
| 简化 observability | 已是最简（13行中间件 + `/status`） | 无需处理 |

**判断：代码层面不需要删除任何东西。** 如果担心过度，最多把 `VERIFIER_PROMPT` 从 prompts.py 删掉（它占 9 行，定义了但从未用）。

---

### 十、你现在真正的最佳版本

> **Phase1：** BeautifulSoup + `unicode61` tokenizer + jieba query tokenize + BM25 + 特殊字符 LIKE fallback
> **Phase2：** 你的方案很好。真的很好。
> **Phase3：** 保留 tool calling + SSE + 文件路由 hint + hallucination guardrail。删掉 verifier agent + FAQ cache。

#### 对照分析

**当前方案与"最佳版本"的差异仅一处：**
- Phase1：当前是 `trigram` + jieba，建议是 `unicode61` + jieba query tokenize
- 其余（Phase2 RRF 混合搜索、Phase3 精简 Agent）**已经等于建议方案**

---

### 十一、最终评价（真实面试视角）

> 如果你按"精简优化版"实现出来：我会认为这是很强的候选人。
>
> 因为你已经展示了：搜索引擎基础、retrieval、vector search、agent、prompt engineering、streaming、backend architecture、observability、hallucination awareness。
>
> 而且：最重要的是：**你不是"套 LangChain"。你是真的理解：系统为什么这样设计。** 这个非常关键。

#### 总评

**这个评价大体公允。** 实际代码质量不错，设计思路清晰。批评中约 60% 命中了真实问题（trigram+jieba 冲突、& 处理的边界），约 40% 批评的是 README 里描述的设计而非实际代码（双Agent验证、FAQ缓存、observability过度）。

---

## 结论：批评中哪些该改、哪些别管

| # | 批评点 | 命中？ | 建议 |
|---|--------|--------|------|
| 1 | jieba + trigram 冲突 | ✅ 命中代码 | **可改可不改**。20/20 已通过，面试准备解释即可 |
| 2 | `&` 处理不够健壮 | ⚠️ 半命中 | **建议改**：加特殊字符正则检测，补充 `len<3` 的判断 |
| 3 | 双 Agent verifier 太重 | ❌ 代码中未实际运行 | 别管。VERIFIER_PROMPT 可保留作为设计文档 |
| 4 | FAQ cache 多余 | ❌ 代码中不存在 | 别管 |
| 5 | observability 过度 | ❌ 已是最简 | 别管 |
| 6 | 文件清单+路由hint 是亮点 | ✅ 正确肯定 | 保持 |
| 7 | 方案整体高级 | ✅ 公允 | 保持自信 |

**最值得做的改动（<30分钟）：**
1. [search_engine.py:45](backend/phase1/search_engine.py#L45) — 在 `len(q) < 3` 旁加 `or re.search(r'[&%_\\/\-]', q)` 作为特殊字符检测
2. [prompts.py:26-34](backend/phase3/prompts.py#L26-L34) — 删除或注释 `VERIFIER_PROMPT`（从未使用，留着容易让人误以为代码在跑双Agent）
