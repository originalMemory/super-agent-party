## Why

项目中存在三套独立的「主动行为」系统——通用自主行为（`behaviorSettings`）、心跳（`heartbeat`）、桌面感知（`desktopAwareness`），它们功能高度重叠但实现分散：各自有独立的配置结构、定时器、触发逻辑、上下文组装和输出路径。这增加了维护负担、配置困惑，也阻碍了后续扩展（如新增主动行为类型时需要从头搭建完整链路）。统一为单一引擎可以降低复杂度，同时让心跳和桌面感知成为开箱即用的预设行为。

## What Changes

- **合并三套系统为统一的自主行为引擎**：心跳和桌面感知不再作为独立子系统，而是 `behaviorSettings.behaviorList` 中的预设行为项（preset），与用户自定义行为共享调度、执行和输出链路
- **新增行为动作类型 `desktopAwareness`**：前端截图 → 发送视觉模型判断 → 决定是否发言。截图在前端完成（确保获取的是用户设备的画面）
- **移除 HEARTBEAT.md 独立文件**：心跳任务说明统一存入行为项的 `action.prompt` 字段
- **统一执行路径为 `sendMessage()`**：所有行为触发后走正常聊天流程，完整携带主会话系统提示词和对话历史，所有工具均可用
- **双层调度（前端 + 后端）**：行为项新增 `runInBackground` 标记。`runInBackground=false`（默认）由前端定时器调度，适合需要前端能力的行为（如桌面截图）；`runInBackground=true` 由后端 asyncio 定时器调度，即使浏览器关闭也能执行（如心跳定时检查）。后端调度时走独立 LLM 调用 + WebSocket 广播结果到前端
- **移除独立的心跳/桌面感知后端代码**：`_heartbeat_periodic_loop`、`_run_heartbeat_check`、`_collect_heartbeat_tools`、`/api/lover/heartbeat-check` endpoint、`/api/lover/desktop-awareness-check` endpoint 等专属代码移除，由统一引擎替代
- **后端统一行为调度器**：重构 `py/behavior_engine.py`，为 `runInBackground=true` 的行为项提供通用的后端 asyncio 定时调度，复用与前端相同的触发类型（time/noInput/cycle）
- **保留 `messageKind` 标记**：行为触发的消息仍通过 `messageKind`（`heartbeat` / `desktopAwareness`）标记来源，便于 UI 区分展示
- **保留智能跳过逻辑**：行为项可配置 `skipIfRecentlyActive`（近期有对话则跳过）和 `noActionDetection`（LLM 判定无需发言则静默），原心跳和桌面感知的跳过逻辑迁移为行为级配置
- **内置预设（preset）**：首次启动或用户重置时自动添加心跳和桌面感知两个预设行为项（默认禁用），用户可修改或删除

## Capabilities

### New Capabilities
- `unified-behavior-engine`：统一自主行为引擎——调度、触发、执行、输出的完整链路重构，包含预设行为管理、新增动作类型、智能跳过配置、messageKind 标记

### Modified Capabilities
- `fts-context-injection`：原 spec 中 Requirement "Desktop awareness and heartbeat do not use FTS" 需要重新评估——合并后桌面感知和心跳走正常聊天流程，FTS 会自然注入（除非显式排除）

## Impact

- **后端**：`server.py`（移除心跳定时器/endpoint/广播，新增统一后端行为调度器）、`py/behavior_engine.py`（重构为统一引擎，支持 `runInBackground` 行为的后端调度）、`py/lover_system_context.py`（移除心跳相关辅助函数）
- **前端**：`static/js/renderer.js`（重构行为定时器，仅调度 `runInBackground=false` 的行为）、`static/js/vue_methods.js`（统一执行函数 `runBehavior`，移除 `_handleHeartbeatMessage` / `runHeartbeatCheck` / `runDesktopAwarenessCheck`，新增后端行为消息的 WebSocket 接收处理）、`static/js/vue_data.js`（合并 `heartbeat` / `desktopAwareness` 配置到 `behaviorSettings`）
- **UI**：`static/index.html`（移除独立的心跳/桌面感知配置面板，统一到自主行为页面）
- **配置**：`config/settings_template.json`（移除顶层 `heartbeat` / `desktopAwareness`，扩展 `behaviorSettings`）
- **i18n**：`static/js/locales/*.js`（新增/调整翻译键）
- **文档**：`docs/LOVER_SSOT.md`（同步更新架构说明）
- **已有 spec**：`openspec/specs/fts-context-injection/spec.md` 需要 delta spec
- **无需向后兼容**：项目处于开发阶段，无真实旧数据，直接替换配置结构
