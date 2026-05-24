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
| **MEMORY.md**（长期记忆） | `memorySettings.memoryNotes`（新增字段，全局共享） | settings JSON |
| **HEARTBEAT.md**（心跳任务） | `lover/HEARTBEAT.md` 文件（动态，心跳时注入） | 文件系统 |
| **AGENTS.md**（操作约束） | 全局 `system_prompt` + 工作区 `.agent/AGENTS.md`（已有通路） | 现有路径不变 |

## 字段职责

| 字段 | 来源 | 职责 | 注入位置 |
|------|------|------|----------|
| **USER.md** | `lover/USER.md` 文件 | 用户姓名/偏好/重要日期，所有角色共享 | ① 最前 |
| **SOUL.md** | `lover/SOUL.md` 文件 | 元层原则：价值观、语调、主动性边界 | ② USER.md 之后 |
| **`description`** | 角色卡级 | 角色设定（已有） | ⑤ |
| **`personality`** | 角色卡级 | 性格设定（已有） | ⑥ |
| **`mesExample`** | 角色卡级 | 对话示例（已有） | ⑦ |
| **`systemPrompt`** | 角色卡级 | 额外系统提示（已有） | ⑧ |
| **`genericSystemPrompt`** | 全局（memorySettings） | 通用系统提示（已有） | ⑨ |
| **MEMORY.md** | `lover/MEMORY.md` 文件 | 手写长期记忆，所有角色共享，与 mem0 互补 | ⑩ genericSystemPrompt 之后 |
| **mem0 recall** | 角色卡级 | 自动向量记忆（已有） | ⑫ 最后 |

> 所有 `.md` 文件来源优先于配置字段（`soul`/`userProfile`/`memoryNotes`），配置字段仅作 fallback。

## AGENTS.md 处理

**不进角色卡**。操作约束层复用 SAP 已有通路：

1. **全局 `system_prompt`**：对所有角色卡生效，位于 `messages[0]` 最前部
2. **工作区 `.agent/AGENTS.md`**：绑定 `cc_path` 时由 `tools_change_messages` 注入

理由：AGENTS.md 定义"环境如何运转"而非"角色是谁"，属环境约束非角色属性。

## 记忆体系

| 层次 | 机制 | 写入方 | 注入时机 | 说明 |
|------|------|--------|----------|------|
| SOUL.md | `lover/SOUL.md` 文件 | 用户 | 每轮 bootstrap 常驻 | 不进 FTS |
| USER.md | `lover/USER.md` 文件 | 用户 | 每轮 bootstrap 常驻 | 不进 FTS |
| MEMORY.md | `lover/MEMORY.md` 文件 | 用户 / AI | 每轮 bootstrap 常驻 | **不进 FTS**——内容量可控，全文注入 |
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
| `get_character_card` | 读取当前角色卡字段 + userProfile + memoryNotes | 无需审批 |
| `update_character_card` | 修改角色卡指定字段（白名单：soul/description/personality/systemPrompt/mesExample） | 需用户审批 |
| `update_user_profile` | 修改全局用户档案 | 需用户审批 |
| `update_memory_notes` | 修改全局记忆笔记 | 需用户审批 |

使用场景：AI 发现用户新事实 → 更新 memoryNotes（全局）；AI 根据反馈调整 soul / personality。

## 桌面主动感知（Desktop Awareness）

**前端定时器**触发截图 → 发给视觉模型 → 判断是否需要主动关心（如深夜加班、久坐等）。

- **截图方式**：`pyautogui.screenshot()` → 缩放到 1280×720 → base64 发送
- **息屏检测**：截图后计算 64×64 缩略图的像素平均亮度；若低于阈值（≈全黑）则判定为锁屏/息屏状态，跳过本次感知（返回 `reason: "screen_off"`），不保存图片、不调用 LLM。macOS 下 `Cmd+Ctrl+Q` 锁屏后显示器关闭时，`screencapture` API 仍会"成功"返回纯黑帧，此检测避免浪费 token 和存储
- **跳过条件**：主分组内近期有会话活动（`skip_window_ms`）/ 屏幕全黑 / 功能未启用
- **与心跳区别**：感知有截图、用视觉模型、定时器在前端；心跳无截图、用主模型、定时器在后端、支持工具调用

## 心跳机制（OpenClaw HEARTBEAT）

**后端 asyncio 定时器**周期性调用 LLM，让 Agent 在用户沉默时有机会主动说话或调用工具。

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `heartbeat.enabled` | `false` | 总开关 |
| `heartbeat.intervalMinutes` | `30` | 心跳间隔（分钟） |
| `heartbeat.skipWindowMinutes` | `10` | 免打扰窗口：主分组内有活动则跳过 |
| `heartbeat.prompt` | `""` | 自定义心跳 prompt，空则使用默认 |
| `heartbeat.enableTools` | `true` | 心跳时是否允许 LLM 调用工具 |
| `heartbeat.maxToolRounds` | `20` | 最多工具调用轮数（上限 50） |

- **HEARTBEAT.md**：`lover/HEARTBEAT.md` 文件存在时，内容注入 system prompt `## 心跳任务 (HEARTBEAT)` 区块
- **安全工具白名单**：`get_character_card`、`update_character_card`、`update_user_profile`、`update_memory_notes`、`DDGsearch`、`searxng`、`time`、`get_weather`、`get_weather_by_city`
- **写入路径**：后端直接 `save_covs` + WebSocket `heartbeat_message` 广播；前端收到后追加到主会话 UI
- **与桌面感知区别**：见上方「桌面主动感知」章节

## 人格注入与 Token（设计说明）

**期望**：所有经 `/v1/chat/completions` 的对话（含 bot 行为推送、非流式 API）均走完整角色卡注入，以保持人格一致。

**常驻 `.md` / 配置块**（`USER.md`、`SOUL.md`、`MEMORY.md` 及 settings 中的 `userProfile` / `memoryNotes` / `soul` 等）单文件通常为几 KB 量级。按中文约 1.5–2 字符/token 粗算，三者合计多在 **约 1k–3k tokens** 以内（视实际字数而定），相对 `description`、世界书命中、`## 相关回忆` FTS 片段、mem0 召回仍属可控开销。空字段会跳过，不注入。

**动态部分**才更占 token：世界书按关键词命中追加、每轮 FTS top-N、mem0 JSON、工具/视觉等 system 追加。长期记忆「文件不大」的判断主要针对常驻层；若需对 bot 关闭 FTS/mem0，可后续按 `is_app_bot` 做可选裁剪（当前未做）。

## 消息元数据（`conversations.db` 内 `messages[]`）

消息对象随会话经 WebSocket `save_conversations` → `save_covs()` 整包 JSON 落库。`getSanitizedConversations` 用 `...rest` 保留未列入剥离名单的字段（含下文元数据）。

### 时间戳 `timestamp`

| 状态 | 说明 |
|------|------|
| **已有** | 开发会话归档摘要、桌面主动感知写入的消息带 `timestamp`（ms） |
| **缺失** | 普通 `sendMessage` 用户/assistant 流式消息**尚未**统一写入 |
| **会话级** | `conv.timestamp` 在发送结束、删消息等路径会更新，用于列表排序与免打扰窗口；`conversation_last_activity_ms` 会 `max(conv.timestamp, 各 msg.timestamp)` |

后续任务 **11.6**：所有消息路径补齐 `timestamp`，前端气泡展示时间。

### 消息来源区分：`messageKind`（字符串枚举，驼峰）

所有写入路径统一使用 `messageKind` 字段（不再使用旧布尔字段）：

| `messageKind` | 写入位置 | 含义 |
|---------------|----------|------|
| `chat`（默认，不写入） | 普通流式回复 | 普通对话 |
| `desktopAwareness` | 前端 `runDesktopAwarenessCheck` → 主会话 | 桌面感知主动关心 |
| `heartbeat` | 后端 `heartbeat_check` → 主会话 | 心跳机制主动消息 |
| `devSummary` | `POST /api/lover/archive-dev-session` → **主会话** | 开发会话归档摘要回流 |
| `archiveSummary` | 同上 API → **归档中的 dev 会话**末尾 | 该 dev 会话内的归档摘要块 |

`source_conv_id` 保留，仅 `devSummary` 主会话消息携带，表示来源 dev 会话 id。

前端通过 `MessageKind` 常量引用枚举值；`resolveMessageKind(msg)` 直接返回 `msg.messageKind || 'chat'`，不再回填旧布尔字段（旧数据按普通 assistant 渲染）。

## 兼容性

- 所有新字段默认空值，老角色卡完全兼容
- 不删除任何现有功能（角色卡 CRUD、TTS 联动、VRM 联动、mem0 等）
- 品牌保持 super-agent-party

## 相关文档

- 角色卡体系详情：`docs/CHARACTER_CARD.md`
- OpenSpec 设计与任务：`openspec/changes/lover-sap-foundation/`
