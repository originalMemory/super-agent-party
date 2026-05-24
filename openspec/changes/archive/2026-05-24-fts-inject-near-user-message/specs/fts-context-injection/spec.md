## ADDED Requirements

### Requirement: Independent FTS search function
系统 SHALL 提供独立的异步函数 `search_fts_for_context(settings, user_prompt)` 用于执行 FTS 检索并返回格式化的文本块。该函数与 system prompt 构建逻辑解耦，调用方可自行决定注入位置。

#### Scenario: FTS returns results
- **WHEN** `search_fts_for_context` 被调用且 FTS 工作空间存在且有匹配结果
- **THEN** 函数返回格式为 `"## 相关回忆\n- [path] snippet\n..."` 的非空字符串

#### Scenario: FTS returns no results
- **WHEN** `search_fts_for_context` 被调用但无匹配结果或工作空间不存在
- **THEN** 函数返回空字符串 `""`

#### Scenario: FTS search raises exception
- **WHEN** FTS 检索过程中抛出异常
- **THEN** 函数捕获异常、记录 warning 日志、返回空字符串（不中断主流程）

### Requirement: FTS results injected near latest user message
系统 SHALL 将 FTS 检索结果作为独立的 `system` 角色消息插入到消息列表中最新 `user` 消息的正前方位置。

#### Scenario: Normal chat with FTS results
- **WHEN** 主聊天流程中 FTS 返回非空结果
- **THEN** 在最终发送给 API 的 messages 数组中，FTS 内容以 `{"role": "system", "content": fts_block}` 形式出现在最后一条 `role == "user"` 消息的正前方（index 位置）

#### Scenario: No user message in list
- **WHEN** 消息列表中不存在 `role == "user"` 的消息（极端 edge case）
- **THEN** 不注入 FTS 结果，静默跳过

#### Scenario: FTS results empty
- **WHEN** FTS 返回空字符串
- **THEN** 不插入任何额外消息，消息列表保持不变

### Requirement: System prompt no longer contains FTS results
`append_character_card_context` 函数 SHALL NOT 将 FTS 检索结果拼接到 system message content 中。原有的 FTS 拼接逻辑 SHALL 被移除。

#### Scenario: System prompt content after change
- **WHEN** `append_character_card_context` 以 `include_fts=True` 被调用
- **THEN** 返回的 system message content 中不包含 "## 相关回忆" 段落；FTS 相关代码块被删除或跳过

### Requirement: Desktop awareness and heartbeat do not use FTS
桌面感知和心跳场景 SHALL NOT 注入 FTS 检索结果。这两个场景的核心输入分别是截图和时间状态，不是在回答用户提问，FTS 记忆召回对其决策无实质帮助。

#### Scenario: Heartbeat without FTS
- **WHEN** 心跳流程执行
- **THEN** 消息列表中不包含 FTS 相关的 system 消息

#### Scenario: Desktop awareness without FTS
- **WHEN** 桌面感知流程执行
- **THEN** 消息列表中不包含 FTS 相关的 system 消息
