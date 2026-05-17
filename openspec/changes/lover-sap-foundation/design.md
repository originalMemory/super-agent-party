## 目标陈述（已定稿方向）

**lover** 为自 SAP **硬分叉**的独立产品线：**唯一代码路径**，**无 `loverMode`**，**不保留**酒馆式旧页面与并行逻辑。单一用户与 **唯一 Agent**；人设与记忆 Markdown 来自 **`USER_DATA_DIR/lover/`**（与 **`CLISettings.cc_path`** 解耦）。  
人设注入：**每次发消息时从磁盘重新加载并注入 system**（与 OpenClaw 对齐）：**用户档案 + 完整角色信息**；**`IDENTITY.md` 与 `SOUL.md` 必须分文件、不合并**（见下）。**每轮 FTS 仅检索「记忆」Markdown**（`lover/MEMORY.md` 与 **`lover/memory/` 下递归的全部 `.md`**；推荐 **`lover/memory/YYYY/MM/<日记>.md`**，**不**做强日历校验）。**不得**索引人设文件。实现为 **SQLite FTS5**：索引 **`{USER_DATA_DIR}/lover/memory_index.sqlite`**；**`loverSettings`**（默认同步 **10 分钟**）；**simple** 扩展由实现 **自动下载/缓存**（失败则 **trigram** → **unicode61**）。**不使用 mem0**。  
会话形态：复用 SAP 既有「分组 + 会话」底座，**收敛为两组固定结构**：**主分组**（含**单例主会话** + 0..N 个**开发会话**）与**归档分组**（仅保存归档的主会话快照）。支持 **主动归档**、**重置会话**；开发会话归档以 **摘要回流** 形式产出 `lover/memory/YYYY/MM/<日期>-work-<slug>.md`，原对话历史不留存。

**品牌与仓库命名**：后续对外将 **super-agent-party** 更名为 **super-agent-lover**（仓库名、包名、文档标题等与发布节奏对齐）。

---

## OpenClaw 对齐：`USER` / `IDENTITY` / `SOUL` / 日记

| 文件 / 路径 | 承担 | lover 定稿 |
|-------------|------|------------|
| **`USER.md`** | 人类用户档案 | **独立文件**；bootstrap；不进 FTS；不与 IDENTITY/SOUL 合并 |
| **`IDENTITY.md`** | Agent 叙事内身份 | **独立文件**；bootstrap；**不与 SOUL 合并** |
| **`SOUL.md`** | 元层运行原则 | **独立文件**；bootstrap；**不与 IDENTITY 合并** |
| **`AGENTS.md`** | 操作约束层：安全规则、权限边界、数据目录约定 | **必注入**（main/dev 均强制）；bootstrap 靠前；文件不存在时报 warning 而非静默跳过 |
| **`MEMORY.md`** | 长期事实 | FTS；可选摘要进 bootstrap |
| **`lover/memory/**/*.md`** | 日记树 | **用户可见**；推荐 `YYYY/MM/`；`lover/memory/` 下任意 `.md`（递归）均 FTS |

**Bootstrap 注入顺序**：`AGENTS`（必须）→ `USER` → `IDENTITY` → `SOUL` →（可选 `MEMORY` 摘要）。**不得**再走设定书关键词流水线。

> **注**：所有人设文件均由服务端 `build_lover_system_prompt()` 从磁盘读取后拼入 system prompt，**agent 无需也不应在对话中主动调用工具读取这些文件**。AGENTS.md 中不应包含"每次会话读取 SOUL.md / USER.md"此类启动指令——这类逻辑由 bootstrap 机制保证，写入 AGENTS.md 只会造成模型行为混乱。

### 三文件职责边界

| 文件 | 优先级 | 定位 | 典型内容 | 不该写的 |
|------|--------|------|---------|---------|
| **`AGENTS.md`** | 最高 | **操作约束层**：工作区如何运转 | 安全规则（`trash > rm`）、权限边界（可自主做什么/需先问什么）、数据目录约定、写权限隔离 | 人格、价值观、"请先读 SOUL.md" 等启动指令 |
| **`SOUL.md`** | 次高 | **元层原则**：我是什么样的存在 | 核心价值观、诚实原则、与用户的关系哲学、语调风格总纲 | 叙事身份细节（名字、具体记忆）、工作区操作规范 |
| **`IDENTITY.md`** | 普通 | **叙事层**：我是谁 | 名字、背景故事、与用户的具体关系描述、人格特质细节 | 操作约束、原则性价值观（应在 SOUL）|

**冲突处理**：优先级高的文件覆盖低的——AGENTS.md 的操作约束不可被 IDENTITY 设定覆盖（例如安全规则即使角色人设"很听话"也不失效）。

---

## 设计原则

1. **单一产品**：无模式开关；移除酒馆 UI 与角色卡主导航。
2. **Markdown SSOT**：bootstrap 集合与加载顺序固定并文档化。
3. **人设 vs 记忆**：人设文件（USER / IDENTITY / SOUL / AGENTS）**每次发消息时从磁盘重新加载、注入 system**（与 OpenClaw 对齐，不写入对话历史）；**仅记忆语料**（含根备忘与按日日记树）走 **每轮 FTS**。
4. **记忆**：仅 FTS5 + 用户维护的 Markdown；无向量记忆栈。
5. **两组固定结构**：主分组（`main` 单例 + 多 `dev`）+ 归档分组（仅 `main` 快照）；开发对话不进 FTS，仅由摘要回流间接进入日记树。
6. **分叉与上游**：择优合并 SAP。

---

## MVP 边界

### 纳入

- SSOT bootstrap：**AGENTS + USER + IDENTITY + SOUL** 四分文件，均必注入。
- **记忆 FTS** + 每轮注入；索引 **`lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**。
- 主分组 + 归档分组的固定两组结构；主会话归档/重置；开发会话多开、可选绑定工作区、归档摘要回流。
- 移除酒馆路径。

### 首期非目标

- OpenClaw 同款 QMD。
- 完整桌面主动感知（backlog）。

### 记忆索引范围

**`lover/MEMORY.md`** + **`lover/memory/`** 下递归的 `.md`。**不得**将 USER / IDENTITY / SOUL / AGENTS 纳入默认 FTS。

---

## 架构触点

| 区域 | 触点 |
|------|------|
| 配置 | **`USER_DATA_DIR/lover`** = 人设 + 记忆 Markdown + FTS 索引根；**`cc_path`** = 工作区（任务 / `.agent` 待办 / 项目 skills） |
| 后端 | SSOT 从 `lover/` 拼接 bootstrap、记忆 FTS、可监视 `lover/memory/`、移除 `cur_memory` 每轮注入；新增 `dev` 会话 bootstrap 装配与摘要回流写入 |
| 前端 | 两组固定结构（主分组/归档分组）；主会话单例；开发会话可多开；归档主会话只读 + 「拉回主会话」；开发会话归档弹窗确认摘要 |

---

## 会话模型与分组

复用 SAP 既有「分组 + 会话」底座，**收敛**为两组固定结构；用户**不得**新建/删除/重命名分组。

```
主分组（fixed, system）
├── 主会话（kind=main，单例，不可删；可"重置"、可"主动归档"）
├── 开发会话 #1（kind=dev，可多开，可绑定 cc_path 工作区）
├── 开发会话 #2
└── ...

归档分组（fixed, system）
├── 归档主会话快照-2026-05-10（kind=archive，只读浏览）
├── 归档主会话快照-2026-04-22
└── ...   ← 仅保存归档的主会话；开发会话不入此分组
```

会话表新增字段（沿用既有 schema，避免新表）：

| 字段 | 取值 | 说明 |
|------|------|------|
| `kind` | `'main' \| 'dev' \| 'archive'` | 强类型；同一时间主分组内 `kind=main` 至多 1 条 |
| `workspace_path` | `string \| null` | 仅 `dev` 可为非空，绑定一个 `cc_path` 工作区；`null` = 无工作区（适合写全局 skill / 脚本） |
| `archived_at` | `timestamp \| null` | `archive` 必填；用于归档分组列表排序 |
| `summary_path` | `string \| null` | 仅 `dev` 归档时写入：摘要日记的相对路径，便于追踪 |

---

## Bootstrap 差异

> **注**：`main` / `dev` 列的"注入"均指**每次发消息时从磁盘重新加载并注入 system**（与 OpenClaw 一致），不写入对话历史。`archive` 只读不发消息，bootstrap 不适用（标 —）。

| 项 | `main` | `dev` | `archive`（只读） |
|----|--------|-------|-------------------|
| `AGENTS.md` | **强制注入** | **强制注入**（额外追加工作区上下文） | — |
| `USER.md` | ✓ | ✓ | — |
| `IDENTITY.md` | ✓ | ✓ | — |
| `SOUL.md` | ✓ | ✓ | — |
| `MEMORY.md` 摘要 | 可选 | 可选（与 `main` 行为一致） | — |
| 工作区 `.agent/` 概要 / 项目 skills 索引 | — | **追加注入**（仅当绑定了工作区） | — |
| 每轮 FTS 召回（`lover/MEMORY.md` + `lover/memory/**/*.md`） | ✓ | **✓**（保持人格连续，能感知最近日记） | — |
| 写权限：人设三件套 / `MEMORY.md` | 仅用户手改 | **不得**直接写 | — |
| 写权限：`lover/memory/` 日记树 | 仅用户手改 | **仅**通过摘要回流间接写入 | — |

**原则**：开发会话与主会话**共享同一份人设 SSOT**——是「同一个她，今天陪你写代码」，而非另一种 mode；这与已决议第 6 条「无 loverMode」一致（`kind` 是会话**种类**，不是会话**模式开关**）。

---

## System Prompt 拼装（每次发消息重建）

每次请求在服务端覆盖式重建 `messages[0].content`，分**稳定块 + 缓存边界 + 动态块**（对齐 OpenClaw，人设文件从磁盘重读，不写入对话历史）：

```
STABLE BLOCK
  # Project Context
  [If SOUL.md is present, embody its persona and tone...]
  ## AGENTS.md（lover/）    ← main/dev 均强制
  ## USER.md
  ## IDENTITY.md
  ## SOUL.md
  ## MEMORY.md              ← 可选摘要
  <!-- LOVER_PROMPT_CACHE_BOUNDARY -->

DYNAMIC BLOCK
  # Dynamic Context
  ## Memory Recall (FTS)    ← 每轮基于最新 user 消息检索
  ## Workspace              ← cc_path 有效时注入（main 和 dev 均支持）
    .agent/AGENTS.md（项目级）
    .agent/ai_todos.json
    skills 索引
  ## Runtime                ← 时间 / kind / workspace_path
  [TTS / VRM / formula 等通用工具提示]
```

实现入口：`py/lover_bootstrap.py`，提供 `build_lover_system_prompt()`；替换 `tools_change_messages` 中现有 `cur_memory` 整块注入与多处零散 `content_append`。

---

## 会话启动序列（Session Startup）

对齐 OpenClaw 的 `/new` 机制：**新建或重置会话时，自动注入启动提示词，让模型用 SOUL.md persona 主动问候用户**。

### 触发时机

- 主会话：创建 / 重置（`POST /api/lover/session/main/reset`）
- 开发会话：创建 / 丢弃重开

### 提示词注入方式

在本次请求的**用户消息**（最后一条 `user` role）末尾追加一段启动指令（不存入对话历史），告知模型：

```
A new session was started. Execute your Session Startup sequence:
greet the user in your configured persona (SOUL.md defines your voice and tone).
Keep it to 1-3 sentences and ask what they want to do.
Do not mention internal steps, files, or tools.
```

### 启动记忆（Daily Memory Prelude）

与 OpenClaw 的 `startupContext` 对应——在启动提示词**前**注入最近 N 天的日记摘要，让模型带着近期记忆开口：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `dailyMemoryDays` | 2 | 回溯天数 |
| `maxTotalChars` | 2800 | 启动记忆总字符上限 |

日记文件范围：`lover/memory/` 下按 `YYYY/MM/` 目录递归查找最近 N 天内修改的 `.md`；与常规 FTS 白名单一致，**不**额外读取人设文件。

### 流程

```
会话新建 / 重置
  ↓
后端：is_new_session = True
  ↓
build_lover_system_prompt()  ← 正常拼 stable + dynamic 块
  ↓
build_startup_prelude()      ← 读最近日记，拼 ## Memory Context 块（可选）
  ↓
startup_prompt               ← "A new session was started..."
  ↓
发给模型：[system] [历史（空）] [user = startup_prelude + startup_prompt]
  ↓
模型用 SOUL.md 语调问候，1-3 句
```

---

## 开发会话生命周期与摘要回流

| 操作 | `main` | `dev` |
|------|--------|-------|
| 创建 | 系统初始化时自动建立单例 | 用户在主分组内"新建开发会话"，可选绑定一个 `cc_path` |
| 重置 | 清空当前对话历史，**不存档** | 等价于"丢弃"（不出摘要、直接清空） |
| 主动归档 | 整段快照 → 归档分组；主会话原地新开 | **摘要回流**（见下）→ 对话历史**直接删除** |
| 关闭 / 退出 | 不动 | 不动（仍在主分组列表，可继续） |

**摘要回流流程**（开发会话主动归档时触发）：

1. Agent 基于本会话上下文起草一段日志摘要（建议 ≤ N 字，含：任务标题、关键产出/决策、未决问题）。
2. 弹窗给用户**编辑/确认**，目标文件名预填 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`，slug 由 Agent 起、可改。
3. 用户确认 → 落盘 → 删除会话历史 → 写入 `summary_path`；下一轮 `sync_memory_index` 后被 FTS 收录，主会话从此可召回。
4. 若用户提供"快速保存"开关（`loverSettings.devArchiveQuickSave`，默认关）→ 跳过弹窗，直接落盘。
5. **降级**：若 Agent 起草失败/拒答，仍允许归档，但摘要文件**仅含元信息**（任务标题、绑定工作区、起止时间），保留 FTS 痕迹。
6. **不写** `lover/MEMORY.md`：MEMORY 留给"长期事实/伴侣关系状态"，工作日志只走日记树。

**归档分组的归档主会话**：只读浏览，不可续聊；提供「**拉回主会话**」按钮——把所选历史段落复制为引用追加到当前主会话上下文（不动归档原件）。

---

## 已决议清单

1. **人设**：USER、IDENTITY、SOUL **三分文件，IDENTITY 与 SOUL 不合并**；无单独设定书流水线。
2. **日记**：推荐 `lover/memory/YYYY/MM/<文件>.md`，实现收录 `lover/memory/` 下任意 `.md`（递归），对用户可见。
3. **会话**：复用「分组+会话」底座，固定两组——**主分组**（`main` 单例 + 0..N 个 `dev`）+ **归档分组**（仅归档主会话）；支持主动归档与重置。
4. **`lover/`**：位于 **`USER_DATA_DIR`**；人设与日记树、**`memory_index.sqlite`** 均在此树下。**`cc_path`** 仅工作区能力。
5. **品牌**：lover。
6. **无 loverMode**。
7. **开发会话**：与主会话**共享同一人设 bootstrap**（含 `AGENTS.md`，绑定工作区时再追加 `.agent/` 概要 / 项目 skills）；自身对话**不入 FTS**；归档时由 Agent 起草摘要 → 默认弹窗确认 → 落 `lover/memory/YYYY/MM/<日期>-work-<slug>.md` → 删除原对话历史；**不**直接写 `MEMORY.md` 或人设三件套。
8. **`AGENTS.md` 必注入**：main / dev 均强制；内容限定为**操作约束**（安全、权限、数据目录），**不得**包含"读取 SOUL.md / USER.md"等启动指令（服务端 bootstrap 已保证文件内容在 system prompt 里）。IDENTITY / SOUL / USER 各司其职，见「三文件职责边界」。

---

## Git 与分支策略（建议）

- **`origin`**：super-agent-lover；**`upstream`**：super-agent-party。

---

## 风险

- **上游合并**：删除 UI 后 diff 大。
- **重置语义**：区分对话上下文 vs 持久记忆存储。
- **开发会话摘要保真**：Agent 起草的摘要可能含幻觉，会以日记形式被 FTS 长期召回；缓解：默认弹窗确认 + 快速保存仅作可关闭的便利项 + 起草失败时降级为元信息摘要。
- **会话调性串味**：开发会话仍走 FTS 召回伴侣记忆，可能在工程上下文里"突然撒娇"；可接受（用户偏好"不死板"），但 prompt 模板需在 `dev` 注入时提示当前任务语境（写代码/写脚本）。
- **`workspace_path` 失效**：用户绑定的 `cc_path` 可能被改名/删除；需在装配 bootstrap 时优雅降级（按"未绑定工作区"处理，不阻塞会话）。
