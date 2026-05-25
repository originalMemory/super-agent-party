## Why

依赖前置 change `unify-behavior-engine-core` 完成功能合并后，仍有三件「横切优化」未处理：

1. **触发消息污染对话历史**：`runBehavior` 通过 `sendMessage()` 触发时，`[system]:prompt` 会作为 user 消息持久化。心跳每 30 分钟触发一次，一天下来会在历史里积累大量 `[system]:` 消息，污染上下文窗口。
2. **可观测性缺失**：自主行为执行（触发/跳过/无行动/错误）没有日志，调试时只能猜。
3. **FTS 排除逻辑硬编码场景名**：当前 `fts-context-injection` spec 中 "Desktop awareness and heartbeat do not use FTS" 按场景名硬编码排除。合并后心跳和桌面感知不再作为独立场景存在，需改成基于 `behavior_trigger` 通用标记的判断。

这三件事都涉及主对话路径或跨模块协议，本 change 将它们一起处理，便于独立 review 和回归。

## What Changes

- **Trigger 消息持久化隔离（前端）**：`runBehavior` 调用 `sendMessage()` 前设置 `_behaviorTriggerMeta = { messageKind }`。`sendMessage` 内部据此给 push 到 `this.messages` 的 user 消息添加 `_behaviorTrigger: true` 标记。`sendMessage` 的 `finally`/`generateAIResponse` 完成后，在 `saveConversations()` 之前从 `this.messages` 中移除所有 `_behaviorTrigger: true` 的消息（不持久化）。
- **Trigger 消息持久化隔离（后端）**：后端调度行为的 trigger prompt 仅存在于本次 LLM 调用的临时消息列表中，不写入主会话的持久化 messages。
- **NO_ACTION 路径补全**：启用 `noActionDetection` 且 LLM 回复命中 NO_ACTION 时，同时移除 trigger user 消息和 assistant 回复——最终对话历史中无任何新增消息。
- **新增执行日志**：`behaviorSettings` 维护内存中的 `behaviorLog` 数组（最近 50 条，不持久化），每次触发/跳过/执行后写入日志。自主行为配置页新增"执行日志"展开区域。
- **FTS 排除逻辑改造**：FTS 检索改为基于 `behavior_trigger` 通用标记的判断。前端 `runBehavior` 触发 `sendMessage()` 时在请求 `extra_body` 中添加 `behavior_trigger: true`；后端 `generate_stream_response` 在 `search_fts_for_context` 调用前检查该标记，true 时跳过 FTS 检索。
- **同步主 spec**：`openspec/specs/fts-context-injection/spec.md` 中 "Desktop awareness and heartbeat do not use FTS" requirement 在归档时被 MODIFIED 为 "Behavior triggers do not use FTS"。

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `unified-behavior-engine`：新增触发消息隔离、NO_ACTION 完整移除路径、执行日志 requirements
- `fts-context-injection`：将硬编码场景排除改为基于 `behavior_trigger` 通用标记的判断

## Impact

- **前端**：`static/js/vue_methods.js`（修改 `sendMessage` 主流程加入 trigger 标记和移除逻辑；修改 `generateAIResponse` 加 `messageKind` 写入；`runBehavior` 设置元数据并在 NO_ACTION 时移除 trigger 消息；新增 `behaviorLog` 数组维护与读取）、`static/js/vue_data.js`（新增 `behaviorLog: []`）
- **后端**：`server.py`（`generate_stream_response` 两处调用点跳过 FTS；后端调度行为的 trigger 消息仅本次调用临时存在）
- **UI**：`static/index.html`（自主行为配置页新增"执行日志"展开区域）
- **i18n**：`static/js/locales/*.js`（新增执行日志相关翻译键）
- **依赖关系**：本 change 依赖 `unify-behavior-engine-core` 已完成（必须有统一的 `runBehavior` 路径、统一的 `behaviorList` 数据模型、后端 `BackgroundBehaviorScheduler`）
- **高风险点**：`sendMessage` / `generateAIResponse` 是所有普通对话的主路径，引入 `_behaviorTrigger` 标记和移除逻辑需要仔细回归——确保普通消息不会被错误移除
