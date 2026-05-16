## 1. 范围与 SSOT 清单

- [x] 1.1 README：固定 **USER 独立**；**IDENTITY.md** 与 **SOUL.md** **必须分文件、不合并**；**AGENTS** 可选；记忆仅 FTS（**`USER_DATA_DIR/lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**）；bootstrap **加载顺序**（见 **`docs/LOVER_SSOT.md`**）
- [x] 1.2 删除仓库内对已移除变更 `workspace-memory-diary` 的残余引用

## 2. 记忆 FTS（仅记忆语料）

- [x] 2.1 SQLite FTS5：`py/lover_memory_fts.py`；内置 **trigram** / **unicode61** 降级；优先 **[wangfenjin/simple](https://github.com/wangfenjin/simple)**（`py/lover_fts_simple_auto.py` 自动下载）
- [x] 2.2 索引白名单：**`lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**；根目录 = **`USER_DATA_DIR/lover`**
- [x] 2.3 每轮 **`search_memory()`** 注入 Dynamic 块 `## Memory Recall (FTS)`
- [x] 2.4 **已移除 mem0**
- [x] 2.5 **定时 sync**：`lifespan` 启动 + 后台循环；间隔 `loverSettings.memoryIndexSyncIntervalMinutes`（默认 10 分钟）
- [ ] 2.6 校验各平台 **libsimple** 与 Python 自带 SQLite 兼容性；PyInstaller 打包说明；可选「重建索引」按钮

## 3. System Prompt 拼装

- [x] 3.1 新建 `py/lover_bootstrap.py`，实现 `build_lover_system_prompt()`：
  - Stable 块：`# Project Context` → AGENTS（可选）→ USER → IDENTITY → SOUL → MEMORY 摘要（可选）→ `<!-- LOVER_PROMPT_CACHE_BOUNDARY -->`
  - Dynamic 块：`## Memory Recall` → `## Workspace`（cc_path 有效时，含 .agent/AGENTS.md / todos / skills）→ `## Runtime`（时间 / kind / workspace_path）→ TTS / VRM 等通用工具提示
- [x] 3.2 替换 `tools_change_messages` 中 `cur_memory` 整块注入及现有 MEMORY.md / AGENTS.md / skills 零散 `content_append`，统一走 `build_lover_system_prompt()`
- [x] 3.3 **删除**酒馆 `cur_memory` 大块注入（description / personality / mesExample / systemPrompt / characterBook）
- [x] 3.4 上下文压缩保护 stable 块（不截断人设文件）

## 4. 会话数据模型（原第 6 节，前端功能依赖此后端基础）

> 5.3-5.5 的前端 UI 已就绪，但 `kind`、`workspace_path`、归档落盘等实际逻辑需要本节后端支持才能端到端验证。

- [ ] 4.1 会话表新增字段：`kind: 'main' | 'dev' | 'archive'`、`workspace_path`、`archived_at`、`summary_path`（沿用既有 schema）
- [ ] 4.2 启动时确保两个固定分组存在；`kind=main` 在主分组内单例
- [ ] 4.3 后端 API：主会话重置 / 归档；开发会话创建（可选 workspace_path）/ 重置 / 归档（触发摘要回流）；归档会话「拉回主会话」
- [ ] 4.4 `dev` bootstrap 装配：强制 lover/AGENTS.md + 人设三件套 + 绑定工作区的 `.agent/` 概要；`workspace_path` 失效时优雅降级
- [ ] 4.5 写入隔离：`dev` 会话拒绝写 USER / IDENTITY / SOUL / lover/AGENTS.md / lover/MEMORY.md / lover/memory/
- [ ] 4.6 摘要回流落盘：`lover/memory/YYYY/MM/<YYYY-MM-DD>-work-<slug>.md`；落盘后删除 `dev` 对话历史并写回 `summary_path`；起草失败时降级为仅含元信息的摘要文件

## 5. 前端与酒馆移除

- [x] 5.1 移除角色卡、换卡、酒馆主导航及相关设置
- [x] 5.2 分组栏收敛为固定「主分组 / 归档分组」；移除用户新建/删除/重命名分组入口
- [x] 5.3 主分组：主会话单例置顶 + 「+ 开发会话」按钮（可选绑定 `cc_path`）；主会话支持归档 / 重置
- [x] 5.4 归档分组：只读浏览；「拉回主会话」按钮（将所选段落追加到主会话上下文，不动原件）
- [x] 5.5 开发会话归档弹窗：展示 Agent 起草摘要 + 目标文件名预填 + 编辑确认；支持 `loverSettings.devArchiveQuickSave` 跳过弹窗
- [ ] 5.6 人设语音页重做：移除多音色 `newtts` 网格与「添加」入口；将主 TTS 配置（`ttsSettings` 引擎/音色/参数）直接内联展示到「角色语音」子页面，仅支持单一音色
- [ ] 5.7 人设形象页重做：移除多形象 `newVRM` 网格与「添加」入口；改为直接展示并可编辑主 VRMConfig（模型选择、尺寸、动作）+ 启动/关闭形象窗口按钮，仅支持单一形象（默认 alice）

## 6. 分叉与文档

- [ ] 6.1 README：lover 定位、SSOT（`USER_DATA_DIR/lover`）、FTS 仅记忆、更名 super-agent-lover、上游合并策略

## 收尾检查项（lover 完工前逐项确认）

- [ ] `server.py`：删除酒馆式 **`cur_memory`** 大块注入（description / personality / mesExample / systemPrompt 等）
- [ ] `server.py`：删除 **`characterBook`** 关键词按需注入
- [ ] `server.py` / 设置：**`memoryId` / `selectedMemory`** 酒馆向量记忆链路废弃后裁剪；清理 **`MEMORY_CACHE_DIR`** 下不再使用的 faiss 数据
- [ ] 前端：角色卡、换卡、酒馆主导航；设置中与 **mem0 / embedding** 相关且已废弃的项
- [ ] 文档：README 酒馆能力与 lover 描述分叉清理
- [ ] 用户数据：若仍存在早期 **`.agent/lover_memory_fts.sqlite`**，提示删除（当前索引仅为 **`memory_index.sqlite`**）
- [ ] **会话启动序列（原第 4 节）**：新建对话时 AI 自动问候 + 注入近期日记前言。待确认触发机制（前端新建时自动发空消息？还是其他方案）后再设计实现。

## 7. 冒烟

- [ ] 7.1 连续两轮：stable 块无重复膨胀；FTS 仅记忆命中
- [ ] 7.2 专有名词进 MEMORY 或当日日记 → FTS 命中；simple / 内置 tokenizer 降级可接受
- [ ] 7.3 新会话 / 重置：启动指令触发问候；带近期日记时 AI 能感知近况
- [ ] 7.4 主会话归档与重置；归档会话只读 + 「拉回主会话」可用
- [ ] 7.5 开发会话：创建（带 / 不带 workspace_path）→ 归档弹窗 → 落 `lover/memory/YYYY/MM/...-work-<slug>.md` → 对话历史被删除 → 下一轮 sync 后主会话 FTS 能召回该摘要
- [ ] 7.6 开发会话写入隔离；workspace_path 失效时仍可对话
