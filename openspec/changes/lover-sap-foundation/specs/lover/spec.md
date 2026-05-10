## ADDED Requirements

### Requirement: 单一产品线（无模式开关）

产品必须为 **lover 单一形态**：**不得**实现 `loverMode` 或等价开关以保留 SAP 酒馆完整 UI；**不得**将酒馆角色卡、换卡作为主路径。

#### Scenario: 无换卡

- **当** 用户使用主界面发起对话
- **则** 不得提供「更换角色卡」类交互。

---

### Requirement: Markdown SSOT 与 USER / IDENTITY / SOUL

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

系统必须在 **每次用户发送消息、调用模型之前**，对 **记忆语料集合** 执行 **SQLite FTS5**：至少包含 **`USER_DATA_DIR/lover/MEMORY.md`** 与 **`USER_DATA_DIR/lover/memory/`** 下 **递归**的 **`.md`** 文件（推荐 **`lover/memory/YYYY/MM/<日记>.md`**，实现 **不**强制校验日期）。记忆根目录为 **`USER_DATA_DIR/lover`**（**与 `CLISettings.cc_path` 无关**）。查询文本 **倾向** 为当前用户消息（可从多模态消息中提取纯文本）。索引库 **`{USER_DATA_DIR}/lover/memory_index.sqlite`**，**不得**当作唯一 SSOT。索引刷新 **不得**绑定在每次查询路径上；同步间隔 **`loverSettings.memoryIndexSyncIntervalMinutes`**（默认 10 分钟）；**进程启动**与**后台周期**调用 **`sync_memory_index`**（见 `server.py` lifespan）。实现 **应尝试** 自动获取并加载 **wangfenjin/simple**（`tokenize='simple'` / `simple_query()`，缓存路径见实现）；失败则使用内置分词降级；换分词器须重建索引文件。

系统 **不得**将 **`USER.md` / `IDENTITY.md` / `SOUL.md` / `AGENTS.md`** 纳入该 FTS 默认索引范围。

系统 **不得**依赖 **mem0** 或同类向量记忆栈完成本轮注入；长期记忆 **读路径** 以 FTS 命中片段为准。

#### Scenario: FTS 分词降级

- **当** 目标 SQLite 不支持首选 FTS5 分词器（如 trigram）
- **则** 必须降级到其它内置 tokenize 或默认 FTS5，且不得崩溃。

---

### Requirement: 主会话、归档与重置

产品必须支持 **主会话**、**归档**、**主动归档**、**重置会话**（重置语义须文档化）。

#### Scenario: 主动归档

- **当** 用户主动归档
- **则** 当前主会话进入归档并可继续新的主会话链路。

#### Scenario: 重置

- **当** 用户重置会话
- **则** 消息上下文按定义清空或换新线程；不得静默清空全部长期记忆存储除非明示。
