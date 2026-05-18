## Why

在 **multiLovers** 分支上，基于 Super Agent Party（SAP）的角色卡体系，引入 **OpenClaw 式人设分层**（SOUL / USER / MEMORY）作为角色卡的扩展字段，实现**伴侣型 Agent** 的人设深度与记忆连续性。

**核心决策**：**保留角色卡及其与 TTS 音色、VRM 形象的同名联动逻辑**，而非 lover 分支原方案中的"删除酒馆角色卡、用独立 Markdown 文件替代"。理由：

1. 角色卡关联链深：TTS `newtts`、VRM `newVRM`、`memorySettings`、`characterBook`、mem0、开场白、群聊等均依赖 `memories[]`，完全删除代价极高
2. 多角色切换是 SAP 差异化能力，multiLovers 天然需要"切换伴侣 = 切换人设 + 语音 + 形象"
3. 原有 `description` / `personality` / `systemPrompt` / `mesExample` 已覆盖 OpenClaw `IDENTITY.md` 的内容域

**品牌**：保持 super-agent-party。**无 loverMode**：伴侣能力是角色卡的功能增强，不是独立模式。

## What Changes（分阶段）

### 阶段 A — 角色卡数据模型扩展

- `memories[]` 每项新增 **`soul`**（元层原则）字段
- `memorySettings` 新增 **`userProfile`**（用户档案，所有角色共享）、**`memoryNotes`**（记忆笔记，所有角色共享）
- **AGENTS.md 不进角色卡**：复用全局 `system_prompt` + 工作区 `.agent/AGENTS.md`（已有通路，方案 A）
- **AI 工具**：新增 `get_character_card` / `update_character_card` / `update_user_profile` / `update_memory_notes`，让 AI 可以读取和修改角色卡字段及全局配置（需用户审批）
- 前端角色卡编辑界面增加对应 tab/表单
- 调整注入顺序：`userProfile` → `soul` → `description` → `personality` → `mesExample` → `systemPrompt` → `genericSystemPrompt` → `memoryNotes` → `FTS recall` → `mem0 recall`（可选，默认关闭）

### 阶段 B — 日记树 FTS 记忆检索

- **日记树 FTS**：`{USER_DATA_DIR}/lover/memory/` 下递归的 `.md` 文件纳入 SQLite FTS5 索引，每轮用户消息触发检索，命中片段注入 dynamic 块
- **memoryNotes 常驻注入**：全局共享的手写记忆全文注入 bootstrap，不进 FTS（内容量可控，参考 OpenClaw MEMORY.md）
- **mem0 可选默认关闭**：保留代码通路但默认不启用——向量检索对专有名词支持差，且每句存储过于冗余；用户可手动开启作为补充
- 复用 lover 分支已有实现：`py/lover_memory_fts.py`、`py/lover_fts_simple_auto.py`

### 阶段 C — 会话模型与摘要回流

沿用 lover 分支已验证的会话模型设计，与角色卡体系融合：

- 主分组（`main` 单例 + 0..N `dev`）+ 归档分组（`archive` 只读）
- `dev` 会话与 `main` 共享当前选中角色卡的完整 bootstrap
- 摘要回流：`dev` 归档时由 Agent 起草摘要 → 用户确认 → 写入角色卡的 `memoryNotes` 或独立日记文件

### 阶段 D — 会话启动序列

- 新建/重置会话时注入启动指令，让模型用 `soul` 定义的 persona 主动问候
- 可选注入最近的 `memoryNotes` 摘要作为启动记忆前言

### 阶段 E — backlog

- 桌面主动感知
- 心跳机制（参照 OpenClaw HEARTBEAT）

## Capabilities

### New Capabilities

- `soul`：角色卡级元层原则（价值观、语调、主动性、边界），注入优先级最高
- `userProfile`：用户档案，全局共享，所有角色可感知用户偏好
- `memoryNotes`：手写可见的长期记忆，全局共享，常驻注入 bootstrap
- AI 工具：`get_character_card` / `update_character_card` / `update_user_profile` / `update_memory_notes`，让 AI 可读写角色卡及全局配置
- 日记树 FTS：用户可配置目录下的 `.md` 文件，SQLite FTS5 每轮检索注入
- 会话模型：主会话/开发会话/归档的固定分组结构
- 摘要回流：开发会话归档时产出结构化日志

### Modified Capabilities

- 角色卡注入顺序调整：新增 `userProfile` → `soul` 在最前
- `memoryNotes` 作为全局共享的记忆维度加入注入链
- mem0 默认关闭（保留代码通路，用户可手动开启）

## Impact

- **后端**：`generate_stream_response` 注入链增加 `userProfile`、`soul`、`memoryNotes`（全局）、FTS recall 四个注入点；保留 `cur_memory` 整套注入逻辑（非删除）；新增 `py/character_card_tools.py` AI 工具模块（含 `update_memory_notes`）；日记树 FTS 索引与检索模块（复用 lover 分支实现）；会话模型新增 `kind`/`workspace_path`/`archived_at`/`summary_path` 字段
- **前端**：角色卡编辑界面新增 SOUL tab；新增独立「用户档案与记忆」Tab（含 memoryNotes、userProfile、日记树配置）；会话分组 UI 收敛为固定两组
- **数据模型**：`memories[]` 增加 `soul` 字段；`memorySettings` 增加 `userProfile`、`memoryNotes`、`memoryDirPath`、`memoryIndexSyncMinutes` 字段；会话表增加 `kind` 等字段
- **兼容性**：新字段均可选（空字符串时跳过注入），对未配置新字段的老角色卡完全兼容
