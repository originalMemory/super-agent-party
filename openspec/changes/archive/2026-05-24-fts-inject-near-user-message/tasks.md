## 1. 提取独立 FTS 检索函数

- [x] 1.1 在 `py/lover_system_context.py` 中新增 `search_fts_for_context(settings, user_prompt)` 异步函数，从现有 FTS 代码块提取逻辑，返回格式化字符串或空串
- [x] 1.2 删除 `append_character_card_context` 中原有的 FTS 检索+拼接代码块（L272-L291）
- [x] 1.3 在模块 export 中暴露 `search_fts_for_context`

## 2. 主聊天流程注入改造

- [x] 2.1 在 `server.py` 第一个主聊天入口（约 L3779）中：将 `include_fts=True` 改为 `include_fts=False`，在 `append_character_card_context` 之后调用 `search_fts_for_context` 并将结果 insert 到最后一条 user 消息前
- [x] 2.2 在 `server.py` 第二个主聊天入口（约 L5899）中：同上处理
- [x] 2.3 封装一个 helper 函数 `inject_fts_before_last_user(messages, fts_block)` 执行查找+insert 逻辑，两个入口复用

## 3. 桌面感知和心跳场景清理

- [x] 3.1 桌面感知流程（约 L7565）：确认 `build_lover_system_messages(include_fts=...)` 改为 `include_fts=False`（这两个场景不需要 FTS 记忆召回）
- [x] 3.2 心跳流程（约 L7772）：同上，设为 `include_fts=False`

## 4. 验证与清理

- [x] 4.1 确认 `append_character_card_context` 中 `include_fts` 参数传 True/False 均不再执行 FTS 相关逻辑（参数可保留但无实际作用，或标记为 deprecated）
- [ ] 4.2 手动测试：发送消息后检查 API 请求的 messages 结构，确认 FTS system 消息位于最后 user 消息前
