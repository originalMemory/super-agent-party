## Why

在 **硬分叉** 的 **lover** 产品线上，基于 Super Agent Party 的工程底座，收敛为 **单用户 ↔ 唯一 Agent** 的伴侣型宿主：人设与工作区纪律以 **`.agent/` Markdown SSOT** 为准，**移除酒馆角色卡 / 多卡 / 旧 UI**。  
人设采用 **OpenClaw 式会话常驻 bootstrap**：**`USER.md`、`IDENTITY.md`、`SOUL.md`（或合并后的等价结构）与可选 `AGENTS.md` 在会话锚点一并注入**；原酒馆「设定书」类内容 **并入这套初始角色信息**，**不设**关键词触发或单独按需拼装。**每轮 FTS 仅用于记忆语料**（`MEMORY.md`、按日日记等）。长期记忆以 **SQLite FTS5 + [wangfenjin/simple](https://github.com/wangfenjin/simple)** 为主；mem0 可选。

**品牌与仓库命名**：后续对外将由 **super-agent-party** 更名为 **super-agent-lover**。文中「SAP」「上游」仍指原 super-agent-party 主线。

## What Changes（分阶段）

### 阶段 A — 范围与设计定型

- 固化 **USER / IDENTITY / SOUL 合并策略**（见 `design.md`）、bootstrap 顺序、**FTS 仅记忆**、主会话+归档。

### 阶段 B — 记忆后端

- FTS 索引 **仅限**记忆类 Markdown；每轮用户消息后、模型调用前注入回忆片段。
- **可选 mem0**：唯一 Agent id。

### 阶段 C — 前端与会话

- 主会话、归档、主动归档、重置；移除酒馆换卡与相关导航。

### 阶段 D — SSOT bootstrap

- 按文档顺序加载 `AGENTS`（可选）→ `USER` → `IDENTITY` / `SOUL`（或合并文件）；**禁止**每轮重复追加酒馆整块人设；**禁止**单独设定书流水线。
- **`MEMORY.md`**：可作为常驻摘要纳入 bootstrap **或** 仅靠 FTS 片段注入（二选一须文档化并与 FTS 白名单一致）。

### 阶段 E — backlog

- 桌面主动感知等。

### 阶段 F — 可选升级

- QMD / 向量混合。

## Capabilities

### New Capabilities

- `lover`：单一产品：SSOT 完整初始角色 bootstrap、记忆 FTS、主会话+归档、移除酒馆 UI。

### Modified Capabilities

- （无）

## Impact

- **后端**：移除酒馆每轮人设注入；实现 SSOT 拼接；记忆 FTS；无设定书关键词分支。
- **前端**：裁剪酒馆/角色卡界面。
- **分叉**：独立 lover；可合并上游 SAP（见 `design.md`）。
