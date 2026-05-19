## 目标陈述

在 SAP 现有**角色卡体系**（`memories[]` + `memorySettings`）之上，引入 **OpenClaw 式人设分层**作为角色卡的**扩展字段**，实现伴侣型 Agent 的人设深度与记忆连续性。

**核心原则**：保留角色卡及其与 TTS 音色、VRM 形象的同名联动逻辑，通过**在角色卡上新增字段**的方式引入 SOUL / 用户档案 / 记忆笔记能力，而非创建独立的 Markdown SSOT 文件体系。

---

## OpenClaw 概念与角色卡字段映射

| OpenClaw 概念 | 映射方式 | 存储位置 |
|---------------|----------|----------|
| **SOUL.md**（元层原则） | 角色卡新增 **`soul`** 字段（Markdown 文本） | `memories[i].soul` |
| **IDENTITY.md**（叙事身份） | 已有字段覆盖：`description` + `personality` + `systemPrompt` | `memories[i].description` 等 |
| **USER.md**（用户档案） | `memorySettings` 新增 **`userProfile`** 字段（Markdown 文本），所有角色共享 | `memorySettings.userProfile` |
| **MEMORY.md**（长期记忆） | `memorySettings` 新增 **`memoryNotes`** 字段（Markdown 文本），所有角色共享 | `memorySettings.memoryNotes` |
| **AGENTS.md**（操作约束） | **方案 A：不进角色卡**。复用全局 `system_prompt` + 工作区 `.agent/AGENTS.md`（已有通路） | 现有路径不变 |

### 字段详情

#### `soul`（新增，角色卡级）

元层运行原则，定义"我是什么样的存在"。包括：核心价值观、诚实原则、与用户的关系哲学、语调风格总纲、主动性边界。

```
memories[i].soul = "你是一个温暖但有边界感的伴侣 AI..."
```

注入优先级高于 `description` / `personality` 等叙事层字段，位于 `userProfile` 之后。

#### `userProfile`（新增，全局共享）

用户档案，所有角色卡共享。包括：用户姓名/昵称、偏好、重要日期、沟通习惯。

```
memorySettings.userProfile = "用户叫小明，喜欢被称为'明哥'..."
```

注入优先级最高（在 `soul` 之前），让所有角色均可感知用户偏好。

#### `memoryNotes`（新增，全局共享）

手写的长期记忆笔记，所有角色共享。与 mem0 自动向量记忆互补：mem0 由 AI 自动提炼，`memoryNotes` 由用户手工维护，内容完全可见可控。`memoryNotes` 沉淀的是与**用户**相关的长期事实与约定，而非特定角色属性，因此属于全局级。

```
memorySettings.memoryNotes = "- 2026-05-01 一起看了《星际穿越》\n- 喜欢在晚上聊天..."
```

注入位置在 `genericSystemPrompt` 之后、FTS recall 之前。

---

## AGENTS.md 处理（方案 A）

**不引入角色卡级 AGENTS 字段**。操作约束层复用 SAP 已有的两条通路：

1. **全局 `system_prompt`**：在 settings 中配置的全局系统提示，对所有角色卡生效
2. **工作区 `.agent/AGENTS.md`**：当会话绑定了工作区（`cc_path`）时，由 `tools_change_messages` 中已有逻辑注入

### 理由

- AGENTS.md 定义的是"工作区如何运转"（安全规则、权限边界、数据目录约定），本质上是**环境约束**而非**角色属性**
- SAP 的 `system_prompt` + `.agent/AGENTS.md` 已覆盖此需求
- 避免在角色卡上堆积过多非人格字段，保持数据模型清晰

### 与 OpenClaw 的差异说明

OpenClaw 要求 AGENTS.md **必注入、优先级最高**。在 SAP 体系中，全局 `system_prompt` 天然位于 `messages[0]` 最前部（`chat_endpoint` 中 `prepend`），已满足"优先级最高"语义。工作区级 `.agent/AGENTS.md` 在 `tools_change_messages` 中注入，位于工具/能力说明区域。

---

## 数据模型变更

### `memories[]` 新增字段

```json
{
  "name": "小樱",
  "description": "...",
  "personality": "...",
  "systemPrompt": "...",
  "mesExample": "...",
  "characterBook": {...},
  "firstMes": "...",
  "alternateGreetings": [...],
  "avatar": "...",
  "providerId": "...",
  "infer": true,

  "soul": ""
}
```

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `soul` | `string` | `""` | 元层原则 Markdown；空时跳过注入 |

### `memorySettings` 新增字段

```json
{
  "is_memory": true,
  "selectedMemory": "...",
  "userName": "...",
  "genericSystemPrompt": "...",
  "memoryLimit": 5,

  "userProfile": "",
  "memoryNotes": "",
  "memoryDirPath": "",
  "memoryIndexSyncMinutes": 10
}
```

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `userProfile` | `string` | `""` | 用户档案 Markdown；空时跳过注入；所有角色共享 |
| `memoryNotes` | `string` | `""` | 手写长期记忆 Markdown；空时跳过注入；所有角色共享 |
| `memoryDirPath` | `string` | `""` | 日记树根目录；空值时使用 `{USER_DATA_DIR}/lover/memory/` |
| `memoryIndexSyncMinutes` | `number` | `10` | FTS 索引同步间隔（分钟） |

### 兼容性

所有新字段默认为空字符串，空时跳过注入。**对未配置新字段的老角色卡完全兼容**——行为与现有版本一致。

### 设置模板

`config/settings_template.json` 中 `memories[]` 项新增 `soul`（默认 `""`），`memorySettings` 新增 `userProfile`、`memoryNotes`（默认 `""`）。

---

## System Prompt 注入顺序

在 `generate_stream_response` 中，对 `messages[0]` 的 system content 进行 `content_append`。**在现有注入链的基础上扩展**，而非替换。

### 完整注入顺序

```
messages[0] (system)
 │
 ├── [全局 system_prompt]               ← chat_endpoint prepend（已有）
 │
 ├── ① 用户档案（userProfile）          ← 新增，非空时注入
 ├── ② 元层原则（soul）                 ← 新增，非空时注入
 │
 ├── ③ 默认用户名说明                   ← 已有，userName 配置时
 ├── ④ 世界观设定（characterBook）       ← 已有，关键词命中时
 ├── ⑤ 角色设定（description）           ← 已有
 ├── ⑥ 性格设定（personality）           ← 已有
 ├── ⑦ 对话示例（mesExample）            ← 已有
 ├── ⑧ 角色系统提示（systemPrompt）      ← 已有
 ├── ⑨ 通用系统提示（genericSystemPrompt）← 已有
 │
 ├── ⑩ 记忆笔记（memoryNotes）          ← 新增，非空时全文常驻注入
 ├── ⑪ 相关回忆（FTS recall）           ← 新增，日记树 FTS 检索命中片段
 ├── ⑫ 相关记忆（mem0 recall）          ← 已有，默认关闭，手动开启时生效
 │
 └── [tools_change_messages 追加]        ← TTS/工具/视觉等（已有）
     └── [.agent/AGENTS.md]              ← 工作区约束（已有）
```

### 注入格式

每个新增块使用 Markdown 标题隔离，与现有格式对齐：

```
## 用户档案
{userProfile 内容，替换 {{user}} / {{char}}}

## 元层原则
{soul 内容，替换 {{user}} / {{char}}}

## 记忆笔记
{memoryNotes 内容，替换 {{user}} / {{char}}}
```

### 实现位置

修改 `server.py` 的 `generate_stream_response` 函数，在现有 `cur_memory` 注入链（约 3629-3711 行）的**前面**插入 `userProfile` 和 `soul`，在**后面**插入 `memoryNotes`。

```python
# === 新增：userProfile（全局共享） ===
user_profile = memory_settings.get("userProfile", "")
if user_profile:
    user_profile = user_profile.replace("{{user}}", user_name).replace("{{char}}", cur_name)
    content_append(messages, f"\n## 用户档案\n{user_profile}")

# === 新增：soul（角色卡级） ===
soul = cur_memory.get("soul", "")
if soul:
    soul = soul.replace("{{user}}", user_name).replace("{{char}}", cur_name)
    content_append(messages, f"\n## 元层原则\n{soul}")

# --- 以下为现有注入链 ---
# ③ userName  ④ characterBook  ⑤ description  ⑥ personality
# ⑦ mesExample  ⑧ systemPrompt  ⑨ genericSystemPrompt

# === 新增：memoryNotes（全局共享，常驻注入） ===
memory_notes = memory_settings.get("memoryNotes", "")
if memory_notes:
    memory_notes = memory_notes.replace("{{user}}", user_name).replace("{{char}}", cur_name)
    content_append(messages, f"\n## 记忆笔记\n{memory_notes}")

# === 新增：日记树 FTS recall ===
# fts_results = search_memory(user_prompt)  # lover_memory_fts.py
# if fts_results:
#     content_append(messages, f"\n## 相关回忆\n{fts_results}")

# --- 现有：mem0 recall（默认关闭） ---
# ⑫ m0.search(user_prompt) — 仅当用户手动开启 mem0 时
```

---

## AI 工具：角色卡查看与修改

当前 SAP 没有给 AI 提供查看/修改角色卡的工具。角色卡的增删改查全部在前端完成（`vue_methods.js` 的 `addMemory` / `changeMemory` / `removeMemory`），AI 无法在对话中感知或修改角色卡内容（除了通过 bootstrap 注入被动读取）。

**新增以下 AI 工具**，注册到 `dispatch_tool` 工具映射表：

### `get_character_card`

读取当前选中角色卡的完整信息或指定字段。

```json
{
  "name": "get_character_card",
  "description": "读取当前角色卡的信息。可指定字段名获取特定内容，不指定则返回全部。",
  "parameters": {
    "type": "object",
    "properties": {
      "fields": {
        "type": "array",
        "items": { "type": "string" },
        "description": "要读取的字段列表，如 ['soul', 'memoryNotes', 'description']。不传则返回全部字段。"
      }
    }
  }
}
```

返回当前 `memorySettings.selectedMemory` 对应角色卡的字段内容。同时返回 `memorySettings.userProfile` 和 `memorySettings.memoryNotes`。

### `update_character_card`

修改当前选中角色卡的指定字段。

```json
{
  "name": "update_character_card",
  "description": "修改当前角色卡的指定字段。修改后自动保存。",
  "parameters": {
    "type": "object",
    "properties": {
      "field": {
        "type": "string",
        "description": "要修改的字段名，如 'soul', 'description', 'personality' 等"
      },
      "value": {
        "type": "string",
        "description": "新的字段值"
      }
    },
    "required": ["field", "value"]
  }
}
```

**可写字段白名单**：`soul`、`description`、`personality`、`systemPrompt`、`mesExample`。**不可通过工具修改** `name`、`avatar`、`providerId` 等结构性字段。`memoryNotes` 已移至全局级，通过 `update_memory_notes` 工具修改。

### `update_user_profile`

修改全局用户档案。

```json
{
  "name": "update_user_profile",
  "description": "修改所有角色共享的用户档案。修改后自动保存。",
  "parameters": {
    "type": "object",
    "properties": {
      "value": {
        "type": "string",
        "description": "新的用户档案内容（Markdown）"
      }
    },
    "required": ["value"]
  }
}
```

### `update_memory_notes`

修改全局记忆笔记（所有角色共享）。

```json
{
  "name": "update_memory_notes",
  "description": "修改所有角色共享的记忆笔记（memoryNotes）——长期事实与约定。修改后自动保存。",
  "parameters": {
    "type": "object",
    "properties": {
      "value": {
        "type": "string",
        "description": "新的记忆笔记内容（Markdown）"
      }
    },
    "required": ["value"]
  }
}
```

### 实现位置

- 工具函数：`py/character_card_tools.py`（新建）
- 注册：`server.py` `dispatch_tool` 的 `_TOOL_HOOKS` 映射表
- 权限：归入 `SENSITIVE_TOOLS`，需用户审批
- 保存：调用现有 `save_settings()` 整包写入 SQLite

### 使用场景

- AI 主动读取 `memoryNotes` 来感知用户偏好，提供个性化回复
- AI 在对话中发现新的用户事实（生日、偏好等），主动更新 `memoryNotes` 或 `userProfile`
- AI 根据对话反馈调整自身 `soul` 或 `personality`
- 与 OpenClaw 的"AI 维护 MEMORY.md"能力对齐

---

## 前端变更

### 角色卡编辑界面

在现有角色卡编辑表单中新增一个 tab：

1. **SOUL / 元层原则**：Markdown 文本编辑区，对应 `memories[i].soul`

### 用户档案与记忆 Tab

新增独立 Tab「用户档案与记忆」，与角色卡配置同级（非嵌套在角色卡编辑中），包含：

1. **日记树目录**：路径输入框，对应 `memorySettings.memoryDirPath`
2. **FTS 同步间隔**：数字输入，对应 `memorySettings.memoryIndexSyncMinutes`
3. **记忆笔记**：Markdown 文本编辑区，对应 `memorySettings.memoryNotes`（所有角色共享）
4. **用户档案**：Markdown 文本编辑区，对应 `memorySettings.userProfile`（所有角色共享，放最下方，内容可能较长）

### 无需删除的现有 UI

- 角色卡列表、换卡、酒馆主导航 → **保留**
- TTS 多角色语音 → **保留**
- VRM 多角色外观 → **保留**
- mem0 相关设置 → **保留**（默认关闭，用户可手动开启）

---

## 会话模型（延续 lover 设计，适配角色卡体系）

复用 SAP 既有「分组 + 会话」底座，**收敛**为两组固定结构。

```
主分组（id=default, fixed）
├── 主会话（kind=main，单例，不可删；可"重置"、可"主动归档"）
├── 开发会话 #1（kind=dev，可多开）
├── 开发会话 #2
└── ...

归档分组（id=archive, fixed）
├── 归档主会话快照-2026-05-10（kind=archive, original_kind=main）
├── 归档开发会话-2026-05-15（kind=archive, original_kind=dev）
└── ...
```

### 会话对象新增字段

| 字段 | 取值 | 说明 |
|------|------|------|
| `kind` | `'main' \| 'dev' \| 'archive'` | 强类型；主分组内 `kind=main` 至多 1 条 |
| `archived_at` | `timestamp \| null` | `archive` 必填 |
| `summary_path` | `string \| null` | dev 归档时写入摘要落盘路径 |
| `original_kind` | `'main' \| 'dev' \| null` | 归档时记录原始类型，用于 UI 区分图标 |

**不新增 `workspace_path`**：所有会话统一使用全局 `CLISettings.cc_path` 作为工作区路径。理由：没有不同开发会话使用不同目录的实际场景。

### Bootstrap（main 与 dev 完全一致）

`dev` 与 `main` 共享同一套 bootstrap 注入，无差异：

| 注入项 | 说明 |
|--------|------|
| 全局 system_prompt | ✓ |
| userProfile | ✓ |
| soul（当前角色卡） | ✓ |
| 现有字段注入（desc/personality/...） | ✓ |
| memoryNotes（全局） | ✓ |
| 日记树 FTS recall | ✓ |
| mem0 recall | 默认关闭，手动开启 |
| 工作区 .agent/ | 统一按全局 `CLISettings.cc_path` |

**原则**：开发会话与主会话**共享同一角色卡**的完整注入——是「同一个她，今天陪你写代码」。

### 后端 API（参考 lover 分支）

| API | 方法 | 说明 |
|-----|------|------|
| `/api/lover/reset-main-session` | POST | 清空主会话消息，保留会话槽位 |
| `/api/lover/archive-main-session` | POST | 深拷贝快照到归档分组（`original_kind=main`），原会话清空重建 |
| `/api/lover/create-dev-session` | POST | 在主分组创建 `kind=dev` 会话 |
| `/api/lover/archive-dev-session` | POST | 落盘摘要 → 追加摘要消息（保留对话历史）→ 移入归档分组（`original_kind=dev`） |

### lifespan 初始化

启动时确保：
1. `default` 和 `archive` 两个固定分组存在
2. 主分组内存在 `kind=main` 单例（不存在则自动创建）

---

## 摘要回流

开发会话主动归档时触发：

1. Agent 基于本会话上下文起草日志摘要（任务标题、关键产出/决策、未决问题）
2. 弹窗给用户编辑/确认，目标文件名预填 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`
3. 确认 → 落盘 → 追加摘要消息到对话末尾（保留原有消息历史）→ 写入 `summary_path` → 移入归档分组
4. 下一轮 `sync_memory_index` 后被 FTS 索引，主会话即可通过 FTS 召回该摘要
5. 降级：Agent 起草失败时，仅含元信息的摘要文件

摘要落盘路径位于 `{USER_DATA_DIR}/lover/memory/` 下，**不写入角色卡的 `memoryNotes`**——memoryNotes 是用户精心维护的长期事实，工作日志走日记树。

---

## 会话启动序列

新建或重置会话时，自动注入启动提示词：

1. 后端检测 `is_new_session = True`
2. 在本次请求的用户消息末尾追加启动指令（不存入历史）
3. 可选注入最近日记摘要作为启动记忆前言（`dailyMemoryDays`=2，`maxTotalChars`=2800）
4. 模型用 `soul` 定义的 persona 主动问候用户

---

## 记忆体系（分层）

| 层次 | 机制 | 写入方 | 注入时机 | 索引范围 |
|------|------|--------|----------|----------|
| **soul** | 角色卡字段 | 用户 | 每轮 bootstrap 常驻 | — |
| **userProfile** | memorySettings 字段 | 用户 | 每轮 bootstrap 常驻 | — |
| **memoryNotes** | memorySettings 字段（全局共享） | 用户 / AI | 每轮 bootstrap 常驻 | **不进 FTS**（内容量可控，参考 OpenClaw MEMORY.md 约 180 行） |
| **日记树 FTS** | SQLite FTS5 | 摘要回流 / 用户手写 | 每轮动态检索 | `{USER_DATA_DIR}/lover/memory/` 下递归 `.md` |
| **mem0 recall** | 向量检索 | AI 自动提炼 | 每轮动态（**默认关闭**） | — |

### 为什么 FTS 优于 mem0 作为主记忆检索

1. **专有名词**：向量嵌入对新词（人名、游戏名、项目名）的表征不准确，FTS 精确匹配无此问题
2. **冗余度**：mem0 每句对话都存，产生大量低价值条目；FTS 只索引用户精心维护的日记 `.md`，信噪比高
3. **可见性**：FTS 索引的是用户可直接查看编辑的 Markdown 文件，mem0 的向量库对用户不透明
4. **确定性**：FTS 命中结果可预期，向量相似度搜索结果有随机性

### 日记树 FTS

复用 lover 分支已有实现（`py/lover_memory_fts.py`、`py/lover_fts_simple_auto.py`）。

| 配置项 | 存储位置 | 默认值 | 说明 |
|--------|----------|--------|------|
| 日记树根目录 | `memorySettings.memoryDirPath` | `{USER_DATA_DIR}/lover/memory/` | 可由用户在前端配置，递归收录所有 `.md` |
| 索引库路径 | 自动派生 | `{memoryDirPath}/../memory_index.sqlite` | FTS5 数据库，跟随日记树目录 |
| 同步间隔 | `memorySettings.memoryIndexSyncMinutes` | `10` | 启动时 sync 一次 + 后台周期同步 |
| 分词器 | — | 优先 wangfenjin/simple → trigram → unicode61 | 自动下载缓存 |

**索引排除**：`soul`、`userProfile`、`memoryNotes` 字段内容**不进入** FTS 索引（已全文常驻注入，索引会造成重复命中）。

**查询时机**：每次用户发送消息后、调用模型前，用当前用户消息作为查询文本。

**注入格式**：命中片段以 `## 相关回忆` 标题注入 dynamic 块，与 bootstrap 内容分区隔离。

### mem0（可选，默认关闭）

保留 mem0 代码通路与 UI 配置，但默认不启用。用户可在角色卡 embedding 设置中手动开启。

开启后行为不变：每轮 `m0.search` 检索 + 请求结束后 `m0.add` 自动提炼。

**定位区分**：
- **memoryNotes**（手写）= 精确事实，用户完全控制
- **日记树 FTS** = 结构化日志与事件回忆，精确检索
- **mem0**（可选）= AI 自动提炼的模糊联想，向量近似匹配

---

## 架构触点

| 区域 | 触点 |
|------|------|
| **后端** | `server.py` `generate_stream_response`：在现有 `cur_memory` 注入链中插入 `userProfile` / `soul` / `memoryNotes` / FTS recall 四个注入点 |
| **后端** | `py/character_card_tools.py`（新建）：`get_character_card` / `update_character_card` / `update_user_profile` / `update_memory_notes` AI 工具 |
| **后端** | `server.py` `dispatch_tool`：注册角色卡工具到 `_TOOL_HOOKS` + `SENSITIVE_TOOLS` |
| **后端** | `py/lover_memory_fts.py` + `py/lover_fts_simple_auto.py`：日记树 FTS 索引与检索（从 lover 分支移植） |
| **后端** | `py/get_setting.py`：`load_settings` / `save_settings` 自动兼容新字段（JSON 整包，无需 schema 迁移）；`load_covs` / `save_covs` 管理会话 JSON |
| **后端** | `config/settings_template.json`：新增字段默认值 |
| **后端** | `server.py` `lifespan`：确保固定分组 + 主会话单例 |
| **后端** | `server.py` `api/lover/*`：会话管理 API（reset-main / archive-main / create-dev / archive-dev） |
| **前端** | `static/index.html`：角色卡编辑表单新增 SOUL 区域；新增独立「用户档案与记忆」Tab（含 memoryNotes、userProfile、日记树配置） |
| **前端** | `static/js/vue_data.js`：`memories[]` 初始结构新增 `soul`；`memorySettings` 新增 `userProfile`、`memoryNotes` |
| **前端** | `static/js/vue_methods.js`：`addMemory` 时初始化 `soul`；`autoSaveSettings` 无需改动（已整包保存） |

---

## 设计原则

1. **扩展不替换**：在角色卡上新增字段，不删除/替代现有字段与通路
2. **向后兼容**：新字段空值时行为与现有版本一致
3. **关注点分离**：`soul` = 元层原则，`description`/`personality` = 叙事身份，`memoryNotes` = 全局可见记忆（用户级），`mem0` = 自动记忆
4. **角色卡为锚点**：切换角色 = 切换人设 + 语音 + 形象 + soul，一致联动；`memoryNotes` 和 `userProfile` 为全局共享，不随角色切换
5. **AGENTS.md 是环境约束**：不进角色卡，复用全局 system_prompt + 工作区 .agent/

---

## 风险

- **注入长度膨胀**：`userProfile` + `soul` + `memoryNotes` + 现有字段 + FTS recall 可能导致 system prompt 过长。缓解：前端提示各字段建议字数；FTS 命中条数可配置上限
- **FTS 分词兼容性**：wangfenjin/simple 与不同平台 SQLite ABI 可能不兼容。缓解：自动降级到 trigram → unicode61；更换分词器须重建索引
- **摘要保真**：Agent 起草的摘要可能含幻觉。缓解：默认弹窗确认
- **会话调性串味**：开发会话仍走角色卡 bootstrap，可能在工程上下文里出现角色语气。缓解：可接受（用户偏好），prompt 中提示当前任务语境

---

## 已决议清单

1. **保留角色卡**：`memories[]` + `memorySettings` 体系完整保留，不删除酒馆 UI
2. **OpenClaw 映射**：SOUL → `soul` 字段（角色卡级）；USER → `userProfile` 字段（全局）；MEMORY → `memoryNotes` 字段（全局）；IDENTITY → 已有字段覆盖
3. **AGENTS.md**：方案 A，复用全局 system_prompt + 工作区 .agent/AGENTS.md
4. **日记树 FTS**：核心记忆检索方式，索引 `lover/memory/` 下递归 `.md`，每轮动态注入
5. **mem0 可选默认关闭**：保留代码通路，用户可手动开启
6. **注入顺序**：userProfile → soul → 现有链 → memoryNotes → FTS recall → mem0（可选）
7. **兼容性**：所有新字段默认空值，向后兼容
8. **会话模型**：固定两组结构（主分组 + 归档分组），沿用 lover 设计；新增 `original_kind` 记录归档前原始类型
9. **不新增 workspace_path**：所有会话统一使用全局 `CLISettings.cc_path`，无需会话级工作区绑定
10. **归档保留消息**：dev 归档时保留原有消息历史 + 追加摘要消息，不删除对话
11. **品牌**：保持 super-agent-party
