## 1. 数据模型扩展

- [x] 1.1 `config/settings_template.json`：`memories[]` 项新增 `soul`（默认 `""`）、`memoryNotes`（默认 `""`）；`memorySettings` 新增 `userProfile`（默认 `""`）、`memoryDirPath`（默认 `""`）、`memoryIndexSyncMinutes`（默认 `10`）
- [x] 1.2 `static/js/vue_data.js`：`memories[]` 初始结构新增 `soul`、`memoryNotes`；`memorySettings` 新增 `userProfile`、`memoryDirPath`、`memoryIndexSyncMinutes`
- [x] 1.3 `static/js/vue_methods.js`：`addMemory` / `resetNewMemory` / `copyExistingMemoryData` 初始化 `soul`、`memoryNotes`
- [x] 1.4 `py/get_setting.py`：`load_settings` 加载后对旧 `memories[]` 补全 `soul`、`memoryNotes` 默认值（向后兼容）

## 2. System Prompt 注入链扩展

- [x] 2.1 `server.py` `generate_stream_response`：在现有 `cur_memory` 注入链**前**插入 `userProfile`（`## 用户档案`）、`soul`（`## 元层原则`）注入
- [x] 2.2 `server.py` `generate_stream_response`：在 `genericSystemPrompt` 之后插入 `memoryNotes`（`## 记忆笔记`）常驻注入
- [x] 2.3 `server.py` `generate_stream_response`：在 `memoryNotes` 之后预留 FTS recall 注入点（TODO 注释）
- [x] 2.4 注入格式：使用 Markdown 标题隔离，`{{user}}` / `{{char}}` 占位符替换，空值跳过
- [x] 2.5 mem0 默认关闭：代码已为"未配置 providerId 则不启用"，无需额外修改

## 3. AI 工具：角色卡查看与修改

- [x] 3.1 新建 `py/character_card_tools.py`：实现 `get_character_card`、`update_character_card`、`update_user_profile` 三个工具函数 + tool schema
- [x] 3.2 `server.py` `dispatch_tool`：在 `_TOOL_HOOKS` 中注册三个工具；`update_character_card`、`update_user_profile` 加入 `SENSITIVE_TOOLS`
- [x] 3.3 `update_character_card` 可写字段白名单：`soul`、`memoryNotes`、`description`、`personality`、`systemPrompt`、`mesExample`
- [x] 3.4 工具调用后通过 `save_settings()` 持久化 + `ws_manager.broadcast_settings_update()` 通知前端；角色卡启用时自动注册 tool schema 到 tools 列表

## 4. 日记树 FTS 记忆检索

- [x] 4.1 从 lover 分支移植 `py/lover_memory_fts.py`、`py/lover_fts_simple_auto.py` 到 multiLovers
- [x] 4.2 配置项：`memorySettings.memoryDirPath`（日记树根目录，默认空 = `{USER_DATA_DIR}/lover/memory/`）、`memorySettings.memoryIndexSyncMinutes`（默认 10 分钟）
- [x] 4.3 索引白名单：`memoryDirPath` 下递归 `.md`；**不索引** `soul`、`userProfile`、`memoryNotes` 字段内容
- [x] 4.4 分词器优先级：wangfenjin/simple → trigram → unicode61 自动降级
- [x] 4.5 索引同步：`lifespan` 启动时 `sync_memory_index` 一次 + 后台按间隔同步
- [x] 4.6 每轮检索：`search_memory(user_prompt)` → 命中片段注入 `## 相关回忆` 块
- [x] 4.7 校验各平台 libsimple 与 Python 自带 SQLite 兼容性；PyInstaller 打包说明

## 5. 前端 UI

- [ ] 5.1 `static/index.html`：角色卡编辑表单新增 **SOUL / 元层原则** 编辑区域（Markdown textarea）
- [ ] 5.2 `static/index.html`：角色卡编辑表单新增 **记忆笔记** 编辑区域（Markdown textarea）
- [ ] 5.3 `static/index.html`：`memorySettings` 编辑区域新增 **用户档案** 编辑区域（Markdown textarea），标注"所有角色共享"
- [ ] 5.4 `static/index.html`：`memorySettings` 编辑区域新增 **日记树目录** 配置（路径输入框 + 浏览按钮，对应 `memoryDirPath`）和 **FTS 同步间隔** 配置（数字输入，对应 `memoryIndexSyncMinutes`）
- [ ] 5.5 i18n：`static/locales/*.js` 新增 `soul`、`memoryNotes`、`userProfile`、FTS 相关翻译键

## 6. 会话数据模型

- [ ] 6.1 会话表新增字段：`kind: 'main' | 'dev' | 'archive'`、`workspace_path`、`archived_at`、`summary_path`
- [ ] 6.2 启动时确保两个固定分组存在；`kind=main` 在主分组内单例
- [ ] 6.3 后端 API：主会话重置/归档；开发会话创建（可选 workspace_path）/重置/归档（触发摘要回流）；归档会话「拉回主会话」
- [ ] 6.4 `dev` bootstrap 装配：与 `main` 共享角色卡完整注入 + FTS recall；绑定工作区时追加 `.agent/` 概要

## 7. 前端会话 UI

- [ ] 7.1 分组栏收敛为固定「主分组 / 归档分组」；保留用户新建开发会话入口
- [ ] 7.2 主分组：主会话单例置顶 + 「+ 开发会话」按钮
- [ ] 7.3 归档分组：只读浏览 + 「拉回主会话」按钮
- [ ] 7.4 开发会话归档弹窗：Agent 起草摘要 + 目标文件名预填 + 编辑确认

## 8. 会话启动序列

- [ ] 8.1 后端：新建/重置会话时 `is_new_session = True`，在用户消息末尾追加启动指令
- [ ] 8.2 可选注入最近日记摘要（`dailyMemoryDays`=2，`maxTotalChars`=2800）——从日记树中读取最近 N 天修改的 `.md`

## 9. 摘要回流

- [ ] 9.1 开发会话归档时 Agent 起草摘要 → 弹窗确认 → 落盘 `{memoryDirPath}/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`
- [ ] 9.2 落盘后删除会话历史、写入 `summary_path`
- [ ] 9.3 落盘后下一轮 `sync_memory_index` 将摘要纳入 FTS 索引
- [ ] 9.4 起草失败降级：仅含元信息的摘要文件
- [ ] 9.5 `memorySettings.devArchiveQuickSave` 开关（默认 false）

## 10. 文档

- [ ] 10.1 更新 `docs/CHARACTER_CARD.md`：补充 `soul`、`memoryNotes`、`userProfile` 字段说明 + AI 工具说明
- [ ] 10.2 更新 `docs/LOVER_SSOT.md`：与新方案对齐（角色卡扩展 + FTS 日记树 + AI 工具）

## 11. 可选增强（backlog）

- [ ] 11.1 桌面主动感知
- [ ] 11.2 心跳机制（OpenClaw HEARTBEAT）
- [ ] 11.3 角色卡导入/导出适配新字段
- [ ] 11.4 「重建索引」按钮（FTS 索引损坏时手动触发）

## 冒烟测试

- [ ] S.1 新增 soul + memoryNotes 后连续两轮：system prompt 无重复膨胀
- [ ] S.2 userProfile 配置后切换角色卡：用户档案保持不变
- [ ] S.3 老角色卡（无新字段）：行为与现有版本一致
- [ ] S.4 soul / memoryNotes 中 `{{user}}` / `{{char}}` 占位符正确替换
- [ ] S.5 日记树写入 `.md` → sync 后 FTS 命中；专有名词精确匹配
- [ ] S.6 FTS 分词降级：simple 不可用时 trigram/unicode61 正常工作
- [ ] S.7 mem0 默认关闭：未配置 providerId 时不触发向量检索
- [ ] S.8 AI 工具 `get_character_card`：返回当前角色卡字段 + userProfile
- [ ] S.9 AI 工具 `update_character_card`：修改 memoryNotes 后 save_settings 生效；修改 name 被拒绝
- [ ] S.10 自定义日记树路径：配置 `memoryDirPath` 后 FTS 索引切换到新目录
- [ ] S.11 主会话归档与重置；归档会话只读 + 「拉回主会话」可用
- [ ] S.12 开发会话归档弹窗 → 落盘摘要 → FTS 收录 → 对话历史删除
