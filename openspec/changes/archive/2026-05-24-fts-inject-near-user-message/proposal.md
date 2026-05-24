## Why

当前 FTS（全文检索）召回的相关记忆被拼接在 system prompt 尾部，在长对话中距离最新用户消息很远，Transformer 注意力衰减导致模型对召回内容利用率低。同时 system prompt 持续膨胀会稀释核心人设/规则指令的遵循能力。将 FTS 结果移到最新用户消息附近可显著提升 RAG 召回利用率，符合主流最佳实践。

## What Changes

- 将 FTS 检索结果从 `append_character_card_context` 中的 system prompt 拼接逻辑中剥离
- 新增独立函数 `search_fts_for_context`，返回格式化的 FTS 结果文本块
- 在 `server.py` 主聊天流程中，将 FTS 结果作为独立 `system` 消息插入到最新 `user` 消息正前方
- `append_character_card_context` 的 `include_fts` 参数保留但语义变为"是否执行 FTS 检索"（向后兼容桌面感知/心跳等调用方）
- 心跳和桌面感知场景同样适用新注入位置（它们已经有 `messages.extend(recent_chat)` + 最后追加 user message 的模式）

## Capabilities

### New Capabilities
- `fts-context-injection`: FTS 检索结果的独立提取与就近注入机制，支持在消息列表中动态插入检索上下文

### Modified Capabilities
<!-- 无现有 spec 需要修改 -->

## Impact

- **代码文件**：`py/lover_system_context.py`（提取新函数，修改原 FTS 注入逻辑）、`server.py`（主聊天流程注入位置变更）
- **API 兼容性**：已确认 deepseek-v4-flash、deepseek-v4-pro、GLM-5 均支持对话中间 system 消息
- **不影响**：前端、设置结构、数据存储格式
- **风险**：极低——若某模型不支持中间 system 消息，可回退到原方案（拼接 system prompt）
