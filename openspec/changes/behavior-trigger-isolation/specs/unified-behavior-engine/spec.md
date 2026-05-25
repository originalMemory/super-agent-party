## ADDED Requirements

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

### Requirement: Trigger metadata cleared after execution
系统 SHALL 在 `runBehavior` 执行完成（成功、失败、异常）后清空 `_behaviorTriggerMeta`，防止后续普通 `sendMessage` 调用被错误标记。

#### Scenario: Normal sendMessage after behavior trigger
- **WHEN** 一次 `runBehavior` 执行完成后，用户立即手动发送普通消息
- **THEN** 该普通消息 SHALL NOT 被标记为 `_behaviorTrigger`，正常持久化到对话历史

#### Scenario: Behavior trigger raises exception
- **WHEN** `runBehavior` 执行过程中抛出异常
- **THEN** `_behaviorTriggerMeta` 仍被清空（通过 `try/finally`）

### Requirement: Execution log
系统 SHALL 在内存中维护最近 50 条行为执行日志。每条日志包含：触发时间戳、行为名称、`presetId`、触发类型、执行结果（`executed` / `skipped_recent_active` / `skipped_screen_off` / `skipped_no_action` / `error`）。

#### Scenario: Behavior executed successfully
- **WHEN** 一个行为被触发并成功执行（LLM 返回有效回复）
- **THEN** 日志记录 `executed`

#### Scenario: Behavior skipped due to recent activity
- **WHEN** 一个行为因 `skipIfRecentlyActive` 命中近期活动被跳过
- **THEN** 日志记录 `skipped_recent_active`

#### Scenario: Desktop awareness skipped due to screen off
- **WHEN** 桌面感知行为因锁屏/idle 被跳过
- **THEN** 日志记录 `skipped_screen_off`

#### Scenario: Behavior skipped due to NO_ACTION
- **WHEN** 一个行为 LLM 回复命中 NO_ACTION 被跳过
- **THEN** 日志记录 `skipped_no_action`

#### Scenario: Behavior raises error
- **WHEN** 一个行为执行过程中抛出异常
- **THEN** 日志记录 `error`，包含 `errorMessage`

#### Scenario: Log viewable in UI
- **WHEN** 用户在自主行为配置页展开"执行日志"
- **THEN** UI 展示最近 50 条执行记录列表（倒序，最新在上）

#### Scenario: Backend behavior log pushed to frontend
- **WHEN** 后端调度触发的行为执行完成
- **THEN** 后端通过 WebSocket `behavior_log_entry` 推送日志条目到前端，前端追加到 `behaviorLog` 数组

#### Scenario: Log capped at 50 entries
- **WHEN** `behaviorLog` 长度达到 50
- **THEN** 写入新条目时 SHALL 丢弃最旧的一条（FIFO）

### Requirement: Behavior trigger flag in request
前端 `runBehavior` 触发的 `sendMessage()` 请求 SHALL 在 `extra_body` 中携带 `behavior_trigger: true` 标记，供后端识别本次请求来自自主行为触发。

#### Scenario: Frontend behavior trigger sends flag
- **WHEN** `runBehavior` 调用 `sendMessage()` 发起请求
- **THEN** 请求体 `extra_body` 中包含 `behavior_trigger: true`

#### Scenario: Normal user message does not send flag
- **WHEN** 用户手动发送普通消息
- **THEN** 请求体 `extra_body` 中不包含 `behavior_trigger` 字段（或为 false）
