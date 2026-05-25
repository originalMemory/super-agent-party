## Context

项目当前有三套主动行为系统：

1. **通用自主行为**（`behaviorSettings`）：前端 `setInterval` 调度，触发后 `sendMessage()` 走主对话流。后端 `BehaviorEngine` 为 Bot 平台（微信/飞书等）提供调度。支持 time/noInput/cycle 三种触发、prompt/random 两种动作。
2. **心跳**（`heartbeat`）：后端 asyncio 定时器，独立调 LLM，带主会话 system prompt + 近 20 条对话 + HEARTBEAT.md 任务备忘 + 安全工具白名单。结果写入主会话 + WebSocket 广播。
3. **桌面感知**（`desktopAwareness`）：前端定时器触发 → 后端 API 截图 + 视觉模型判断。结果前端写入主会话。

三套系统各自维护独立的配置结构、定时器、上下文组装、输出路径和 UI 面板。

## Goals / Non-Goals

**Goals:**
- 将心跳和桌面感知收编为 `behaviorSettings.behaviorList` 中的预设行为项
- 所有行为共享统一的调度→触发→执行→输出链路
- 支持前端调度和后端调度两种模式（`runInBackground` 标记）
- 走正常 `sendMessage()` 聊天流程（完整 system prompt + 完整对话历史 + 全量工具）
- 提供简单的执行日志（触发时间、是否跳过、是否发言）
- 移除所有心跳/桌面感知专属后端代码和 API

**Non-Goals:**
- 不合并任务中心（`TaskCenter`）——那是工作区级重量任务系统，定位不同
- 不改造 Bot 平台（微信/飞书/钉钉/Discord）的行为调度——保持现有 `BehaviorEngine` 对 Bot 的调度能力
- 不新增行为类型（topic 等）——仅整合现有能力
- 不处理旧数据迁移——项目开发阶段，无真实旧数据

## Decisions

### D1: 统一数据模型——扩展 BehaviorItem

**决定**：在现有 `BehaviorItem` 上扩展，而非新建模型。

新增字段：
- `action.type` 新增枚举值 `"desktopAwareness"`（与现有 `"prompt"` / `"random"` 并列）
- `runInBackground: bool`（默认 `false`）——标记是否由后端调度
- `skipIfRecentlyActive: bool`（默认 `false`）——近期有对话则跳过本次触发
- `skipWindowMinutes: int`（默认 `30`）——`skipIfRecentlyActive` 的窗口大小
- `noActionDetection: bool`（默认 `false`）——LLM 回复包含 NO_ACTION 标记时不追加到对话
- `messageKind: string`（默认 `"chat"`）——触发消息的来源标记
- `presetId: string | null`（默认 `null`）——预设标识符，非空表示是内置预设（`"heartbeat"` / `"desktopAwareness"`）

**理由**：复用现有的前端 UI（卡片列表、编辑弹窗、触发类型选择）和后端调度逻辑，增量改造成本最低。

### D2: 双层调度——前端 + 后端

**决定**：`runInBackground=false` 的行为由前端 `setInterval` 调度（现有机制）；`runInBackground=true` 的行为由后端统一调度器调度。

**后端调度器**：重构 `py/behavior_engine.py`，在 `lifespan` 启动时为所有 `runInBackground=true` 的 chat 平台行为创建 asyncio 定时器。配置变更时，`save_settings` 回调中 diff 新旧 `behaviorSettings`（浅比较 JSON 序列化），仅当 `behaviorSettings` 实际发生变化时才重建定时器，避免无关配置变更（如改模型名）导致 cycle 计时被重置。

**后端执行路径**：后端调度触发时，向 `POST /v1/chat/completions` 发请求（类似现有心跳的独立 LLM 调用），带上完整主会话的 system prompt + 全部对话历史 + 全量工具。LLM 回复后写入主会话 + WebSocket `behavior_message` 广播到前端。

**前端执行路径**：前端调度触发时直接走 `runBehavior` → `sendMessage()`，与现有逻辑一致。

**理由**：桌面截图必须在前端完成（用户设备画面）；心跳等纯文本行为需要后端调度保证关掉浏览器也能执行。

### D3: 桌面感知——前端截图 + 特殊执行流程

**决定**：`action.type === "desktopAwareness"` 时，`runBehavior` 走特殊分支：

1. 先通过 Electron `powerMonitor.getSystemIdleState()` 检测系统状态——如果处于 `locked` 或 `idle` 超过阈值，直接跳过（不截图，零开销）
2. 通过 Electron `desktopCapturer.getSources()` 截取 Electron 所在设备的屏幕（确保截取的是用户正在使用的设备，而非后端服务器所在设备）
3. 组装带图片的 user 消息（`[system]:桌面感知检查` + 图片附件）
4. 调用 `sendMessage()` 走正常对话流程
5. 根据 `noActionDetection` 判断是否保留回复

**理由**：截图必须在前端 Electron 完成。使用 `powerMonitor` 做息屏/锁屏检测比截图后算平均亮度更准确、更省资源——锁屏时完全不截图，避免浪费。非 Electron 环境下桌面感知不可用（静默跳过）。

### D4: HEARTBEAT.md → action.prompt

**决定**：移除 HEARTBEAT.md 独立文件机制。心跳预设的 `action.prompt` 直接存储完整的心跳指令文本（包含原来 HEARTBEAT.md 中的任务备忘内容）。

**理由**：行为项已有 `action.prompt` 字段，无需额外文件。用户在 UI 编辑行为的 prompt 文本框即可修改心跳指令，体验统一。

### D5: 预设行为管理

**决定**：`behaviorSettings` 新增 `presets` 配置（仅 `settings_template.json` 中定义默认值），首次加载时将预设插入 `behaviorList`。预设项通过 `presetId` 标识，用户可修改或删除。

内置预设：
- **心跳**：`presetId: "heartbeat"`, `trigger.type: "cycle"`, `trigger.cycle.cycleValue: "00:30:00"`, `runInBackground: true`, `skipIfRecentlyActive: true`, `noActionDetection: true`, `messageKind: "heartbeat"`, `enabled: false`
- **桌面感知**：`presetId: "desktopAwareness"`, `trigger.type: "cycle"`, `trigger.cycle.cycleValue: "01:00:00"`, `runInBackground: false`, `skipIfRecentlyActive: true`, `noActionDetection: true`, `messageKind: "desktopAwareness"`, `action.type: "desktopAwareness"`, `enabled: false`

**理由**：开箱即用但默认关闭，用户可以看到这些预设并决定是否启用，也可以修改参数。

### D6: 执行日志

**决定**：`behaviorSettings` 新增 `behaviorLog: Array`（内存中维护，不持久化），记录最近 N 条（如 50）执行记录。每条记录包含：`timestamp`、行为名称、触发类型、是否跳过（含原因）、是否发言。前端 UI 在自主行为配置页新增"执行日志"展开区域。

**理由**：调试用，不需要持久化。内存中维护最近记录即可。

### D7: WebSocket 广播消息类型统一

**决定**：移除 `heartbeat_message` 类型，新增通用的 `behavior_message` 类型。后端调度的行为执行完毕后通过 `behavior_message` 广播，前端 `_handleBehaviorMessage` 统一处理（追加到主会话 + 按 `messageKind` 渲染）。

**理由**：所有后端触发的行为共享同一广播通道，不再按类型区分。

### D9: 对话历史中只保留一条 assistant 消息

**问题**：当前 `runBehavior` 通过 `sendMessage()` 发送 `[system]:prompt`，这条触发消息会作为 user 消息持久化到对话历史中。心跳每 30 分钟触发一次，一天下来会在历史里积累大量 `[system]:` 消息，污染上下文。同时 LLM 的回复消息没有 `messageKind` 标记，无法在 UI 中区分来源。

**原则**：自主行为的执行结果在对话历史中只体现为一条 assistant 消息（带 `messageKind`）。所有中间消息（trigger prompt、系统注入）不留痕迹。

**决定**：

1. **前端路径**：`runBehavior` 在调用 `sendMessage()` 前设置 `this._behaviorTriggerMeta = { messageKind: "heartbeat" }`。
   - `sendMessage` 内部检查该标记，给 push 到 `this.messages` 的 user 消息添加 `_behaviorTrigger: true`
   - `sendMessage` 的 `finally` 块中，在 `saveConversations()` 之前，移除所有 `_behaviorTrigger: true` 的消息
   - `generateAIResponse` 组装 assistant 回复消息时，检查 `_behaviorTriggerMeta`，写入 `messageKind`
   - 若启用 `noActionDetection` 且 LLM 回复命中 NO_ACTION，同时移除 assistant 回复——最终对话历史中无任何新增消息

2. **后端路径**：后端行为执行时直接控制消息组装，trigger prompt 仅存在于本次 LLM 调用的临时消息列表中，不写入主会话的持久化 messages。只有 LLM 的有效回复（带 `messageKind`）写入并广播。

**理由**：用户在对话列表中只应看到 AI 角色的主动发言，不应看到系统内部的触发指令。

### D8: 移除清单

移除的后端代码：
- `server.py`：`_heartbeat_periodic_loop`、`_heartbeat_task`、`_heartbeat_in_flight`、`_build_heartbeat_prompt`、`_collect_heartbeat_tools`、`_execute_heartbeat_tool_calls`、`_heartbeat_write_and_broadcast`、`_run_heartbeat_check`、`/api/lover/heartbeat-check` endpoint、`/api/lover/desktop-awareness-check` endpoint
- `py/lover_system_context.py`：`heartbeat_skip_window_ms`、`read_heartbeat_md` 等心跳专属辅助函数
- `config/settings_template.json`：顶层 `heartbeat` 和 `desktopAwareness` 配置块

移除的前端代码：
- `vue_methods.js`：`runHeartbeatCheck`、`_handleHeartbeatMessage`、`startDesktopAwarenessTimer`、`stopDesktopAwarenessTimer`、`runDesktopAwarenessCheck`
- `vue_data.js`：`heartbeat`、`desktopAwareness` 顶层数据
- `index.html`：心跳配置面板、桌面感知配置面板
- WebSocket `heartbeat_message` 处理分支

## Risks / Trade-offs

- **[后端调度行为的上下文组装]** → 后端触发时需要重新组装完整主会话上下文（system prompt + 全部历史），这比前端直接 `sendMessage()` 复杂。 → 复用 `build_lover_system_messages` + 全量 `messages` 读取，与现有心跳实现类似但不再裁剪到 20 条
- **[后端调度行为的工具调用]** → 后端独立 LLM 调用需要支持工具调用循环。 → 复用 `dispatch_tool` 等现有基础设施，不再限制白名单
- **[桌面截图平台兼容性]** → 桌面感知依赖 Electron API（`powerMonitor` + `desktopCapturer`），非 Electron 环境下该行为类型不可用。 → 非 Electron 环境静默跳过，不报错
- **[执行日志内存占用]** → 保留最近 50 条记录，单条数据量极小，风险可忽略
