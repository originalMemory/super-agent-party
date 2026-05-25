## Context

项目当前有三套主动行为系统：

1. **通用自主行为**（`behaviorSettings`）：前端 `setInterval` 调度，触发后 `sendMessage()` 走主对话流。后端 `BehaviorEngine`（`py/behavior_engine.py`）为 Bot 平台（微信/飞书等）提供调度。支持 time/noInput/cycle 三种触发、prompt/random 两种动作。
2. **心跳**（`heartbeat`）：后端 `_heartbeat_periodic_loop` (asyncio) 定时器，独立调 LLM，带主会话 system prompt + 近 20 条对话 + `HEARTBEAT.md` 任务备忘 + 安全工具白名单。结果写入主会话 + WebSocket `heartbeat_message` 广播。
3. **桌面感知**（`desktopAwareness`）：前端定时器触发 → 后端 `/api/lover/desktop-awareness-check` API 截图 + 视觉模型判断。结果前端写入主会话。**当前实现的截图是后端服务器画面，并非用户实际桌面**，这是顺带要修复的正确性问题。

三套系统各自维护独立的配置结构、定时器、上下文组装、输出路径和 UI 面板。本 change 把它们合并到一个引擎，但**不动 `sendMessage` 的存盘逻辑**——触发后留下来的 `[system]:xxx` user 消息暂时容忍，由后续 change `behavior-trigger-isolation` 处理。

## Goals / Non-Goals

**Goals:**
- 将心跳和桌面感知收编为 `behaviorSettings.behaviorList` 中的预设行为项（`presetId` 标识）
- 所有行为共享统一的调度→触发→执行→输出链路
- 支持前端调度（`runInBackground=false`）和后端调度（`runInBackground=true`）两种模式
- 走正常 `sendMessage()` 聊天流程（完整 system prompt + 完整对话历史 + 全量工具）
- 行为级 `skipIfRecentlyActive` / `noActionDetection` 配置
- WebSocket 广播消息类型统一为 `behavior_message`
- 移除所有心跳/桌面感知专属后端代码和 API
- 修正桌面感知截到错误设备的问题（改前端 Electron 截图）

**Non-Goals:**
- **不处理触发消息持久化（D9）**——`runBehavior` 通过 `sendMessage()` 触发的 `[system]:prompt` user 消息仍然会进入对话历史，由后续 change 处理
- **不实现执行日志**——由后续 change 一并处理
- **不修改 FTS 检索逻辑**——FTS 仍按现有规则注入；由后续 change 改造为 `behavior_trigger` 通用标记
- 不合并任务中心（`TaskCenter`）——那是工作区级重量任务系统
- 不改造 Bot 平台（微信/飞书/钉钉/Discord）行为调度——保持现有 `BehaviorEngine` 对 Bot 的能力
- 不新增 prompt/random/desktopAwareness 之外的行为类型
- 不处理旧数据迁移——项目开发阶段，无真实旧数据

## Decisions

### D1: 统一数据模型——扩展 BehaviorItem

**决定**：在现有 `BehaviorItem` 上扩展，而非新建模型。

新增字段：
- `action.type` 新增枚举值 `"desktopAwareness"`（与现有 `"prompt"` / `"random"` 并列）
- `runInBackground: bool`（默认 `false`）——标记是否由后端调度
- `skipIfRecentlyActive: bool`（默认 `false`）——近期有对话则跳过本次触发
- `skipWindowMinutes: int`（默认 `30`）——`skipIfRecentlyActive` 的窗口大小
- `noActionDetection: bool`（默认 `false`）——LLM 回复含 NO_ACTION 时不追加 assistant 消息
- `messageKind: string`（默认 `"chat"`）——触发消息的来源标记
- `presetId: string | null`（默认 `null`）——预设标识符，非空表示是内置预设（`"heartbeat"` / `"desktopAwareness"`）

**理由**：复用现有的前端 UI（卡片列表、编辑弹窗、触发类型选择）和后端调度逻辑，增量改造成本最低。

**Alternatives considered**：单独建 `PresetBehavior` 模型——会带来"两套行为类型分别渲染"的负担，违背"统一引擎"的初衷。

### D2: 双层调度——前端 + 后端

**决定**：`runInBackground=false` 的行为由前端 `setInterval` 调度（现有机制）；`runInBackground=true` 的行为由后端统一调度器调度。

**后端调度器**：新增 `BackgroundBehaviorScheduler` 类（放在 `py/behavior_engine.py`），在 `lifespan` 启动时为所有 `runInBackground=true` 且 `platforms` 包含 `"chat"` 的行为创建 asyncio 定时器。配置变更时，`save_settings` 回调中 diff 新旧 `behaviorSettings`（JSON 序列化比较），仅当 `behaviorSettings` 实际发生变化时才重建定时器，避免无关配置变更（如改模型名）导致 cycle 计时被重置。

**后端执行路径**：后端调度触发时，独立调用 LLM（类似现有心跳的实现），带上完整主会话的 system prompt + 全部对话历史 + 全量工具。LLM 回复后写入主会话 + WebSocket `behavior_message` 广播到前端。

**前端执行路径**：前端调度触发时直接走 `runBehavior` → `sendMessage()`，与现有逻辑一致。

**理由**：桌面截图必须在前端完成（用户设备画面）；心跳等纯文本行为需要后端调度保证关掉浏览器也能执行。

**Alternatives considered**：纯前端调度——浏览器关闭后心跳失效，违背心跳"后台兜底"语义；纯后端调度——后端无法获取用户桌面截图。

### D3: 桌面感知——前端截图 + 特殊执行流程

**决定**：`action.type === "desktopAwareness"` 时，`runBehavior` 走特殊分支：

1. 先通过 Electron `powerMonitor.getSystemIdleState()` 检测系统状态——如果处于 `locked` 或 `idle` 超过阈值，直接跳过（不截图，零开销）
2. 通过 Electron `desktopCapturer.getSources()` 截取 Electron 所在设备的屏幕（确保截取的是用户正在使用的设备，而非后端服务器所在设备）
3. 组装带图片的 user 消息（`[system]:桌面感知检查` + 图片附件）
4. 调用 `sendMessage()` 走正常对话流程
5. 根据 `noActionDetection` 判断是否保留回复

**理由**：截图必须在前端 Electron 完成。使用 `powerMonitor` 做息屏/锁屏检测比截图后算平均亮度更准确、更省资源——锁屏时完全不截图，避免浪费。非 Electron 环境下桌面感知不可用（静默跳过）。

**Alternatives considered**：保留后端截图——会继续截到服务器画面，是已知 bug；前端截图 + 后端视觉模型调用——增加额外 API 跳转，不如直接走 `sendMessage()` 复用全套基础设施。

### D4: HEARTBEAT.md → action.prompt

**决定**：移除 `HEARTBEAT.md` 独立文件机制。心跳预设的 `action.prompt` 直接存储完整的心跳指令文本（包含原来 `HEARTBEAT.md` 中的任务备忘内容）。

**理由**：行为项已有 `action.prompt` 字段，无需额外文件。用户在 UI 编辑行为的 prompt 文本框即可修改心跳指令，体验统一。

### D5: 预设行为管理

**决定**：`settings_template.json` 的 `behaviorSettings.behaviorList` 中预置两个预设行为项。预设项通过 `presetId` 标识，用户可修改或删除。

内置预设：
- **心跳**：`presetId: "heartbeat"`, `trigger.type: "cycle"`, `trigger.cycle.cycleValue: "00:30:00"`, `runInBackground: true`, `skipIfRecentlyActive: true`, `noActionDetection: true`, `messageKind: "heartbeat"`, `enabled: false`, `action.type: "prompt"`, `action.prompt`: 心跳完整指令文本
- **桌面感知**：`presetId: "desktopAwareness"`, `trigger.type: "cycle"`, `trigger.cycle.cycleValue: "01:00:00"`, `runInBackground: false`, `skipIfRecentlyActive: true`, `noActionDetection: true`, `messageKind: "desktopAwareness"`, `action.type: "desktopAwareness"`, `enabled: false`

**理由**：开箱即用但默认关闭，用户可以看到这些预设并决定是否启用，也可以修改参数。

### D6: WebSocket 广播消息类型统一

**决定**：移除 `heartbeat_message` 类型，新增通用的 `behavior_message` 类型。后端调度的行为执行完毕后通过 `behavior_message` 广播，前端 `_handleBehaviorMessage` 统一处理（追加到主会话 + 按 `messageKind` 渲染）。

**理由**：所有后端触发的行为共享同一广播通道，不再按类型区分。

### D7: 不引入触发消息隔离机制

**决定**：本 change 不处理触发消息持久化问题。`runBehavior` 调用 `sendMessage()` 后，`[system]:prompt` 仍会作为 user 消息保留在对话历史中。

**理由**：D9（trigger 消息不持久化）会动到 `sendMessage` / `generateAIResponse` 这条**所有普通对话也走的主流程**，是一处高危改动。把它隔离到独立 change 便于单独 review 和回归。短期内对话历史里多一条 `[system]:xxx` 不影响功能可用性，只是观感问题。

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

- **[后端调度行为的上下文组装]** → 后端触发时需要重新组装完整主会话上下文（system prompt + 全部历史），这比前端直接 `sendMessage()` 复杂 → 复用 `build_lover_system_messages` + 全量 `messages` 读取，与现有心跳实现类似但不再裁剪到 20 条
- **[后端调度行为的工具调用]** → 后端独立 LLM 调用需要支持工具调用循环 → 复用 `dispatch_tool` 等现有基础设施，不再限制白名单
- **[桌面截图平台兼容性]** → 桌面感知依赖 Electron API（`powerMonitor` + `desktopCapturer`），非 Electron 环境下该行为类型不可用 → 非 Electron 环境静默跳过，不报错；预设默认 `enabled: false` 也避免在浏览器中无意触发
- **[桌面感知失去后端调度兜底]** → 浏览器/Electron 关闭后桌面感知不工作 → 业务上桌面感知只在用户在线时才有意义，可接受
- **[对话历史污染]** → 触发后会留下 `[system]:xxx` user 消息 → 由后续 change `behavior-trigger-isolation` 处理；本 change 期内可容忍
- **[心跳重写有功能回归风险]** → 用通用引擎替换跑稳的 `_run_heartbeat_check` → 上线后人工验证心跳触发 → LLM 调用 → 工具循环 → 写主会话 → WS 广播的完整链路；保留行为日志用于排查
- **[后端调度器与现有 BehaviorEngine 共存]** → 现有 `BehaviorEngine` 为 Bot 平台服务（不动）；新 `BackgroundBehaviorScheduler` 服务 chat 平台。两者使用相同 `BehaviorItem` 模型 → 在 `behavior_engine.py` 内通过职责区分，避免重复调度同一行为
