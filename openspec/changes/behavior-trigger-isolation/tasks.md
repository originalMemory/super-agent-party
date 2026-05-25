## 1. 前端：Trigger 消息标记与移除

- [ ] 1.1 `static/js/vue_data.js`：新增 `behaviorLog: []`（顶层数据，初始空数组）
- [ ] 1.2 `static/js/vue_methods.js` `runBehavior`：在调用 `sendMessage()` 前设置 `this._behaviorTriggerMeta = { messageKind }`；使用 `try/finally` 包裹，确保异常时清空
- [ ] 1.3 `static/js/vue_methods.js` `sendMessage`：检查 `this._behaviorTriggerMeta`，给即将 push 到 `this.messages` 的 user 消息添加 `_behaviorTrigger: true`
- [ ] 1.4 `static/js/vue_methods.js` `sendMessage`：在 `saveConversations()` 之前从 `this.messages` 中过滤掉所有 `_behaviorTrigger: true` 的消息
- [ ] 1.5 `static/js/vue_methods.js` `generateAIResponse`：组装 assistant 回复消息时，检查 `_behaviorTriggerMeta`，写入 `messageKind`
- [ ] 1.6 `static/js/vue_methods.js` `runBehavior`：执行后根据 `noActionDetection` 检查 LLM 回复是否包含 NO_ACTION 标记，命中则**同时**移除 trigger user 消息（确保 1.4 已处理）和 assistant 回复消息——最终对话历史中无任何新增消息

## 2. 后端：Trigger 消息只存活于单次调用

- [ ] 2.1 `server.py` `BackgroundBehaviorScheduler` 触发路径：构造 LLM 调用的临时 messages 列表：`[system_prompt] + [全部历史 messages] + [{"role": "user", "content": trigger_prompt}]`，仅用于本次 LLM 调用
- [ ] 2.2 `server.py`：trigger prompt SHALL NOT 写入主会话的持久化 messages（仅有效 assistant 回复带 `messageKind` 写入）
- [ ] 2.3 验证 `noActionDetection` 命中时，主会话 messages 数组长度无变化（无 trigger、无 assistant 写入）

## 3. 执行日志

- [ ] 3.1 `static/js/vue_methods.js`：新增辅助方法 `_appendBehaviorLog(entry)`——追加到 `behaviorLog` 数组，超过 50 条时丢弃最旧的一条
- [ ] 3.2 `static/js/vue_methods.js` `runBehavior`：各分支结束时调用 `_appendBehaviorLog`（`executed` / `skipped_recent_active` / `skipped_screen_off` / `skipped_no_action` / `error`），含 `timestamp` / `behaviorName` / `presetId` / `triggerType` / `result` / `errorMessage?` / `durationMs?` 字段
- [ ] 3.3 `server.py` `BackgroundBehaviorScheduler` 触发路径：每次行为执行结束后通过 WebSocket 推送 `behavior_log_entry` 事件到所有连接的前端
- [ ] 3.4 `static/js/vue_methods.js` WebSocket `onmessage`：新增 `behavior_log_entry` 处理分支，调用 `_appendBehaviorLog`
- [ ] 3.5 `static/index.html`：自主行为配置页新增"执行日志"折叠展开区域，倒序展示 `behaviorLog`，按 result 类型上色（如 `executed` 绿色、`error` 红色、跳过类灰色）
- [ ] 3.6 `static/index.html`：日志条目格式化展示（相对时间 / 行为名称 / 触发类型 / 结果 / 耗时）

## 4. FTS 通用标记改造

- [ ] 4.1 `static/js/vue_methods.js`：`runBehavior` 触发 `sendMessage()` 时在请求 `extra_body` 中添加 `behavior_trigger: true`
- [ ] 4.2 `server.py`：在请求模型（`ChatCompletionRequest` 或对应 Pydantic 类）中支持读取 `extra_body.behavior_trigger`
- [ ] 4.3 `server.py` `generate_stream_response`（两处调用点）：在 `search_fts_for_context` 调用前检查 `behavior_trigger`，为 true 时跳过 FTS 检索
- [ ] 4.4 `server.py` `BackgroundBehaviorScheduler` 触发路径：独立 LLM 调用不调用 `search_fts_for_context`（直接跳过，不依赖 `behavior_trigger` 标记，因为不走 `generate_stream_response`）

## 5. i18n

- [ ] 5.1 `static/js/locales/zh-CN.js`：新增执行日志相关翻译键（`behaviorExecutionLog`、`logResultExecuted`、`logResultSkippedRecentActive`、`logResultSkippedScreenOff`、`logResultSkippedNoAction`、`logResultError` 等）
- [ ] 5.2 `static/js/locales/en-US.js`：同步英文翻译

## 6. 验证

- [ ] 6.1 手动验证：触发心跳预设，对话历史中仅新增一条 `messageKind = "heartbeat"` 的 assistant 消息，无 `[system]:` user 消息
- [ ] 6.2 手动验证：触发桌面感知预设，对话历史中仅新增一条 `messageKind = "desktopAwareness"` 的 assistant 消息
- [ ] 6.3 手动验证：启用 `noActionDetection` 行为且 LLM 回 `[NO_ACTION]`，对话历史 messages 数组长度无变化
- [ ] 6.4 回归验证：用户手动发送普通消息，消息正常持久化（无 `_behaviorTrigger` 误标）
- [ ] 6.5 回归验证：行为触发过程中抛异常，下一次普通 `sendMessage` 不被错误标记（`_behaviorTriggerMeta` 已清空）
- [ ] 6.6 手动验证：执行日志面板正确展示前端触发和后端触发的所有记录
- [ ] 6.7 手动验证：行为触发的请求 FTS 不注入；用户普通消息的请求 FTS 正常注入
- [ ] 6.8 验证 `openspec validate behavior-trigger-isolation --strict` 通过
