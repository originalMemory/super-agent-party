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
| **MEMORY.md**（长期记忆） | 角色卡新增 **`memoryNotes`** 字段（Markdown 文本） | `memories[i].memoryNotes` |
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

#### `memoryNotes`（新增，角色卡级）

手写的长期记忆笔记。与 mem0 自动向量记忆互补：mem0 由 AI 自动提炼，`memoryNotes` 由用户手工维护，内容完全可见可控。

```
memories[i].memoryNotes = "- 2026-05-01 一起看了《星际穿越》\n- 喜欢在晚上聊天..."
```

注入位置在 `genericSystemPrompt` 之后、mem0 recall 之前。

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

  "soul": "",
  "memoryNotes": ""
}
```

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `soul` | `string` | `""` | 元层原则 Markdown；空时跳过注入 |
| `memoryNotes` | `string` | `""` | 手写长期记忆 Markdown；空时跳过注入 |

### `memorySettings` 新增字段

```json
{
  "is_memory": true,
  "selectedMemory": "...",
  "userName": "...",
  "genericSystemPrompt": "...",
  "memoryLimit": 5,

  "userProfile": "",
  "memoryDirPath": "",
  "memoryIndexSyncMinutes": 10
}
```

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `userProfile` | `string` | `""` | 用户档案 Markdown；空时跳过注入；所有角色共享 |
| `memoryDirPath` | `string` | `""` | 日记树根目录；空值时使用 `{USER_DATA_DIR}/lover/memory/` |
| `memoryIndexSyncMinutes` | `number` | `10` | FTS 索引同步间隔（分钟） |

### 兼容性

所有新字段默认为空字符串，空时跳过注入。**对未配置新字段的老角色卡完全兼容**——行为与现有版本一致。

### 设置模板

`config/settings_template.json` 中 `memories[]` 项新增 `soul`、`memoryNotes`（默认 `""`），`memorySettings` 新增 `userProfile`（默认 `""`）。

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

# === 新增：memoryNotes（角色卡级，常驻注入） ===
memory_notes = cur_memory.get("memoryNotes", "")
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

返回当前 `memorySettings.selectedMemory` 对应角色卡的字段内容。同时返回 `memorySettings.userProfile`。

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
        "description": "要修改的字段名，如 'soul', 'memoryNotes', 'description', 'personality' 等"
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

**可写字段白名单**：`soul`、`memoryNotes`、`description`、`personality`、`systemPrompt`、`mesExample`。**不可通过工具修改** `name`、`avatar`、`providerId` 等结构性字段。

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

在现有角色卡编辑表单中新增两个 tab 或折叠区域：

1. **SOUL / 元层原则**：Markdown 文本编辑区，对应 `memories[i].soul`
2. **记忆笔记**：Markdown 文本编辑区，对应 `memories[i].memoryNotes`

### 用户档案编辑

在 `memorySettings` 编辑区域（角色卡设定区域的"通用"部分）新增：

- **用户档案**：Markdown 文本编辑区，对应 `memorySettings.userProfile`
- 提示文案：此档案对所有角色共享

### 无需删除的现有 UI

- 角色卡列表、换卡、酒馆主导航 → **保留**
- TTS 多角色语音 → **保留**
- VRM 多角色外观 → **保留**
- mem0 相关设置 → **保留**（默认关闭，用户可手动开启）

---

## 会话模型（延续 lover 设计，适配角色卡体系）

复用 SAP 既有「分组 + 会话」底座，**收敛**为两组固定结构。

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

### 会话表新增字段

| 字段 | 取值 | 说明 |
|------|------|------|
| `kind` | `'main' \| 'dev' \| 'archive'` | 强类型；同一时间主分组内 `kind=main` 至多 1 条 |
| `workspace_path` | `string \| null` | 仅 `dev` 可为非空 |
| `archived_at` | `timestamp \| null` | `archive` 必填 |
| `summary_path` | `string \| null` | 仅 `dev` 归档时写入 |

### Bootstrap 差异

| 项 | `main` | `dev` |
|----|--------|-------|
| 全局 system_prompt | ✓ | ✓ |
| userProfile | ✓ | ✓ |
| soul | ✓（当前角色卡） | ✓（当前角色卡） |
| 现有字段注入（desc/personality/...） | ✓ | ✓ |
| memoryNotes | ✓（常驻） | ✓（常驻） |
| 日记树 FTS recall | ✓ | ✓ |
| mem0 recall | 默认关闭，手动开启 | 默认关闭，手动开启 |
| 工作区 .agent/ | 按 cc_path | 按 workspace_path |

**原则**：开发会话与主会话**共享同一角色卡**的完整注入——是「同一个她，今天陪你写代码」。

---

## 摘要回流

开发会话主动归档时触发：

1. Agent 基于本会话上下文起草日志摘要（任务标题、关键产出/决策、未决问题）
2. 弹窗给用户编辑/确认，目标文件名预填 `lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`
3. 确认 → 落盘 → 删除会话历史 → 写入 `summary_path`
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
| **memoryNotes** | 角色卡字段 | 用户 | 每轮 bootstrap 常驻 | **不进 FTS**（内容量可控，参考 OpenClaw MEMORY.md 约 180 行） |
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
| **后端** | `py/character_card_tools.py`（新建）：`get_character_card` / `update_character_card` / `update_user_profile` AI 工具 |
| **后端** | `server.py` `dispatch_tool`：注册角色卡工具到 `_TOOL_HOOKS` + `SENSITIVE_TOOLS` |
| **后端** | `py/lover_memory_fts.py` + `py/lover_fts_simple_auto.py`：日记树 FTS 索引与检索（从 lover 分支移植） |
| **后端** | `py/get_setting.py`：`load_settings` / `save_settings` 自动兼容新字段（JSON 整包，无需 schema 迁移） |
| **后端** | `config/settings_template.json`：新增字段默认值 |
| **前端** | `static/index.html`：角色卡编辑表单新增 SOUL / 记忆笔记区域；memorySettings 编辑新增用户档案 |
| **前端** | `static/js/vue_data.js`：`memories[]` 初始结构新增 `soul`、`memoryNotes`；`memorySettings` 新增 `userProfile` |
| **前端** | `static/js/vue_methods.js`：`addMemory` 时初始化新字段；`autoSaveSettings` 无需改动（已整包保存） |

---

## 设计原则

1. **扩展不替换**：在角色卡上新增字段，不删除/替代现有字段与通路
2. **向后兼容**：新字段空值时行为与现有版本一致
3. **关注点分离**：`soul` = 元层原则，`description`/`personality` = 叙事身份，`memoryNotes` = 可见记忆，`mem0` = 自动记忆
4. **角色卡为锚点**：切换角色 = 切换人设 + 语音 + 形象 + soul + memoryNotes，一致联动
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
2. **OpenClaw 映射**：SOUL → `soul` 字段；USER → `userProfile` 字段；MEMORY → `memoryNotes` 字段；IDENTITY → 已有字段覆盖
3. **AGENTS.md**：方案 A，复用全局 system_prompt + 工作区 .agent/AGENTS.md
4. **日记树 FTS**：核心记忆检索方式，索引 `lover/memory/` 下递归 `.md`，每轮动态注入
5. **mem0 可选默认关闭**：保留代码通路，用户可手动开启
6. **注入顺序**：userProfile → soul → 现有链 → memoryNotes → FTS recall → mem0（可选）
7. **兼容性**：所有新字段默认空值，向后兼容
8. **会话模型**：固定两组结构（主分组 + 归档分组），沿用 lover 设计
9. **品牌**：保持 super-agent-party
