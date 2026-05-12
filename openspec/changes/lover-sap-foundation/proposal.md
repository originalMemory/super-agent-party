## Why

在 **硬分叉** 的 **lover** 产品线上，基于 Super Agent Party 的工程底座，收敛为 **单用户 ↔ 唯一 Agent** 的伴侣型宿主：人设与记忆 Markdown 以 **`USER_DATA_DIR/lover/`** 为 SSOT（**与 `CLISettings.cc_path` 无关**）；工作区 `.agent/` 仍可用于任务、待办、项目 skills 等。**移除酒馆角色卡 / 多卡 / 旧 UI**。  
人设采用 **OpenClaw 式会话常驻 bootstrap**：**`USER.md`、`IDENTITY.md`、`SOUL.md` 必须为三份独立文件（IDENTITY 与 SOUL 不合并）**，可选 **`AGENTS.md`** 一并注入；原酒馆「设定书」类内容 **并入初始角色信息**，**不设**关键词按需拼装。**每轮 FTS 仅用于记忆语料**：**`lover/MEMORY.md`** 与 **`lover/memory/` 下递归的 `.md`**（推荐 `YYYY/MM` 布局；对用户 **可见、可手改**）。长期记忆 **仅 SQLite FTS5**；**`loverSettings`**（默认同步 **10 分钟**）；**simple** 分词扩展 **自动获取**（见实现）。**已移除 mem0**。

**品牌与仓库命名**：后续对外将由 **super-agent-party** 更名为 **super-agent-lover**。文中「SAP」「上游」仍指原 super-agent-party 主线。

## What Changes（分阶段）

### 阶段 A — 范围与设计定型

- 固化 **USER / IDENTITY / SOUL 三分文件（不合并）**、**日记树 `lover/memory/**/*.md`（推荐按年月）**、bootstrap 顺序、**FTS 仅记忆**、**主分组（main 单例 + 多 dev）+ 归档分组（仅 main 快照）** 的两组固定结构。

### 阶段 B — 记忆后端

- FTS 索引 **`lover/MEMORY.md`** + **`lover/memory/`** 下按日文件；每轮用户消息后、模型调用前注入回忆片段。
- **无 mem0**：不向向量库自动写入对话摘要。

### 阶段 C — 前端与会话

#### C1 — 主会话 / 归档 / 重置

- 主会话单例、归档分组只读、主动归档、重置；移除酒馆换卡与相关导航；归档主会话提供「拉回主会话」按钮。

#### C2 — 开发会话与摘要回流

- 主分组内可多开 `dev` 会话，可选绑定一个 `cc_path` 工作区；与主会话**共享人设 bootstrap**，额外强制注入 `AGENTS.md` + 工作区 `.agent/` 概要。
- 自身对话**不入 FTS**；归档时由 Agent 起草摘要 → 默认弹窗确认 → 落 `lover/memory/YYYY/MM/<日期>-work-<slug>.md` → 删除原对话历史。
- 提供 `loverSettings.devArchiveQuickSave`（默认关）跳过弹窗的快速保存开关。
- 摘要起草失败时降级为元信息摘要（任务标题、绑定工作区、起止时间），仍保留 FTS 痕迹。

### 阶段 D — SSOT bootstrap

- 按文档顺序加载 `AGENTS`（可选）→ `USER` → `IDENTITY` → `SOUL`；**禁止**每轮重复追加酒馆整块人设；**禁止**单独设定书流水线。
- **`MEMORY.md`**：可作为常驻摘要纳入 bootstrap **或** 仅靠 FTS 片段注入（二选一须文档化并与 FTS 白名单一致）。
- `dev` 会话装配相同人设三件套 + 强制 `AGENTS`，绑定工作区时追加 `.agent/` 概要 / 项目 skills 索引；**不得**写入 `MEMORY.md` 或人设三件套。

### 阶段 E — backlog

- 桌面主动感知等。

### 阶段 F — 可选升级

- QMD / 向量混合。

## Capabilities

### New Capabilities

- `lover`：单一产品：SSOT 三分人设文件、可见日记树、记忆 FTS、主会话+归档、移除酒馆 UI。

### Modified Capabilities

- （无）

## Impact

- **后端**：移除酒馆每轮人设注入；SSOT 拼接；FTS 监视 `memory/`；无设定书关键词分支；新增 `dev` 会话 bootstrap 装配（强制 AGENTS + 可选工作区概要）与摘要回流写入路径。
- **前端**：裁剪酒馆/角色卡界面；分组栏收敛为固定的「主分组 / 归档分组」；主会话单例 + 多个 `dev` 会话；归档主会话只读 + 「拉回主会话」；`dev` 归档弹窗确认摘要。
- **数据模型**：会话表新增 `kind` / `workspace_path` / `archived_at` / `summary_path`；分组用户不可增删。
- **设置**：新增 `loverSettings.devArchiveQuickSave`（默认 `false`）。
- **分叉**：独立 lover；可合并上游 SAP（见 `design.md`）。
