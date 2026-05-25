## Why

项目当前存在三套独立的「主动行为」系统——通用自主行为（`behaviorSettings`）、心跳（`heartbeat`）、桌面感知（`desktopAwareness`）。它们功能高度重叠但各自维护独立的配置结构、定时器、上下文组装、输出路径和 UI 面板，新增主动行为类型需要从零搭建完整链路。本次变更将三者合并到统一的自主行为引擎中：心跳和桌面感知不再是独立子系统，而是 `behaviorSettings.behaviorList` 中的预设行为项，与用户自定义行为共享调度、执行和输出链路。

本 change 聚焦「功能合并」本身——把三套机械替换为一套，但**不动 `sendMessage` / `generateAIResponse` 这条主对话流程**。触发后留下来的 `[system]:xxx` user 消息暂时容忍存在；该问题以及 FTS 注入的隔离改由后续 change `behavior-trigger-isolation` 处理。

## What Changes

- **新增统一引擎能力 `unified-behavior-engine`**：行为项数据模型扩展 `runInBackground` / `skipIfRecentlyActive` / `skipWindowMinutes` / `noActionDetection` / `messageKind` / `presetId` 字段；`action.type` 枚举新增 `"desktopAwareness"`
- **新增双层调度**：前端 `setInterval` 调度 `runInBackground=false` 行为；后端 `BackgroundBehaviorScheduler` (asyncio) 调度 `runInBackground=true` 行为。配置变更时仅当 `behaviorSettings` 实际变化才重建定时器
- **新增预设行为**：`settings_template.json` 内置心跳（`presetId: "heartbeat"`，后端调度）和桌面感知（`presetId: "desktopAwareness"`，前端调度 + Electron 截图）两个默认禁用预设
- **新增桌面感知前端执行路径**：Electron `powerMonitor.getSystemIdleState()` 检测锁屏/idle → `desktopCapturer.getSources()` 截图 → 组装带图片的消息走 `sendMessage()`。非 Electron 环境静默跳过
- **统一前端执行路径为 `sendMessage()`**：所有前端调度行为通过现有 `runBehavior → sendMessage()`，完整携带主会话 system prompt + 完整对话历史 + 全量工具
- **后端调度行为独立 LLM 调用**：组装完整主会话上下文（复用 `build_lover_system_messages` + 全部历史），支持工具调用循环（复用 `dispatch_tool`，不限制白名单），结果通过新 WebSocket `behavior_message` 广播
- **新增 `messageKind` 标记**：assistant 回复写入 `messageKind`（`heartbeat` / `desktopAwareness` / `chat`），UI 据此区分渲染
- **新增 `skipIfRecentlyActive` 行为级跳过**：原心跳/桌面感知的"近期有活动就跳过"逻辑迁移为行为级配置
- **新增 `noActionDetection` 配置**：LLM 回复包含 NO_ACTION 标记时不追加 assistant 回复
- **移除旧心跳子系统**：`server.py` 的 `_heartbeat_periodic_loop` / `_run_heartbeat_check` / `_build_heartbeat_prompt` / `_collect_heartbeat_tools` / `_execute_heartbeat_tool_calls` / `_heartbeat_write_and_broadcast` / `/api/lover/heartbeat-check` endpoint；`lover_system_context.py` 的 `heartbeat_skip_window_ms` / `read_heartbeat_md`；前端 `runHeartbeatCheck` / `_handleHeartbeatMessage`；WebSocket `heartbeat_message` 处理分支；`settings_template.json` 顶层 `heartbeat`；HEARTBEAT.md 独立文件（内容并入 `action.prompt`）；心跳 UI 配置面板
- **移除旧桌面感知子系统**：`/api/lover/desktop-awareness-check` endpoint；前端 `startDesktopAwarenessTimer` / `stopDesktopAwarenessTimer` / `runDesktopAwarenessCheck`；`settings_template.json` 顶层 `desktopAwareness`；桌面感知 UI 配置面板
- **UI 改造**：行为编辑弹窗新增 `runInBackground` / `skipIfRecentlyActive`（含 `skipWindowMinutes`） / `noActionDetection` / `messageKind` 配置项；`action.type` 下拉新增 `"desktopAwareness"` 选项；行为卡片摘要（`getBehaviorSummary`）适配新字段
- **不做**：trigger 消息持久化隔离（D9）、执行日志、FTS `behavior_trigger` 标记——这三项交由后续 change

## Capabilities

### New Capabilities
- `unified-behavior-engine`：统一自主行为引擎——数据模型、双层调度（前端 + 后端）、桌面感知前端执行、后端独立调用、WebSocket 广播、预设管理、移除旧心跳/桌面感知子系统的完整链路

### Modified Capabilities
（本 change 不修改任何已有 capability 的 requirements）

## Impact

- **后端**：`server.py`（移除心跳定时器/endpoint/广播，新增统一后端行为调度器及其 LLM 调用路径）、`py/behavior_engine.py`（新增 `BackgroundBehaviorScheduler`，扩展 `BehaviorItem` 模型字段）、`py/lover_system_context.py`（移除心跳辅助函数）
- **前端**：`static/js/renderer.js`（前端定时器仅调度 `runInBackground=false`）、`static/js/vue_methods.js`（统一 `runBehavior`，新增桌面感知分支与 `behavior_message` WebSocket 接收处理，移除 `runHeartbeatCheck` / `runDesktopAwarenessCheck` / `_handleHeartbeatMessage`）、`static/js/vue_data.js`（合并 `heartbeat` / `desktopAwareness` 配置到 `behaviorSettings`）
- **UI**：`static/index.html`（移除心跳/桌面感知独立配置面板，统一到自主行为页面；行为编辑弹窗扩展新字段）
- **配置**：`config/settings_template.json`（移除顶层 `heartbeat` / `desktopAwareness`，扩展 `behaviorSettings.behaviorList` 预设）
- **i18n**：`static/js/locales/*.js`（新增/调整翻译键）
- **文档**：`docs/LOVER_SSOT.md`（同步架构说明）
- **依赖关系**：本 change 完成后，对话历史中行为触发会留下 `[system]:xxx` user 消息（暂时容忍），由后续 change `behavior-trigger-isolation` 处理
- **无需向后兼容**：项目处于开发阶段，无真实旧数据，直接替换配置结构
