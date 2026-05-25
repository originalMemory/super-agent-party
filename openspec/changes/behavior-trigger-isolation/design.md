## Context

前置 change `unify-behavior-engine-core` 已完成功能合并：心跳和桌面感知作为预设进入统一行为引擎，所有前端行为通过 `runBehavior → sendMessage()` 触发，后端 `runInBackground=true` 行为通过 `BackgroundBehaviorScheduler` 调度并独立调用 LLM。

但有三件事被刻意从前置 change 推迟：

1. **触发消息污染**：`sendMessage('[system]:xxx')` 会把这条消息 push 到 `this.messages` 并最终 `saveConversations`，导致对话历史中累积大量 `[system]:` 触发消息。
2. **执行日志缺失**：行为是否触发、是否跳过（原因）、是否回复，目前只能靠 `console.log` 观察。
3. **FTS 排除硬编码**：`fts-context-injection` 主 spec 当前按"心跳/桌面感知"场景名硬编码排除 FTS。合并后这两个不再是独立场景。

这三件事的共同点是**都涉及主对话或跨模块协议的改动**：`sendMessage` 是所有普通消息的入口，FTS 是所有 LLM 调用的预处理。隔离到独立 change 是为了让 review 焦点收窄。

## Goals / Non-Goals

**Goals:**
- 自主行为触发的对话历史中 SHALL 只留下 assistant 回复（带 `messageKind`），不留 `[system]:` user 消息
- LLM 调用的 messages 入参中仍包含 trigger prompt（确保模型知道触发意图），仅"持久化路径"上移除
- 后端调度的行为执行：trigger prompt 仅存在于本次 API 调用的临时消息列表中，不写入主会话持久化 messages
- 执行日志（最近 50 条）支持在 UI 中查看
- FTS 排除改为基于 `behavior_trigger` 通用标记的判断，覆盖前端触发和后端触发两条路径

**Non-Goals:**
- 不改造非行为触发的普通对话路径（`sendMessage` 普通调用的语义保持不变）
- 不持久化执行日志（内存中维护即可，重启清空）
- 不暴露执行日志 API 给外部消费
- 不修改 FTS 检索本身的实现（`search_fts_for_context`）

## Decisions

### D1: 前端 trigger 消息标记 + 移除

**问题**：`sendMessage` 当前会无差别 push `userInput` 到 `this.messages` 并 `saveConversations`。行为触发时传入 `[system]:xxx`，会作为 user 消息留下来。

**决定**：

1. `runBehavior` 在调用 `sendMessage()` 前设置 `this._behaviorTriggerMeta = { messageKind: <配置值> }`。
2. `sendMessage` 内部检查该标记，给即将 push 到 `this.messages` 的 user 消息添加非持久字段 `_behaviorTrigger: true`。
3. `sendMessage` 在 `generateAIResponse` 完成后、`saveConversations()` 之前，从 `this.messages` 中过滤掉所有 `_behaviorTrigger: true` 的消息。
4. `generateAIResponse` 组装 assistant 回复消息时，检查 `_behaviorTriggerMeta`，写入 `messageKind`。
5. `runBehavior` 在执行完成后清空 `_behaviorTriggerMeta`（`finally`）。
6. 若启用 `noActionDetection` 且 LLM 回复命中 NO_ACTION，同时移除 assistant 回复消息——最终对话历史中无任何新增消息。

**LLM 调用入参**：trigger 消息仍参与本次 LLM 调用的 messages 组装（只是在 `saveConversations` 前移除），确保模型知道触发意图。

**理由**：这是最小侵入的方案——`sendMessage` 主流程保持不变，仅在两处加 `_behaviorTrigger` 标记的读写。对普通对话（无 `_behaviorTriggerMeta`）完全没有影响。

**Alternatives considered**：
- 让 `runBehavior` 走另一条不写 `this.messages` 的执行路径（复制一份 `sendMessage` 逻辑）——会引入路径分叉，未来 `sendMessage` 任何改动都要同步两边
- 让 trigger 消息存进去然后过滤展示——历史仍然被污染，只是 UI 不显示，FTS / context 仍会带上

### D2: 后端 trigger 消息只存活于单次调用

**决定**：后端调度行为执行时，构造本次 LLM 调用的 messages 列表：`[system_prompt] + [全部历史 messages] + [{"role": "user", "content": trigger_prompt}]`。这个临时列表只用于调用 LLM，不写回主会话的持久化 messages。

LLM 返回有效回复后：
- 通过 `noActionDetection` 检查
- 通过则将 `{role: "assistant", messageKind: <配置值>, content: reply}` 单独写入主会话的持久化 messages
- 通过 WebSocket `behavior_message` 广播

**理由**：后端不走 `sendMessage` 主流程，直接控制消息组装更直观，不需要"先写后删"的标记机制。

### D3: 执行日志（内存数组 + UI 展开区）

**决定**：`behaviorSettings` 新增 `behaviorLog: Array`（内存中维护，不持久化），保留最近 50 条执行记录。

每条日志结构：
```js
{
  timestamp: 1748000000000,         // 触发时间
  behaviorName: "心跳",              // 行为名称
  presetId: "heartbeat" | null,
  triggerType: "cycle" | "time" | "noInput",
  result: "executed"
        | "skipped_recent_active"
        | "skipped_screen_off"      // 桌面感知专属
        | "skipped_no_action"       // LLM 命中 NO_ACTION
        | "error",
  errorMessage?: string,            // result === "error" 时
  durationMs?: number               // 整体耗时
}
```

写入点：
- 前端：`runBehavior` 各分支结束时写入（前 50 条 FIFO）
- 后端：`BackgroundBehaviorScheduler` 触发后通过 WebSocket `behavior_log_entry` 推送到前端，前端追加到同一 `behaviorLog` 数组

UI：自主行为配置页新增"执行日志"展开区域，倒序展示（最新在上），按 result 类型上色，无需分页。

**理由**：调试用，不需要持久化。50 条够覆盖一天的心跳记录（30min 一次 = 48 条）。

**Alternatives considered**：
- 持久化到本地文件——增加 I/O 复杂度，调试场景下未必需要历史回看
- 后端独立维护一份日志 + 提供 GET API——前端展示需要轮询或拉取，复杂度高于 WebSocket 推送

### D4: FTS 通用标记替换硬编码场景

**决定**：FTS 排除改为基于请求标记的判断。

前端：`runBehavior` 触发 `sendMessage()` 时在请求 `extra_body` 中加 `behavior_trigger: true`。
后端：`server.py` 的 `generate_stream_response` 在两处调用 `search_fts_for_context` 之前，检查 `request.extra_body.behavior_trigger`，true 时跳过 FTS 检索。
后端调度路径：`BackgroundBehaviorScheduler` 触发的独立 LLM 调用本来就不走 `generate_stream_response`，但其调用路径也应统一不触发 FTS（直接不调用 `search_fts_for_context` 即可）。

**主 spec 同步**：`openspec/specs/fts-context-injection/spec.md` 中原 "Desktop awareness and heartbeat do not use FTS" requirement 被 MODIFIED 为 "Behavior triggers do not use FTS"，使用 `behavior_trigger` 标记判断。

**理由**：消除"按场景名硬编码"的反模式，未来加新行为类型不需要再改 FTS 逻辑。

**Alternatives considered**：
- 按 `messageKind` 判断（`heartbeat` / `desktopAwareness`）——仍是按类型枚举的硬编码，未来加新类型还要改
- 检查最后一条消息是否带 `_behaviorTrigger`——前端可以但需要把字段透传到后端，不如 extra_body 直接

## Risks / Trade-offs

- **[D1 高危：误删普通对话消息]** → `sendMessage` 移除 `_behaviorTrigger: true` 的消息逻辑，如果普通对话路径错误标记了 `_behaviorTriggerMeta`，会丢消息 → `runBehavior` 严格使用 try/finally 包裹，确保异常时也清空 `_behaviorTriggerMeta`；普通 `sendMessage` 调用前不应有任何路径设置该标记；review 时重点关注所有设置/清空 `_behaviorTriggerMeta` 的代码点
- **[D1 风险：消息丢失影响 UI 流]** → 移除 user 消息后，UI 中的"用户气泡"会瞬间消失 → 由于 user 消息是 `[system]:xxx`，本来就不显示气泡（已有渲染逻辑过滤）；只影响内存数组，不影响视觉
- **[D2 风险：后端触发后 LLM 没有"对话上下文衔接"]** → 后端写入 assistant 消息时，主会话历史里没有 trigger user 消息，下一次普通对话时模型可能困惑"为什么突然冒出一句 assistant 关心" → 实际上这正是设计目的：让 AI 的主动发言看起来像"自然行为"。模型在后续对话中通过历史回复内容理解上下文即可
- **[D3 风险：内存累积]** → 50 条上限 + 简单结构，单条 < 500 字节，总占用 < 25KB，可忽略
- **[D4 风险：未来某些行为需要 FTS]** → 假设未来某个自主行为确实需要 FTS（如基于记忆的主动回忆触发）→ 改成行为级 `disableFts` 配置即可，比当前 PR 范围窄
- **[与前置 change 顺序耦合]** → 必须在 `unify-behavior-engine-core` 归档后才能开始 → 严格执行 OpenSpec 工作流，先归档前置 change
