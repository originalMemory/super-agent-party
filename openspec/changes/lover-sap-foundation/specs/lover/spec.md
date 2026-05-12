## ADDED Requirements

### Requirement: 单一产品线（无模式开关）

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

产品必须为 **lover 单一形态**：**不得**实现 `loverMode` 或等价开关以保留 SAP 酒馆完整 UI；**不得**将酒馆角色卡、换卡作为主路径。

#### Scenario: 无换卡

- **当** 用户使用主界面发起对话
- **则** 不得提供「更换角色卡」类交互。

---

### Requirement: Markdown SSOT 与 USER / IDENTITY / SOUL

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

产品必须以约定根目录（默认 **`.agent/`**）下 Markdown 为真相源。

- **`USER.md`**：人类用户档案；**必须**作为 bootstrap 的一部分；**不得**默认并入 FTS。
- **`IDENTITY.md`**、**`SOUL.md`**：**必须**各为 **独立文件**；**不得**合并为单一 Markdown、**不得**省略其一；**不得**重复注入两份等价正文。
- **`AGENTS.md`**：可选；若存在则纳入 bootstrap（倾向先于 USER/人设）。
- **`MEMORY.md`**：长期记忆事实；**必须**纳入 FTS；是否在 bootstrap 中额外常驻摘要以实现为准，须文档化且与 FTS 白名单一致。

**按日日记**路径（相对 CLI `cwd`）：**`memory/YYYY/MM/YYYY-MM-DD.md`**。该路径 **不得**设计为对用户隐藏；须支持用户直接查看与编辑。日记文件 **必须**纳入 FTS 记忆语料。

**不得**实现酒馆式「设定书」的 **关键词触发按需注入**；此类内容须 **并入初始角色信息**，随 bootstrap 一并提供。

#### Scenario: 会话锚点注入

- **当** 主会话请求模型回复
- **则** 系统必须按设计文档顺序组装 **完整初始角色信息**（USER + IDENTITY + SOUL + 可选 AGENTS + 可选 MEMORY 摘要），且 **会话级不随每条用户消息倍增**。

---

### Requirement: OpenClaw 式人设注入（非 FTS、无设定书流水线）

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统 **不得**在 **每一次** 用户请求路径中 **无条件重复追加** 完整酒馆式「角色描述、性格、示例对话、系统提示词」块。

系统必须将会话级人设 **固定为 bootstrap**（一条逻辑 system 组合）；**不得**用人设语料参与 **每轮记忆 FTS**。

**记忆 FTS** 命中块 **单独** 以「相关回忆」等形式附加，**不得替代** bootstrap。

#### Scenario: 连续多轮用户消息

- **当** 同一主会话内用户连续发送多条消息
- **则** 服务端不得对每一条消息都重新追加一整份与上一轮相同的完整人设正文（bootstrap 锚点更新除外）。

#### Scenario: 裁剪保护

- **当** 实现对话历史压缩或截断
- **则** 人设 bootstrap 不得被静默丢弃，除非用户触发「重置会话」等定义操作。

---

### Requirement: 记忆检索专用 FTS（无 mem0）

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统必须在 **每次用户发送消息、调用模型之前**，对 **记忆语料集合** 执行 **SQLite FTS5**：至少包含 **`USER_DATA_DIR/lover/MEMORY.md`** 与 **`USER_DATA_DIR/lover/memory/`** 下 **递归**的 **`.md`** 文件（推荐 **`lover/memory/YYYY/MM/<日记>.md`**，实现 **不**强制校验日期）。记忆根目录为 **`USER_DATA_DIR/lover`**（**与 `CLISettings.cc_path` 无关**）。查询文本 **倾向** 为当前用户消息（可从多模态消息中提取纯文本）。索引库 **`{USER_DATA_DIR}/lover/memory_index.sqlite`**，**不得**当作唯一 SSOT。索引刷新 **不得**绑定在每次查询路径上；同步间隔 **`loverSettings.memoryIndexSyncIntervalMinutes`**（默认 10 分钟）；**进程启动**与**后台周期**调用 **`sync_memory_index`**（见 `server.py` lifespan）。实现 **应尝试** 自动获取并加载 **wangfenjin/simple**（`tokenize='simple'` / `simple_query()`，缓存路径见实现）；失败则使用内置分词降级；换分词器须重建索引文件。

系统 **不得**将 **`USER.md` / `IDENTITY.md` / `SOUL.md` / `AGENTS.md`** 纳入该 FTS 默认索引范围。

系统 **不得**依赖 **mem0** 或同类向量记忆栈完成本轮注入；长期记忆 **读路径** 以 FTS 命中片段为准。

#### Scenario: FTS 分词降级

- **当** 目标 SQLite 不支持首选 FTS5 分词器（如 trigram）
- **则** 必须降级到其它内置 tokenize 或默认 FTS5，且不得崩溃。

---

### Requirement: 主会话、归档与重置

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

产品必须支持 **主会话**、**归档**、**主动归档**、**重置会话**（重置语义须文档化）。

产品必须复用既有「分组 + 会话」底座，**收敛为两组固定结构**：**主分组**与**归档分组**。这两个分组**不得**由用户新建、删除或重命名。会话**必须**带有种类字段 `kind ∈ { main, dev, archive }`：

- **`main`**：主会话；**主分组**内**至多一条**；**不得**被删除；可"重置"或"主动归档"。
- **`dev`**：开发会话；**仅**存在于**主分组**内；**可多开**；可选绑定一个 `cc_path` 工作区。
- **`archive`**：归档主会话快照；**仅**存在于**归档分组**内；**只读**，**不得**被续聊。

**开发会话不得进入归档分组**：其归档形式由「摘要回流」承担（见对应 Requirement），原对话历史**不**被持久保留。

#### Scenario: 主动归档（主会话）

- **当** 用户对主会话执行"主动归档"
- **则** 当前主会话快照进入归档分组，主分组中保留主会话槽位以承接新一轮对话。

#### Scenario: 重置（主会话）

- **当** 用户重置主会话
- **则** 消息上下文按定义清空或换新线程；**不得**静默清空全部长期记忆存储除非明示。

#### Scenario: 主分组单例约束

- **当** 主分组内已存在 `kind=main` 的会话
- **则** 系统**不得**允许在主分组内再创建第二条 `kind=main` 会话。

#### Scenario: 分组不可变

- **当** 用户尝试新建/删除/重命名分组
- **则** 系统**不得**允许；前端**不得**提供相应入口。

#### Scenario: 归档主会话只读

- **当** 用户打开归档分组中的某条 `archive` 会话
- **则** 仅可浏览历史与触发"拉回主会话"（将所选历史段落以引用追加到当前主会话），**不得**在归档会话内继续发送新消息。

---

### Requirement: 开发会话 Bootstrap

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

`dev` 会话**必须**与 `main` 会话**共享同一份人设 SSOT**：bootstrap **必须**按 `AGENTS`（**强制**） → `USER` → `IDENTITY` → `SOUL` 顺序装配；`USER.md` / `IDENTITY.md` / `SOUL.md` 仍为**独立文件**且**不得**合并。

`dev` 会话**应**继续受益于"每轮记忆 FTS 召回"，以保持人格连续与对最近日记的感知；FTS 范围与 `main` 会话保持一致（`lover/MEMORY.md` + `lover/memory/**/*.md`）。

`dev` 会话**应**根据 `workspace_path` 决定是否追加注入工作区上下文：

- **当** `workspace_path` 非空且对应 `cc_path` 工作区可用 → **必须**追加注入该工作区 `.agent/` 概要与项目 skills 索引。
- **当** `workspace_path` 为空或绑定的工作区已失效 → **必须**优雅降级为"未绑定工作区"模式（仅人设三件套 + 强制 `AGENTS`），**不得**因此阻塞会话创建或对话。

`dev` 会话**不得**直接写入 `USER.md` / `IDENTITY.md` / `SOUL.md` / `AGENTS.md` / `lover/MEMORY.md`，**也不得**直接在 `lover/memory/` 下创建/编辑任意 `.md`；对日记树的写入**仅可**通过"摘要回流"间接发生。

#### Scenario: 强制 AGENTS

- **当** `dev` 会话装配 bootstrap 而仓库 / `USER_DATA_DIR/lover/` 中存在可用的 `AGENTS.md`
- **则** 必须将 `AGENTS.md` 注入到 bootstrap 中（顺序在 `USER` 之前）。

#### Scenario: 工作区降级

- **当** `dev` 会话的 `workspace_path` 指向已失效路径（被改名/删除）
- **则** 系统不得阻塞或报错中断会话；必须按未绑定工作区装配并对用户给出可见提示。

#### Scenario: 写入隔离

- **当** `dev` 会话的工具调用尝试写入人设三件套 / `MEMORY.md` / `lover/memory/` 下任意 `.md`
- **则** 系统必须拒绝写入；如确需更新长期事实，引导用户回到主会话或手动编辑 Markdown。

---

### Requirement: 开发会话摘要回流

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

`dev` 会话**主动归档时**，系统**必须**触发"摘要回流"：由 Agent 基于本会话上下文起草一段日志摘要，并以日记 `.md` 的形式落入 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`。

落盘路径**必须**位于 `lover/memory/` 子树下，使其可被既有 FTS 白名单（递归 `.md`）自然覆盖；**不得**写入 `lover/MEMORY.md`。

默认行为**必须**为"先弹窗给用户编辑/确认，再落盘"。系统**应**提供 `loverSettings.devArchiveQuickSave`（默认 `false`）开关；当且仅当开启时，方可跳过弹窗直接落盘。

落盘成功后，系统**必须**：
1. 删除该 `dev` 会话的对话历史（**不**保留原文）。
2. 将摘要文件相对路径写入会话表的 `summary_path` 字段以备追溯。
3. 触发或等待下一轮 `sync_memory_index` 将该日记纳入 FTS 索引。

若 Agent 起草摘要**失败或拒答**，系统**仍必须**允许归档完成，但摘要文件**仅含元信息**（任务标题、绑定的 `workspace_path`、起止时间），以保留 FTS 痕迹。

#### Scenario: 默认弹窗确认

- **当** 用户对 `dev` 会话执行"主动归档"且 `loverSettings.devArchiveQuickSave` 为 `false`
- **则** 系统必须弹窗展示 Agent 起草的摘要、目标文件名（预填 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`），允许用户编辑后再确认落盘。

#### Scenario: 快速保存

- **当** `loverSettings.devArchiveQuickSave` 为 `true` 且用户对 `dev` 会话执行"主动归档"
- **则** 系统可不弹窗直接落盘 Agent 起草的摘要，并删除会话历史。

#### Scenario: 起草失败降级

- **当** Agent 起草摘要失败或拒答
- **则** 系统不得阻塞归档；必须以仅含元信息的摘要文件落盘，并删除原对话历史。

#### Scenario: 重置不出摘要

- **当** 用户对 `dev` 会话执行"重置"而非"主动归档"
- **则** 系统不得生成摘要、不得写入 `lover/memory/`；仅清空当前会话上下文。

#### Scenario: FTS 不索引开发会话原文

- **当** `dev` 会话存在持久化的对话历史
- **则** 该历史不得被纳入 FTS 索引；FTS 仅可通过"摘要回流"产物间接感知开发活动。
