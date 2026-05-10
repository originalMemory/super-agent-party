## Why

在 **硬分叉** 的 **lover** 产品线上，基于 Super Agent Party 的工程底座，收敛为 **单用户 ↔ 唯一 Agent** 的伴侣型宿主：人设与记忆 Markdown 以 **`USER_DATA_DIR/lover/`** 为 SSOT（**与 `CLISettings.cc_path` 无关**）；工作区 `.agent/` 仍可用于任务、待办、项目 skills 等。**移除酒馆角色卡 / 多卡 / 旧 UI**。  
人设采用 **OpenClaw 式会话常驻 bootstrap**：**`USER.md`、`IDENTITY.md`、`SOUL.md` 必须为三份独立文件（IDENTITY 与 SOUL 不合并）**，可选 **`AGENTS.md`** 一并注入；原酒馆「设定书」类内容 **并入初始角色信息**，**不设**关键词按需拼装。**每轮 FTS 仅用于记忆语料**：**`lover/MEMORY.md`** 与 **`lover/memory/` 下递归的 `.md`**（推荐 `YYYY/MM` 布局；对用户 **可见、可手改**）。长期记忆 **仅 SQLite FTS5**；**`loverSettings`**（默认同步 **10 分钟**）；**simple** 分词扩展 **自动获取**（见实现）。**已移除 mem0**。

**品牌与仓库命名**：后续对外将由 **super-agent-party** 更名为 **super-agent-lover**。文中「SAP」「上游」仍指原 super-agent-party 主线。

## What Changes（分阶段）

### 阶段 A — 范围与设计定型

- 固化 **USER / IDENTITY / SOUL 三分文件（不合并）**、**日记树 `lover/memory/**/*.md`（推荐按年月）**、bootstrap 顺序、**FTS 仅记忆**、主会话+归档。

### 阶段 B — 记忆后端

- FTS 索引 **`lover/MEMORY.md`** + **`lover/memory/`** 下按日文件；每轮用户消息后、模型调用前注入回忆片段。
- **无 mem0**：不向向量库自动写入对话摘要。

### 阶段 C — 前端与会话

- 主会话、归档、主动归档、重置；移除酒馆换卡与相关导航。

### 阶段 D — SSOT bootstrap

- 按文档顺序加载 `AGENTS`（可选）→ `USER` → `IDENTITY` → `SOUL`；**禁止**每轮重复追加酒馆整块人设；**禁止**单独设定书流水线。
- **`MEMORY.md`**：可作为常驻摘要纳入 bootstrap **或** 仅靠 FTS 片段注入（二选一须文档化并与 FTS 白名单一致）。

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

- **后端**：移除酒馆每轮人设注入；SSOT 拼接；FTS 监视 `memory/`；无设定书关键词分支。
- **前端**：裁剪酒馆/角色卡界面。
- **分叉**：独立 lover；可合并上游 SAP（见 `design.md`）。
