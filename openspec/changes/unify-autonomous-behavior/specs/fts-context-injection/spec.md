## MODIFIED Requirements

### Requirement: Desktop awareness and heartbeat do not use FTS
原规则按场景名硬编码排除。合并后心跳和桌面感知不再作为独立场景存在，改为通用条件判断：FTS 检索 SHALL 仅在最后一条消息为 `role == "user"` 时触发。自主行为的触发消息不持久化（D9），后端触发时 trigger prompt 也不写入 messages，因此自主行为的 LLM 调用不满足此条件，FTS 自然不会注入。

#### Scenario: Normal user message triggers FTS
- **WHEN** 请求未携带 `behavior_trigger` 标记
- **THEN** 正常执行 FTS 检索并注入结果

#### Scenario: Behavior trigger skips FTS
- **WHEN** 请求 `extra_body` 中 `behavior_trigger == true`（前端或后端行为触发）
- **THEN** 跳过 FTS 检索，不注入任何内容
