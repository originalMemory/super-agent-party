# 伴侣型 Agent：角色卡 OpenClaw 扩展约定

本文档定义 **multiLovers 分支**中，如何通过**角色卡扩展字段**引入 OpenClaw 式人设分层能力。实现以 OpenSpec `openspec/changes/lover-sap-foundation/` 为准。

## 核心策略

**在 SAP 现有角色卡体系上扩展**，不创建独立的 Markdown SSOT 文件体系。OpenClaw 概念映射为角色卡字段或复用已有通路。

## OpenClaw 映射

| OpenClaw 概念 | SAP 映射 | 存储 |
|---------------|----------|------|
| **SOUL.md**（元层原则） | `memories[i].soul`（新增字段） | settings JSON |
| **IDENTITY.md**（叙事身份） | `memories[i].description` + `personality` + `systemPrompt`（已有字段覆盖） | settings JSON |
| **USER.md**（用户档案） | `memorySettings.userProfile`（新增字段，全局共享） | settings JSON |
| **MEMORY.md**（长期记忆） | `memories[i].memoryNotes`（新增字段） | settings JSON |
| **AGENTS.md**（操作约束） | 全局 `system_prompt` + 工作区 `.agent/AGENTS.md`（已有通路） | 现有路径不变 |

## 字段职责

| 字段 | 级别 | 职责 | 注入位置 |
|------|------|------|----------|
| **`userProfile`** | 全局（memorySettings） | 用户姓名/偏好/重要日期，所有角色共享 | ① 最前 |
| **`soul`** | 角色卡级 | 元层原则：价值观、语调、主动性边界 | ② userProfile 之后 |
| **`description`** | 角色卡级 | 角色设定（已有） | ⑤ |
| **`personality`** | 角色卡级 | 性格设定（已有） | ⑥ |
| **`mesExample`** | 角色卡级 | 对话示例（已有） | ⑦ |
| **`systemPrompt`** | 角色卡级 | 额外系统提示（已有） | ⑧ |
| **`genericSystemPrompt`** | 全局（memorySettings） | 通用系统提示（已有） | ⑨ |
| **`memoryNotes`** | 角色卡级 | 手写长期记忆，与 mem0 互补 | ⑩ genericSystemPrompt 之后 |
| **mem0 recall** | 角色卡级 | 自动向量记忆（已有） | ⑪ 最后 |

## AGENTS.md 处理

**不进角色卡**。操作约束层复用 SAP 已有通路：

1. **全局 `system_prompt`**：对所有角色卡生效，位于 `messages[0]` 最前部
2. **工作区 `.agent/AGENTS.md`**：绑定 `cc_path` 时由 `tools_change_messages` 注入

理由：AGENTS.md 定义"环境如何运转"而非"角色是谁"，属环境约束非角色属性。

## 记忆体系

| 层次 | 机制 | 写入方 | 注入时机 | 说明 |
|------|------|--------|----------|------|
| `soul` | 角色卡字段 | 用户 | 每轮 bootstrap 常驻 | 不进 FTS |
| `userProfile` | memorySettings 字段 | 用户 | 每轮 bootstrap 常驻 | 不进 FTS |
| `memoryNotes` | 角色卡字段 | 用户 | 每轮 bootstrap 常驻 | **不进 FTS**——内容量可控，全文注入 |
| 日记树 FTS | SQLite FTS5 | 摘要回流 / 用户手写 | 每轮动态检索 | **核心记忆检索方式** |
| mem0 recall | 向量检索 | AI 自动提炼 | 每轮动态 | **默认关闭**，用户可手动开启 |

### 日记树 FTS（核心记忆检索）

- **索引范围**：`memorySettings.memoryDirPath`（默认 `{USER_DATA_DIR}/lover/memory/`）下递归 `.md`
- **路径可配置**：用户可在 memorySettings 中自定义日记树目录
- **实现**：SQLite FTS5（`py/lover_memory_fts.py` + `py/lover_fts_simple_auto.py`，从 lover 分支移植）
- **同步**：进程启动 + 后台按 `memorySettings.memoryIndexSyncMinutes`（默认 10 分钟）间隔同步
- **优势**：专有名词精确匹配（人名、游戏名、项目名）；索引内容用户可见可编辑；无冗余存储

### mem0（可选，默认关闭）

保留代码通路与 UI 配置。用户手动配置 embedding `providerId` 后可开启。

定位区分：memoryNotes = 精确事实（手写），日记树 FTS = 结构化日志（精确检索），mem0 = AI 自动提炼（模糊联想）。

## 会话模型

复用 SAP 既有「分组 + 会话」底座，收敛为两组固定结构：

- **主分组**：主会话（`kind=main`，单例）+ 开发会话（`kind=dev`，可多开）
- **归档分组**：归档主会话快照（`kind=archive`，只读）

开发会话与主会话**共享同一角色卡**的完整注入。归档时通过"摘要回流"产出日记 `.md`。

## AI 工具

系统向 AI 提供以下工具，让 AI 可以在对话中读写角色卡：

| 工具 | 功能 | 权限 |
|------|------|------|
| `get_character_card` | 读取当前角色卡字段 + userProfile | 需用户审批 |
| `update_character_card` | 修改角色卡指定字段（白名单限制） | 需用户审批 |
| `update_user_profile` | 修改全局用户档案 | 需用户审批 |

使用场景：AI 发现用户新事实 → 更新 memoryNotes；AI 根据反馈调整 soul / personality。

## 兼容性

- 所有新字段默认空值，老角色卡完全兼容
- 不删除任何现有功能（角色卡 CRUD、TTS 联动、VRM 联动、mem0 等）
- 品牌保持 super-agent-party

## 相关文档

- 角色卡体系详情：`docs/CHARACTER_CARD.md`
- OpenSpec 设计与任务：`openspec/changes/lover-sap-foundation/`
