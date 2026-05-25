## MODIFIED Requirements

### Requirement: Desktop awareness and heartbeat do not use FTS
原 requirement 按场景名（桌面感知 / 心跳）硬编码排除 FTS。统一行为引擎合并后，心跳和桌面感知不再作为独立场景存在，改为基于 `behavior_trigger` 通用标记的判断：当请求 `extra_body` 中 `behavior_trigger == true` 时，系统 SHALL NOT 注入 FTS 检索结果。该规则覆盖所有自主行为触发路径（前端通过 `sendMessage()` 触发的行为、后端调度行为的独立 LLM 调用）。

#### Scenario: Normal user message triggers FTS
- **WHEN** 请求未携带 `behavior_trigger` 标记
- **THEN** 正常执行 FTS 检索并按现有规则注入结果

#### Scenario: Frontend behavior trigger skips FTS
- **WHEN** 请求 `extra_body` 中 `behavior_trigger == true`（前端自主行为触发的 `sendMessage()`）
- **THEN** 跳过 FTS 检索，不注入任何内容

#### Scenario: Backend behavior trigger skips FTS
- **WHEN** 后端 `BackgroundBehaviorScheduler` 触发的独立 LLM 调用
- **THEN** 不调用 `search_fts_for_context`，messages 列表中不包含 FTS 相关的 system 消息
