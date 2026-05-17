# 角色卡（酒馆角色卡）说明

本文档说明 Super Agent Party **当前 main 分支**上「角色卡」「多角色语音」「多角色外观」三者的关系、存储位置，以及每次对话时如何拼进模型上下文。实现以 `server.py`、`static/js/vue_methods.js` 为准。

## 三者分别做什么

| 模块 | 配置键 | 作用 |
|------|--------|------|
| **角色卡** | `memories[]` + `memorySettings` | 人设、系统提示、世界书、开场白；可选 **mem0 向量长期记忆** |
| **多角色语音** | `ttsSettings.newtts` | 按「音色名」配置 TTS；模型输出 `<音色名>…</音色名>` 时路由到对应引擎 |
| **多角色外观** | `VRMConfig.newVRM` | 按「形象名」配置桌宠 VRM 模型、动作、窗口大小 |

三者是**独立配置**，通过**同名约定**串联，没有数据库外键或自动联动。

## 存储位置

### 角色卡元数据

- 保存在 **`super_agent_party.db`** 的 `settings` 表（JSON 整包），字段：
  - `memories[]`：所有角色卡
  - `memorySettings`：是否启用、当前选中 `selectedMemory`、默认用户名、`genericSystemPrompt`、`memoryLimit` 等
- 读写：`py/get_setting.py` 的 `load_settings` / `save_settings`
- 前端保存：WebSocket `save_settings`，payload 含 `memories`、`memorySettings`（见 `vue_methods.js` `autoSaveSettings`）

代码里虽有 `USER_DATA_DIR/settings.json` 常量，**运行时以 SQLite 为准**。

### 长期记忆向量库

- 路径：`{USER_DATA_DIR}/memory_cache/{角色卡 id}/`
- 条件：角色卡配置了 embedding 的 `providerId`、`model`、`api_key`、`base_url`
- 实现：mem0 + FAISS（`generate_stream_response` 内 `Memory.from_config`）
- 删除角色卡：调用 `/remove_memory` 会删掉对应 `memory_cache` 目录

### 对话历史中的开场白

- `firstMes`、`alternateGreetings` 不写入 system，而在前端 `changeMemory` / `randomGreetings` 时插入 **`messages` 里一条 `assistant` 消息**（替换 `{{user}}` / `{{char}}`），随会话保存在 `conversations.db`

### 单张角色卡字段（`memories[]` 一项）

| 字段 | 用途 | 注入方式 |
|------|------|----------|
| `name` | 显示名；与语音/形象**同名**时才能联动 | 替换 `{{char}}`；TTS 标签名 |
| `description` | 角色设定 | 每轮 system 追加 |
| `personality` | 性格 | 每轮 system 追加 |
| `systemPrompt` | 额外系统提示 | 每轮 system 追加 |
| `mesExample` | 对话示例 | 每轮 system 追加 |
| `characterBook` | 世界书（关键词 + 内容） | 关键词命中时 system 追加 |
| `firstMes` / `alternateGreetings` | 开场白 | 前端写入对话历史 |
| `avatar` | 头像 URL |  mainly UI（如 `getRoleAvatar`），**不**自动进 prompt |
| `providerId` + embedding 相关 | 长期记忆 | 检索/写入 mem0 |
| `infer` | 是否自动提炼记忆 | 控制 `m0.add(..., infer=)` |

导入/导出：支持 SillyTavern 风格 `*_v3.json`；导入后仍进入 `memories[]`。

## 与多角色语音、多角色外观的关系

### 为什么创建角色卡后，下拉里会出现角色名？

在「多角色语音 / 多角色外观」**新增**时，名称下拉框会列出已有角色卡名称（及「旁白 / Narrator」），方便起**同名**配置：

- `static/index.html`：`el-option v-for="memory in memories"`

**仅作选项，不会自动创建**语音或形象条目；删除角色卡也**不会**删除已配置的 `newtts` / `newVRM`。

### 选角色卡后，语音会自动用同名音色吗？

需同时满足：

1. 对话里 **启用角色卡** 且选中该角色（`memorySettings.is_memory` + `selectedMemory`）
2. **开启 TTS**
3. 「多角色语音」中存在**同名**且 **enabled** 的 `ttsSettings.newtts[角色名]`

满足时，`tools_change_messages` 会把角色名加入可用音色列表，并 instruct 模型用 `<角色名>…</角色名>` 包裹该角色台词（`server.py` 约 2475–2524 行）。前端 `splitTTSBuffer` 按标签从 `newtts` 取配置合成。

仅选角色卡、未配同名语音 → **不会**自动换音色。

### 选角色卡后，桌宠会自动换形象吗？

**不会。** 多角色外观需在各形象卡片上 **手动点播放**（`startNewVRM(name)`）。对话里选角色卡不改变 `VRMConfig.name`。

### 对话页「桌宠」按钮

调用 `startVRM()`，在 Electron 下固定设 `VRMConfig.name = 'default'`，使用 **桌宠机器人** 页的全局模型/动作（`selectedModelId`、`selectedMotionIds`），**不是** `newVRM[角色名]`。

浏览器下仅打开 `vrm.html`，读当前已保存配置（若上次用过多角色形象启动，可能仍是上次形象）。

## 何时、如何拼给 AI

### 前置条件

- `memorySettings.is_memory === true`
- `memorySettings.selectedMemory` 为有效角色 id
- 非子 agent 请求（`request.is_sub_agent` 为 false 时完整注入）

### 时间线（每次 `POST /v1/chat/completions`）

```
前端 sendMessage
  → messages（含历史、开场白 assistant 条）+ fileLinks
  → chat_endpoint：若有全局 system_prompt，prepend 到 messages[0]
  → generate_stream_response：
       ① 角色卡字段 + 长期记忆检索 → content_append 到 system
       ② tools_change_messages（TTS 说明、工具、视觉等）
       ③ 知识库 / 联网等（流式路径内继续追加）
  → 调用模型
  → 流式结束后：若 m0 已初始化，后台 m0.add 更新长期记忆
```

### 服务端注入顺序（`generate_stream_response`，`tools_change_messages` 之前）

均 `content_append` 到 **`messages[0]` 的 system**（与第一条 system 合并），且替换 `{{user}}` → `memorySettings.userName`、`{{char}}` → 角色 `name`：

| 顺序 | 内容 | 条件 |
|------|------|------|
| 1 | 默认用户名说明 | 配置了 `userName` |
| 2 | 世界观设定 | `characterBook` 任一关键词出现在**本条 user** 或**上一条 assistant** |
| 3 | 角色设定 | `description` 非空 |
| 4 | 性格设定 | `personality` 非空 |
| 5 | 对话示例 | `mesExample` 非空 |
| 6 | 角色 `systemPrompt` | 非空 |
| 7 | `memorySettings.genericSystemPrompt` | 非空 |
| 8 | 之前的相关记忆 | 角色卡配了 `providerId`，`m0.search(user_prompt)`，条数 `memoryLimit` |

实现位置：`server.py` 约 3629–3711 行。

### `tools_change_messages` 中与角色卡相关的部分

- 群聊：`isGroupMode` 时注入「你在扮演 {selectedMemoryName}」
- TTS + 角色卡：注入音色 XML 标签规范（见上文）

其余为 CLI、技能、公式、视觉、工具列表等，同样追加到 system。

### 请求结束后

- 若 mem0 已启用：用本轮「用户话 + 模型完整回复」调用 `m0.add`；`infer` 控制是否自动提炼
- **不会**因选角色卡而改桌宠或自动创建语音配置

## 推荐配置流程（三者一致）

1. 创建角色卡（例如「小樱」）
2. **多角色语音**：新增名为 **小樱** 的条目，配置引擎/音色并 **开启**
3. **多角色外观**：新增名为 **小樱** 的条目，选 VRM 模型/动作；需要时 **手动启动** 桌宠
4. 对话中 **启用角色卡** 并选中「小樱」
5. 桌宠若用对话页按钮：在 **工具 → 桌宠机器人** 改默认模型（与多角色形象无关）

## 与 lover / multiLovers 分支的边界

- 本文描述 **SAP 通用角色卡（memories）** 通路。
- **lover** 分支另有 `lover/` 目录、FTS、`USER.md` / `IDENTITY.md` 等 SSOT，见 `docs/LOVER_SSOT.md`；与酒馆角色卡 **路径分离**，后续 multiLovers 可能演进多角色方案，以 OpenSpec 为准。

## 相关代码索引

| 主题 | 位置 |
|------|------|
| 角色卡 CRUD | `static/js/vue_methods.js`：`addMemory`、`changeMemory`、`removeMemory` |
| 发请求 | `sendMessage` → `/v1/chat/completions` |
| 注入逻辑 | `server.py`：`generate_stream_response`、`tools_change_messages` |
| TTS 标签解析 | `static/js/vue_methods.js`：`splitTTSBuffer` |
| 桌宠默认启动 | `startVRM`；多角色 `startNewVRM` |
| 配置模板 | `config/settings_template.json`：`memories`、`memorySettings` |
