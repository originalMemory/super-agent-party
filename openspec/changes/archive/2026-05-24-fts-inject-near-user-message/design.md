## Context

当前 `py/lover_system_context.py` 中的 `append_character_card_context` 函数在构建 system prompt 时，将 FTS 检索结果直接拼接到 system message 的 content 末尾。调用链路如下：

1. `server.py` 主聊天端点调用 `append_character_card_context(messages, settings, include_fts=True, ...)`
2. 函数内部执行 `search_memory` 并将结果 `content_append` 到 system message
3. 最终消息结构：`[system(人设+FTS)] → [user/assistant 历史...] → [user 最新消息]`

桌面感知和心跳场景使用 `build_lover_system_messages` 构建独立的 system messages 列表，再追加 recent_chat 和最终 user message，结构类似。

`server.py` 中有两个主聊天流程入口（约 L3779 和 L5899）都调用 `append_character_card_context`。

## Goals / Non-Goals

**Goals:**
- FTS 检索结果注入到最新 user 消息正前方，缩短注意力距离
- 保持 system prompt 精练（仅人设/规则/记忆笔记/日记概要）
- 对桌面感知/心跳场景同样生效
- 向后兼容：不改变外部调用接口的必需参数

**Non-Goals:**
- 不处理 DeepSeek-Reasoner (R1) 的兼容性降级（用户明确排除）
- 不改变 FTS 检索逻辑本身（查询词、结果数、ranking）
- 不修改前端或设置 schema

## Decisions

### 1. 提取独立函数 `search_fts_for_context`

**选择**：从 `append_character_card_context` 中剥离 FTS 逻辑为独立 async 函数，返回格式化字符串。

**理由**：
- 解耦检索与注入位置的关系，调用方可自由选择注入点
- 桌面感知/心跳/主聊天三个场景可复用同一检索函数
- 替代方案（在 `append_character_card_context` 中通过参数控制注入位置）会让函数签名和职责更复杂

### 2. 注入方式：独立 system message 而非拼接到 user message

**选择**：在最新 user 消息前 `insert` 一条 `{"role": "system", "content": fts_block}`。

**理由**：
- 语义清晰：模型不会误认为检索内容是用户说的话
- deepseek-v4-flash/pro 和 GLM-5 均已确认支持对话中间 system 消息
- 替代方案（拼接到 user message prefix）会污染用户消息原文，影响后续 mem0/知识库搜索依赖 user_prompt 的准确性

### 3. 注入位置查找逻辑

**选择**：从消息列表末尾向前找第一条 `role == "user"` 的消息，在其索引处 `insert`。

**理由**：
- 简单且鲁棒——无论消息列表如何构建，总是找最后一条 user 消息
- 若列表中无 user 消息（极端 edge case），回退不注入

### 4. `include_fts` 参数处理

**选择**：保留 `append_character_card_context` 的 `include_fts` 参数，但将其行为改为**不执行任何 FTS 操作**（原来是在内部拼接，现在整块删除）。调用方如需 FTS 需显式调用新函数。

**理由**：
- 桌面感知/心跳场景已经通过 `build_lover_system_messages` 间接调用，改为显式调用新函数更清晰
- 主聊天流程改为：先 `append_character_card_context(include_fts=False)`，再调用 `search_fts_for_context` + insert

## Risks / Trade-offs

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| 某些小众模型/自部署后端不支持中间 system 消息 | 低 | 主流 provider 已确认支持；如遇到可加配置开关回退原方案 |
| 多条 system 消息可能影响某些模型的 token 缓存命中 | 低 | 智谱的上下文缓存按 prefix match，system 在开头的缓存不受影响 |
| 消息列表操作（insert）改变索引，影响后续逻辑 | 中 | FTS 注入应在所有消息列表构建完成后、发送给 API 前的最后一步执行 |

## Open Questions

- 是否需要添加设置项让用户选择注入位置（system prompt vs near-user）？暂定不加，默认新方案，后续根据反馈决定。
