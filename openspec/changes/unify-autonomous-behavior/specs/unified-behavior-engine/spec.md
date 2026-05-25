## ADDED Requirements

### Requirement: Unified behavior data model
系统 SHALL 使用统一的 `BehaviorItem` 数据模型来表达所有自主行为（包括用户自定义行为、心跳、桌面感知）。每个 `BehaviorItem` SHALL 包含以下字段：
- `enabled: bool`
- `trigger: { type, time?, noInput?, cycle? }`（复用现有触发类型）
- `action: { type, prompt?, random? }`（`type` 枚举扩展为 `"prompt"` / `"random"` / `"desktopAwareness"`）
- `platforms: string[]`（目标平台列表）
- `runInBackground: bool`（默认 `false`）
- `skipIfRecentlyActive: bool`（默认 `false`）
- `skipWindowMinutes: int`（默认 `30`）
- `noActionDetection: bool`（默认 `false`）
- `messageKind: string`（默认 `"chat"`）
- `presetId: string | null`（默认 `null`）

#### Scenario: Standard prompt behavior
- **WHEN** 用户创建一个 `action.type = "prompt"` 的行为项
- **THEN** 数据模型与现有自主行为完全兼容，触发后使用 `action.prompt` 作为发送内容

#### Scenario: Desktop awareness behavior
- **WHEN** 用户创建或启用 `action.type = "desktopAwareness"` 的行为项
- **THEN** 数据模型包含 `desktopAwareness` 动作类型，触发时走截图+视觉模型判断流程

#### Scenario: Heartbeat preset
- **WHEN** 系统加载心跳预设行为项（`presetId = "heartbeat"`）
- **THEN** 该项使用 `action.type = "prompt"` + `runInBackground = true` + `messageKind = "heartbeat"`，prompt 内容包含心跳检查指令

### Requirement: Preset behavior initialization
系统 SHALL 在 `settings_template.json` 中的 `behaviorSettings.behaviorList` 包含两个默认禁用的预设行为项：心跳（`presetId: "heartbeat"`）和桌面感知（`presetId: "desktopAwareness"`）。

#### Scenario: Fresh installation
- **WHEN** 用户首次启动系统（使用 `settings_template.json` 初始化）
- **THEN** `behaviorSettings.behaviorList` 包含两个 `enabled: false` 的预设行为项，用户可在 UI 中看到并启用

#### Scenario: User modifies preset
- **WHEN** 用户修改预设行为项的参数（如修改心跳间隔）
- **THEN** 修改被正常保存，`presetId` 保持不变

#### Scenario: User deletes preset
- **WHEN** 用户删除预设行为项
- **THEN** 预设被正常删除，不会自动重新创建

### Requirement: Frontend scheduling for foreground behaviors
系统 SHALL 通过前端定时器（`setInterval`）调度所有 `runInBackground = false` 的 chat 平台行为项。调度逻辑 SHALL 支持 time、noInput、cycle 三种触发类型。

#### Scenario: Time trigger fires
- **WHEN** 当前时间匹配行为项的 `trigger.time.timeValue`，且星期匹配（或未配置星期限制）
- **THEN** 前端执行该行为

#### Scenario: NoInput trigger fires
- **WHEN** 用户闲置时间超过 `trigger.noInput.latency` 秒，且 `noInputFlag` 为 true
- **THEN** 前端执行该行为

#### Scenario: Cycle trigger fires
- **WHEN** 距上次触发已过 `trigger.cycle.cycleValue` 指定的时间间隔
- **THEN** 前端执行该行为

#### Scenario: Background behavior skipped by frontend
- **WHEN** 行为项 `runInBackground = true`
- **THEN** 前端定时器 SHALL NOT 调度该行为

### Requirement: Backend scheduling for background behaviors
系统 SHALL 通过后端 asyncio 定时器调度所有 `runInBackground = true` 且 `platforms` 包含 `"chat"` 的行为项。调度逻辑 SHALL 支持 time、noInput、cycle 三种触发类型，与前端逻辑一致。

#### Scenario: Backend cycle trigger
- **WHEN** 服务运行中，某个 `runInBackground = true` 的 cycle 行为到达触发时间
- **THEN** 后端调度器触发该行为，即使没有浏览器客户端连接

#### Scenario: Settings change rebuilds timers only when behaviorSettings changed
- **WHEN** 用户通过 WebSocket `save_settings` 更新配置，且 `behaviorSettings` 与上一次保存的值不同
- **THEN** 后端调度器重建所有 `runInBackground = true` 行为的定时器

#### Scenario: Unrelated settings change does not rebuild timers
- **WHEN** 用户通过 WebSocket `save_settings` 更新配置，但 `behaviorSettings` 未发生变化（如仅修改了模型名）
- **THEN** 后端调度器 SHALL NOT 重建定时器，现有 cycle 计时不受影响

#### Scenario: Foreground behavior skipped by backend
- **WHEN** 行为项 `runInBackground = false`
- **THEN** 后端调度器 SHALL NOT 调度该行为

### Requirement: Frontend execution via sendMessage
所有由前端调度触发的行为 SHALL 通过 `sendMessage()` 执行，完整携带主会话的系统提示词、完整对话历史和全量工具。

#### Scenario: Prompt behavior execution
- **WHEN** 前端触发一个 `action.type = "prompt"` 的行为
- **THEN** `userInput` 设为 `"[system]:" + action.prompt`，调用 `sendMessage()`，走正常聊天流程

#### Scenario: Desktop awareness behavior execution
- **WHEN** 前端触发一个 `action.type = "desktopAwareness"` 的行为，且运行在 Electron 环境中
- **THEN** 前端先通过 `powerMonitor.getSystemIdleState()` 检测系统状态（锁屏/idle 超阈值则跳过），再通过 `desktopCapturer.getSources()` 截取 Electron 所在设备的屏幕，将截图作为图片附件与感知提示词一起通过 `sendMessage()` 发送

#### Scenario: Desktop awareness in non-Electron environment
- **WHEN** 前端触发一个 `action.type = "desktopAwareness"` 的行为，但不在 Electron 环境中
- **THEN** 静默跳过，记录跳过日志，不报错

#### Scenario: Random behavior execution
- **WHEN** 前端触发一个 `action.type = "random"` 的行为
- **THEN** 从 `action.random.events` 中选取一条（随机或顺序），设为 `userInput` 调用 `sendMessage()`

### Requirement: Backend execution with full context
后端调度触发的行为 SHALL 独立调用 LLM，组装完整的主会话上下文（系统提示词 + 全部对话历史 + 全量工具），执行完成后将结果写入主会话并通过 WebSocket 广播到前端。

#### Scenario: Backend behavior generates reply
- **WHEN** 后端调度触发一个 `runInBackground = true` 的行为，LLM 返回有效回复
- **THEN** 回复以 `{ role: "assistant", messageKind: <行为的messageKind> }` 写入主会话的 messages，通过 WebSocket `behavior_message` 广播到所有连接的前端客户端

#### Scenario: Backend behavior with tool calls
- **WHEN** 后端触发的行为执行中 LLM 返回 tool_calls
- **THEN** 系统 SHALL 执行工具调用循环（不限制工具白名单），直到 LLM 返回纯文本回复

#### Scenario: Frontend receives behavior_message
- **WHEN** 前端收到 WebSocket `behavior_message` 事件
- **THEN** 前端将消息追加到主会话的 messages 列表中（去重判断，避免重复插入）

### Requirement: Skip if recently active
当行为项 `skipIfRecentlyActive = true` 时，系统 SHALL 在触发前检查主分组是否有近期对话活动。若 `skipWindowMinutes` 分钟内有活动，则跳过本次触发。

#### Scenario: Recent activity within window
- **WHEN** 行为触发时，主分组内任一会话在 `skipWindowMinutes` 分钟内有过用户消息
- **THEN** 跳过本次触发，记录跳过日志

#### Scenario: No recent activity
- **WHEN** 行为触发时，主分组内所有会话超过 `skipWindowMinutes` 分钟无活动
- **THEN** 正常执行该行为

#### Scenario: skipIfRecentlyActive disabled
- **WHEN** 行为项 `skipIfRecentlyActive = false`
- **THEN** 不检查近期活动，直接执行

### Requirement: No-action detection
当行为项 `noActionDetection = true` 时，系统 SHALL 检查 LLM 回复是否包含 NO_ACTION 标记。若检测到，则不将回复追加到对话流中。

#### Scenario: LLM replies with NO_ACTION
- **WHEN** LLM 回复内容匹配 NO_ACTION 模式（如 `[NO_ACTION]` 或 `无需行动`）
- **THEN** 不将回复追加到主会话，记录"无需行动"日志

#### Scenario: LLM replies with normal content
- **WHEN** LLM 回复不含 NO_ACTION 标记
- **THEN** 正常追加回复到主会话

#### Scenario: noActionDetection disabled
- **WHEN** 行为项 `noActionDetection = false`
- **THEN** 不检查 NO_ACTION，所有回复均追加到对话

### Requirement: Behavior only produces one assistant message in history
自主行为的执行结果在对话历史中 SHALL 仅体现为**一条 assistant 消息**（带 `messageKind` 标记）。触发 prompt、过程中的 system 注入等中间消息 SHALL NOT 出现在持久化的对话历史中。

#### Scenario: Frontend behavior completes successfully
- **WHEN** 前端 `runBehavior` 通过 `sendMessage()` 触发行为，LLM 回复完成
- **THEN** 持久化的对话历史中仅新增一条 `{ role: "assistant", messageKind: <配置值> }` 消息；触发用的 `[system]:prompt` user 消息在 `saveConversations()` 之前从 `this.messages` 中移除

#### Scenario: Backend behavior completes successfully
- **WHEN** 后端调度触发行为，LLM 返回有效回复
- **THEN** 仅将 `{ role: "assistant", messageKind: <配置值> }` 写入主会话的持久化 messages；trigger prompt 仅存在于本次 API 调用的临时消息列表中

#### Scenario: LLM still receives trigger message for context
- **WHEN** 行为触发时 LLM 被调用
- **THEN** LLM 的 messages 入参中包含 trigger prompt（作为 user 消息），确保模型知道触发意图；该消息仅用于本次调用，不持久化

#### Scenario: NO_ACTION results in zero messages
- **WHEN** 行为启用了 `noActionDetection` 且 LLM 回复包含 NO_ACTION 标记
- **THEN** 对话历史中不新增任何消息（trigger 消息移除 + assistant 回复也移除）

### Requirement: MessageKind tagging
行为触发的 **assistant 回复消息** SHALL 携带 `messageKind` 字段（取自行为项配置），用于前端 UI 区分消息来源和渲染样式。

#### Scenario: Heartbeat message rendering
- **WHEN** 一条 `messageKind = "heartbeat"` 的消息在对话中展示
- **THEN** UI SHALL 以心跳消息样式渲染（与现有心跳消息渲染一致）

#### Scenario: Desktop awareness message rendering
- **WHEN** 一条 `messageKind = "desktopAwareness"` 的消息在对话中展示
- **THEN** UI SHALL 以桌面感知消息样式渲染（与现有桌面感知消息渲染一致）

#### Scenario: Default chat message
- **WHEN** 行为项 `messageKind = "chat"`
- **THEN** 触发的消息以普通对话消息样式渲染，无特殊标记

### Requirement: Execution log
系统 SHALL 在内存中维护最近 50 条行为执行日志。每条日志包含：触发时间戳、行为名称/presetId、触发类型、执行结果（`executed` / `skipped_recent_active` / `skipped_screen_off` / `skipped_no_action` / `error`）。

#### Scenario: Behavior executed successfully
- **WHEN** 一个行为被触发并成功执行（LLM 返回有效回复）
- **THEN** 日志记录 `executed`

#### Scenario: Behavior skipped
- **WHEN** 一个行为因近期活动/息屏/NO_ACTION 被跳过
- **THEN** 日志记录对应的跳过原因

#### Scenario: Log viewable in UI
- **WHEN** 用户在自主行为配置页点击"执行日志"
- **THEN** 展示最近的执行记录列表

### Requirement: Remove legacy heartbeat system
系统 SHALL 移除所有独立的心跳子系统代码，包括：后端 `_heartbeat_periodic_loop` 定时器、`_run_heartbeat_check` 函数、`_collect_heartbeat_tools` 函数、`_execute_heartbeat_tool_calls` 函数、`_heartbeat_write_and_broadcast` 函数、`/api/lover/heartbeat-check` API endpoint、HEARTBEAT.md 文件读取逻辑、`heartbeat_skip_window_ms` 辅助函数、`read_heartbeat_md` 辅助函数、前端 `runHeartbeatCheck` 方法、前端 `_handleHeartbeatMessage` 方法、WebSocket `heartbeat_message` 处理分支、`settings_template.json` 顶层 `heartbeat` 配置块、前端心跳配置 UI 面板。

#### Scenario: Heartbeat endpoint removed
- **WHEN** 客户端请求 `POST /api/lover/heartbeat-check`
- **THEN** 服务器返回 404

#### Scenario: Heartbeat config key removed
- **WHEN** 系统加载 settings
- **THEN** 顶层不存在 `heartbeat` 配置键（心跳配置已迁移到 `behaviorSettings.behaviorList` 中的预设项）

### Requirement: Remove legacy desktop awareness system
系统 SHALL 移除所有独立的桌面感知子系统代码，包括：`/api/lover/desktop-awareness-check` API endpoint、前端 `startDesktopAwarenessTimer` / `stopDesktopAwarenessTimer` / `runDesktopAwarenessCheck` 方法、`settings_template.json` 顶层 `desktopAwareness` 配置块、前端桌面感知配置 UI 面板。截图和息屏检测的核心工具函数 SHALL 保留，供统一行为引擎复用。

#### Scenario: Desktop awareness endpoint removed
- **WHEN** 客户端请求 `POST /api/lover/desktop-awareness-check`
- **THEN** 服务器返回 404

#### Scenario: Desktop awareness config key removed
- **WHEN** 系统加载 settings
- **THEN** 顶层不存在 `desktopAwareness` 配置键

#### Scenario: Screenshot utility preserved
- **WHEN** 统一行为引擎触发桌面感知行为
- **THEN** 可复用现有的截图和息屏检测工具函数

### Requirement: Unified behavior UI
自主行为配置 UI SHALL 作为心跳和桌面感知的唯一配置入口。原有的独立心跳配置面板和桌面感知配置面板 SHALL 被移除。

#### Scenario: Heartbeat configured via behavior UI
- **WHEN** 用户想配置心跳
- **THEN** 在自主行为页面找到心跳预设行为项，编辑其参数（间隔、prompt、是否启用等）

#### Scenario: Desktop awareness configured via behavior UI
- **WHEN** 用户想配置桌面感知
- **THEN** 在自主行为页面找到桌面感知预设行为项，编辑其参数（间隔、是否启用等）

#### Scenario: Behavior edit dialog supports new fields
- **WHEN** 用户编辑任意行为项
- **THEN** 编辑弹窗包含 `runInBackground`、`skipIfRecentlyActive`、`skipWindowMinutes`、`noActionDetection`、`messageKind` 等新增配置选项
