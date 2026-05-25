## 1. 数据模型与配置

- [x] 1.1 `config/settings_template.json`：移除顶层 `heartbeat` 和 `desktopAwareness` 配置块
- [x] 1.2 `config/settings_template.json`：扩展 `behaviorSettings.behaviorList` 默认值，加入心跳和桌面感知两个预设行为项（`enabled: false`），包含 `runInBackground`、`skipIfRecentlyActive`、`skipWindowMinutes`、`noActionDetection`、`messageKind`、`presetId` 等新增字段；心跳预设的 `action.prompt` 直接存储 HEARTBEAT.md 完整文本
- [x] 1.3 `static/js/vue_data.js`：移除 `heartbeat`、`desktopAwareness` 顶层数据；`newBehavior` 模板和 `behaviorSettings` 初始结构新增 `runInBackground`、`skipIfRecentlyActive`、`skipWindowMinutes`、`noActionDetection`、`messageKind`、`presetId` 字段
- [x] 1.4 `py/behavior_engine.py`：`BehaviorItem` Pydantic 模型新增 `runInBackground`、`skipIfRecentlyActive`、`skipWindowMinutes`、`noActionDetection`、`messageKind`、`presetId` 字段（含默认值）；`BehaviorAction.type` 扩展支持 `"desktopAwareness"` 枚举

## 2. 移除旧心跳系统

- [ ] 2.1 `server.py`：移除 `_heartbeat_periodic_loop`、`_heartbeat_task`、`_heartbeat_in_flight`、`_build_heartbeat_prompt`、`_collect_heartbeat_tools`、`_execute_heartbeat_tool_calls`、`_heartbeat_write_and_broadcast`、`_run_heartbeat_check` 函数
- [ ] 2.2 `server.py`：移除 `/api/lover/heartbeat-check` endpoint
- [ ] 2.3 `server.py` `lifespan`：移除心跳定时器启动和 cancel 逻辑
- [ ] 2.4 `py/lover_system_context.py`：移除 `heartbeat_skip_window_ms`、`read_heartbeat_md` 等心跳专属辅助函数
- [ ] 2.5 `static/js/vue_methods.js`：移除 `runHeartbeatCheck`、`_handleHeartbeatMessage` 方法
- [ ] 2.6 `static/js/vue_methods.js` WebSocket `onmessage`：移除 `heartbeat_message` 处理分支
- [ ] 2.7 `static/index.html`：移除心跳配置 UI 面板
- [ ] 2.8 移除 `HEARTBEAT.md` 文件读写相关 endpoint（`/api/lover/file` 中的 `HEARTBEAT.md` 分支）以及前端 `loadAllLoverFiles` 中的 HEARTBEAT.md 读取

## 3. 移除旧桌面感知系统

- [ ] 3.1 `server.py`：移除 `/api/lover/desktop-awareness-check` endpoint
- [ ] 3.2 `static/js/vue_methods.js`：移除 `startDesktopAwarenessTimer`、`stopDesktopAwarenessTimer`、`runDesktopAwarenessCheck` 方法
- [ ] 3.3 `static/index.html`：移除桌面感知配置 UI 面板
- [ ] 3.4 `static/js/vue_data.js`：确认 `desktopAwareness` 顶层数据已在 1.3 中移除

## 4. 前端调度与执行

- [ ] 4.1 `static/js/renderer.js`：重构 time/noInput/cycle 三个定时器，增加 `runInBackground` 过滤——仅调度 `runInBackground === false` 的行为
- [ ] 4.2 `static/js/vue_methods.js` `runBehavior`：增加 `skipIfRecentlyActive` 检查逻辑（调用辅助方法判断主分组近期活动）
- [ ] 4.3 `static/js/vue_methods.js` `runBehavior`：增加 `action.type === "desktopAwareness"` 分支——Electron 环境下先 `powerMonitor.getSystemIdleState()` 检测锁屏/idle（命中则跳过），再 `desktopCapturer.getSources()` 截图 → 组装带图片的消息 → `sendMessage()`；非 Electron 环境静默跳过
- [ ] 4.4 `static/js/vue_methods.js` `runBehavior`：在调用 `sendMessage` 前设置 `_behaviorTriggerMeta = { messageKind }`；`generateAIResponse` 组装 assistant 回复时据此写入 `messageKind`
- [ ] 4.5 `static/js/vue_methods.js` `runBehavior`：执行后根据 `noActionDetection` 检查 LLM 回复是否包含 NO_ACTION 标记，命中则移除 assistant 回复消息
- [ ] 4.6 触发前抛弃 `[system]:` 前缀重复触发的防抖：复用现有 `_behaviorTriggerMeta` 状态避免并发触发同一行为

## 5. 后端调度器

- [ ] 5.1 `py/behavior_engine.py`：新增 `BackgroundBehaviorScheduler` 类，在 `lifespan` 启动时为所有 `runInBackground=true` 且 `platforms` 包含 `"chat"` 的行为项创建 asyncio 定时器（支持 time/cycle 触发类型；noInput 在后端不适用，跳过）
- [ ] 5.2 `py/behavior_engine.py`：`BackgroundBehaviorScheduler` 配置变更时 diff 新旧 `behaviorSettings`（JSON 序列化比较），仅当实际变化时才重建定时器，避免无关配置变更导致 cycle 计时重置
- [ ] 5.3 `server.py`：后端行为触发时组装完整主会话上下文（复用 `build_lover_system_messages` + 读取全部对话历史），独立调用 LLM
- [ ] 5.4 `server.py`：后端行为执行支持完整工具调用循环（复用 `dispatch_tool`，不限制工具白名单）
- [ ] 5.5 `server.py`：后端行为执行前检查 `skipIfRecentlyActive`（复用 `is_default_group_recently_active`）
- [ ] 5.6 `server.py`：后端行为 LLM 回复后检查 `noActionDetection`（复用 `is_awareness_no_action`）
- [ ] 5.7 `server.py`：后端行为有效回复写入主会话（带 `messageKind` 标记）+ WebSocket `behavior_message` 广播
- [ ] 5.8 `server.py` `lifespan`：启动 `BackgroundBehaviorScheduler`，关闭时 cancel
- [ ] 5.9 `server.py` `save_settings` WebSocket handler：行为配置变更时通知 `BackgroundBehaviorScheduler.update_config()`

## 6. WebSocket 与前端接收

- [ ] 6.1 `static/js/vue_methods.js` WebSocket `onmessage`：新增 `behavior_message` 处理分支，调用 `_handleBehaviorMessage`
- [ ] 6.2 `static/js/vue_methods.js`：实现 `_handleBehaviorMessage`——追加消息到主会话 messages（去重判断），按 `messageKind` 渲染，调用 `saveConversations`

## 7. UI 改造

- [ ] 7.1 `static/index.html`：行为编辑弹窗新增 `runInBackground`、`skipIfRecentlyActive`（含 `skipWindowMinutes`）、`noActionDetection`、`messageKind` 配置项
- [ ] 7.2 `static/index.html`：行为编辑弹窗 `action.type` 下拉新增 `"desktopAwareness"` 选项
- [ ] 7.3 `static/index.html`：行为卡片摘要（`getBehaviorSummary`）适配新字段展示（如显示 `runInBackground` 徽章、`presetId` 标记）

## 8. i18n

- [ ] 8.1 `static/js/locales/zh-CN.js`：新增/调整自主行为相关翻译键（`runInBackground`、`skipIfRecentlyActive`、`noActionDetection`、`desktopAwareness` 动作类型、预设标识等）
- [ ] 8.2 `static/js/locales/en-US.js`：同步英文翻译
- [ ] 8.3 移除已不再使用的心跳/桌面感知专属翻译键（`heartbeatXxx` / `desktopAwarenessXxx` 中由独立面板使用的部分）

## 9. 文档

- [ ] 9.1 `docs/LOVER_SSOT.md`：更新架构说明——心跳和桌面感知合并到统一自主行为引擎，移除独立子系统描述

## 10. 验证

- [ ] 10.1 手动验证：创建一个 `action.type = "prompt"` + `runInBackground = false` 的行为，cycle 触发后通过前端 `sendMessage()` 走完整流程
- [ ] 10.2 手动验证：启用心跳预设（`runInBackground = true`），关闭浏览器后端定时器仍然触发；触发后 LLM 调用 → 工具循环 → 写主会话 → WebSocket `behavior_message` 广播 → 前端追加显示
- [ ] 10.3 手动验证：Electron 环境启用桌面感知预设，锁屏时跳过；解锁后截图 → 视觉模型判断 → 触发回复
- [ ] 10.4 手动验证：`save_settings` 仅修改模型名时，后端 cycle 计时器不重置
- [ ] 10.5 验证 `openspec validate unify-behavior-engine-core --strict` 通过
