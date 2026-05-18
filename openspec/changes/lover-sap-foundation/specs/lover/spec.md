## ADDED Requirements

### Requirement: 角色卡扩展字段（soul / memoryNotes / userProfile）

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

角色卡 `memories[]` **必须**新增 `soul`（元层原则）字段。`memorySettings` **必须**新增 `userProfile`（用户档案）和 `memoryNotes`（记忆笔记）字段，二者所有角色**共享**。

所有新字段**必须**默认为空字符串。空字符串时**不得**注入 system prompt，以保证老角色卡**向后兼容**。

- **`soul`**：角色卡级；定义元层运行原则（价值观、语调、主动性边界）。
- **`memoryNotes`**：`memorySettings` 级；所有角色**共享**的手写长期记忆，沉淀与用户相关的长期事实与约定。
- **`userProfile`**：`memorySettings` 级；所有角色**共享**的用户档案。

#### Scenario: 向后兼容

- **当** 用户加载一张不含 `soul` 字段的旧角色卡
- **则** 系统**必须**自动补全默认空值，注入行为与现有版本一致。

#### Scenario: userProfile 和 memoryNotes 跨角色共享

- **当** 用户在 `memorySettings` 中配置了 `userProfile` 或 `memoryNotes`
- **则** 无论切换到哪张角色卡，二者均**必须**保持不变并参与注入。

---

### Requirement: System Prompt 注入顺序

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

在现有角色卡注入链的基础上扩展。注入顺序**必须**为：

1. `userProfile`（非空时）
2. `soul`（非空时）
3. 默认用户名说明（已有）
4. `characterBook` 世界观设定（已有，关键词命中时）
5. `description` 角色设定（已有）
6. `personality` 性格设定（已有）
7. `mesExample` 对话示例（已有）
8. `systemPrompt` 角色系统提示（已有）
9. `genericSystemPrompt` 通用系统提示（已有）
10. `memoryNotes`（非空时，从 `memorySettings` 读取，常驻全文注入）
11. FTS recall（日记树检索命中片段）
12. mem0 recall（已有，**默认关闭**，用户手动配置 providerId 时生效）

**不得**删除或替代现有注入链中的任何步骤。新增字段**必须**使用 Markdown 标题隔离（如 `## 用户档案`）。

`{{user}}` / `{{char}}` 占位符替换**必须**适用于三个新字段。

#### Scenario: 注入不膨胀

- **当** 同一会话内用户连续发送多条消息
- **则** 新增字段的注入**不得**随轮次重复膨胀（与现有字段行为一致）。

#### Scenario: 裁剪保护

- **当** 实现对话历史压缩或截断
- **则** `userProfile`、`soul` 与现有 bootstrap 字段**不得**被静默丢弃。

---

### Requirement: 日记树 FTS 记忆检索

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统**必须**在**每次用户发送消息、调用模型之前**，对日记树执行 **SQLite FTS5** 检索。

**索引范围**：`{USER_DATA_DIR}/lover/memory/` 下**递归**的 `.md` 文件（推荐 `lover/memory/YYYY/MM/<日记>.md`，**不**强制校验日期格式）。

**不得索引**的内容：角色卡字段（`soul`、`memoryNotes`）、`memorySettings` 字段（`userProfile`）——这些已全文常驻注入 bootstrap，索引会造成重复命中。

**索引库**：`{USER_DATA_DIR}/lover/memory_index.sqlite`。**索引同步**：进程启动时 `sync_memory_index` 一次 + 后台按 `loverSettings.memoryIndexSyncIntervalMinutes`（默认 10 分钟）周期同步。同步**不得**绑定在每次查询路径上。

**分词器**：**应尝试**自动获取并加载 wangfenjin/simple；失败则降级到 trigram → unicode61；更换分词器**须**重建索引文件。

**查询文本**：倾向为当前用户消息纯文本。命中片段以 `## 相关回忆` 标题注入 system prompt dynamic 块。

#### Scenario: FTS 分词降级

- **当** 目标 SQLite 不支持首选 FTS5 分词器
- **则** **必须**降级到其它内置 tokenize，**不得**崩溃。

#### Scenario: 专有名词精确命中

- **当** 用户消息包含日记中出现过的专有名词（人名、游戏名、项目名）
- **则** FTS **必须**能精确匹配命中，不依赖向量近似。

#### Scenario: 摘要回流后可检索

- **当** 开发会话摘要回流落盘至 `lover/memory/` 下
- **则** 下一轮 `sync_memory_index` 后，主会话 FTS **必须**能检索到该摘要内容。

---

### Requirement: mem0 可选默认关闭

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统**必须**保留 mem0 代码通路与 UI 配置，但**必须**默认不启用。仅当用户在角色卡 embedding 设置中手动配置了 `providerId`、`model`、`api_key`、`base_url` 时方可生效。

**不得**在未配置 mem0 的情况下执行向量检索或自动提炼写入。

#### Scenario: 默认关闭

- **当** 用户未配置角色卡的 embedding `providerId`
- **则** 系统**不得**执行 mem0 相关的 `m0.search` 或 `m0.add` 操作。

#### Scenario: 手动开启

- **当** 用户手动配置了 embedding 相关字段
- **则** mem0 按现有逻辑工作（每轮检索 + 请求结束后自动提炼），与 FTS 并存。

---

### Requirement: AI 工具——角色卡查看与修改

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统**必须**向 AI 提供以下工具，注册到 `dispatch_tool` 工具映射表：

1. **`get_character_card`**：读取当前选中角色卡的完整信息或指定字段，同时返回 `memorySettings.userProfile` 和 `memorySettings.memoryNotes`。
2. **`update_character_card`**：修改当前选中角色卡的指定字段。**可写字段白名单**：`soul`、`description`、`personality`、`systemPrompt`、`mesExample`。**不得**允许修改 `name`、`avatar`、`providerId` 等结构性字段。
3. **`update_user_profile`**：修改全局用户档案（`memorySettings.userProfile`）。
4. **`update_memory_notes`**：修改全局记忆笔记（`memorySettings.memoryNotes`）。

四个工具**必须**归入 `SENSITIVE_TOOLS`（`get_character_card` 除外），执行前**须**用户审批。修改后**必须**调用 `save_settings()` 持久化，并通知前端刷新。

#### Scenario: AI 读取角色卡

- **当** AI 调用 `get_character_card` 且不传 `fields` 参数
- **则** 返回当前角色卡的全部字段内容以及全局 `userProfile` 和 `memoryNotes`。

#### Scenario: AI 修改 memoryNotes

- **当** AI 调用 `update_memory_notes` 修改 `memoryNotes`
- **则** 修改**必须**经用户审批后生效并持久化到 `memorySettings.memoryNotes`。

#### Scenario: AI 修改结构性字段被拒绝

- **当** AI 调用 `update_character_card` 尝试修改 `name` 字段
- **则** 系统**必须**拒绝并返回错误提示。

---

### Requirement: 日记树路径可配置

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

日记树根目录**必须**可配置，配置项为 `memorySettings.memoryDirPath`。默认为空字符串，空值时使用 `{USER_DATA_DIR}/lover/memory/`。

FTS 索引库路径**必须**跟随日记树目录自动派生。FTS 同步间隔**必须**可配置（`memorySettings.memoryIndexSyncMinutes`，默认 10 分钟）。

配置变更后**必须**重建 FTS 索引。

#### Scenario: 自定义路径

- **当** 用户将 `memoryDirPath` 设置为自定义路径
- **则** FTS 索引**必须**切换到该目录下递归 `.md`，摘要回流**必须**落盘到该目录下。

#### Scenario: 默认路径

- **当** `memoryDirPath` 为空字符串
- **则** 系统**必须**使用 `{USER_DATA_DIR}/lover/memory/` 作为日记树根目录。

---

### Requirement: AGENTS.md 处理（方案 A）

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

操作约束层**不得**引入角色卡级字段。**必须**复用以下已有通路：

1. **全局 `system_prompt`**：settings 中配置的全局系统提示，对所有角色卡生效
2. **工作区 `.agent/AGENTS.md`**：会话绑定工作区（`cc_path`）时，由 `tools_change_messages` 现有逻辑注入

#### Scenario: 全局约束

- **当** 用户在 settings 中配置了 `system_prompt`
- **则** 该提示**必须**位于 `messages[0]` 最前部，对所有角色卡和会话类型生效。

#### Scenario: 工作区约束

- **当** 会话绑定了有效的 `cc_path` 且该路径下存在 `.agent/AGENTS.md`
- **则** 系统**必须**按现有逻辑注入工作区约束。

---

### Requirement: 前端角色卡编辑扩展

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

角色卡编辑界面**必须**新增以下编辑区域：

1. **SOUL / 元层原则**：Markdown 文本编辑区，对应 `memories[i].soul`

**必须**新增独立「用户档案与记忆」Tab（与角色卡配置同级），包含：

2. **日记树目录**：路径输入框，对应 `memorySettings.memoryDirPath`
3. **FTS 同步间隔**：数字输入，对应 `memorySettings.memoryIndexSyncMinutes`
4. **记忆笔记**：Markdown 文本编辑区，对应 `memorySettings.memoryNotes`（所有角色共享）
5. **用户档案**：Markdown 文本编辑区，对应 `memorySettings.userProfile`（所有角色共享，放最下方）

现有角色卡列表、换卡、TTS 多角色语音、VRM 多角色外观等 UI **不得**删除。

#### Scenario: 新建角色卡

- **当** 用户新建一张角色卡
- **则** `soul` 字段**必须**初始化为空字符串。

---

### Requirement: 保留角色卡体系

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

系统**必须**保留完整的 `memories[]` + `memorySettings` 角色卡体系，包括：

- 角色卡 CRUD（创建、切换、删除）
- TTS 多角色语音同名联动
- VRM 多角色外观同名联动
- mem0 向量长期记忆（可选）
- `characterBook` 世界观设定（关键词触发注入）
- 开场白（`firstMes` / `alternateGreetings`）
- 角色卡导入/导出

**不得**以引入 OpenClaw 能力为由删除上述任何功能。

#### Scenario: 多角色切换

- **当** 用户切换角色卡
- **则** `soul` 随角色卡切换，`userProfile` 和 `memoryNotes` 保持不变（全局共享）。

---

### Requirement: 主会话、归档与重置

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

产品**必须**复用既有「分组 + 会话」底座，**收敛为两组固定结构**：**主分组**与**归档分组**。这两个分组**不得**由用户新建、删除或重命名。

会话**必须**带有种类字段 `kind ∈ { main, dev, archive }`：

- **`main`**：主会话；主分组内**至多一条**；**不得**被删除；可"重置"或"主动归档"。
- **`dev`**：开发会话；**仅**存在于主分组内；可多开；可选绑定 `workspace_path`。
- **`archive`**：归档主会话快照；**仅**存在于归档分组内；**只读**。

#### Scenario: 主动归档（主会话）

- **当** 用户对主会话执行"主动归档"
- **则** 当前主会话快照进入归档分组，主分组中保留主会话槽位。

#### Scenario: 重置（主会话）

- **当** 用户重置主会话
- **则** 消息上下文按定义清空；**不得**静默清空全部长期记忆。

#### Scenario: 归档只读

- **当** 用户打开归档会话
- **则** 仅可浏览和「拉回主会话」，**不得**继续发送新消息。

---

### Requirement: 开发会话摘要回流

The implementation MUST conform to all normative statements ("必须" / "不得") in this requirement.

`dev` 会话主动归档时，系统**必须**触发"摘要回流"：Agent 基于本会话上下文起草日志摘要，以 `.md` 形式落入 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`。

默认行为**必须**为"先弹窗给用户编辑/确认，再落盘"。`loverSettings.devArchiveQuickSave`（默认 `false`）开关开启时可跳过弹窗。

落盘成功后**必须**：删除 `dev` 会话对话历史 + 写入 `summary_path`。

Agent 起草失败时**仍必须**允许归档，以仅含元信息的摘要文件落盘。

**不得**将摘要写入角色卡的 `memoryNotes`——memoryNotes 由用户精心维护，工作日志走日记树。

#### Scenario: 默认弹窗确认

- **当** 用户对 `dev` 会话执行归档且 `devArchiveQuickSave` 为 `false`
- **则** 系统**必须**弹窗展示摘要供编辑确认。

#### Scenario: 起草失败降级

- **当** Agent 起草失败
- **则** 系统**不得**阻塞归档；以仅含元信息的摘要文件落盘。
