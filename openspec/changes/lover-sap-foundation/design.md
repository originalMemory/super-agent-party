## 目标陈述（已定稿方向）

**lover** 为自 SAP **硬分叉**的独立产品线：**唯一代码路径**，**无 `loverMode`**，**不保留**酒馆式旧页面与并行逻辑。单一用户与 **唯一 Agent**；人设与记忆 Markdown 来自 **`USER_DATA_DIR/lover/`**（与 **`CLISettings.cc_path`** 解耦）。  
人设注入：**会话常驻一份 bootstrap**：**用户档案 + 完整初始角色信息**；**`IDENTITY.md` 与 `SOUL.md` 必须分文件、不合并**（见下）。**每轮 FTS 仅检索「记忆」Markdown**（`lover/MEMORY.md` 与 **`lover/memory/` 下递归的全部 `.md`**；推荐 **`lover/memory/YYYY/MM/<日记>.md`**，**不**做强日历校验）。**不得**索引人设文件。实现为 **SQLite FTS5**：索引 **`{USER_DATA_DIR}/lover/memory_index.sqlite`**；**`loverSettings`**（默认同步 **10 分钟**）；**simple** 扩展由实现 **自动下载/缓存**（失败则 **trigram** → **unicode61**）。**不使用 mem0**。  
会话形态：**主会话 + 归档**，支持 **主动归档** 与 **重置会话**。

**品牌与仓库命名**：后续对外将 **super-agent-party** 更名为 **super-agent-lover**（仓库名、包名、文档标题等与发布节奏对齐）。

---

## OpenClaw 对齐：`USER` / `IDENTITY` / `SOUL` / 日记

| 文件 / 路径 | 承担 | lover 定稿 |
|-------------|------|------------|
| **`USER.md`** | 人类用户档案 | **独立文件**；bootstrap；不进 FTS；不与 IDENTITY/SOUL 合并 |
| **`IDENTITY.md`** | Agent 叙事内身份 | **独立文件**；bootstrap；**不与 SOUL 合并** |
| **`SOUL.md`** | 元层运行原则 | **独立文件**；bootstrap；**不与 IDENTITY 合并** |
| **`AGENTS.md`** | 工具/协作元指令 | 可选；bootstrap 靠前 |
| **`MEMORY.md`** | 长期事实 | FTS；可选摘要进 bootstrap |
| **`lover/memory/**/*.md`** | 日记树 | **用户可见**；推荐 `YYYY/MM/`；`lover/memory/` 下任意 `.md`（递归）均 FTS |

**Bootstrap 注入顺序**：`AGENTS`（若有）→ `USER` → `IDENTITY` → `SOUL` →（可选 `MEMORY` 摘要）。**不得**再走设定书关键词流水线。

---

## 设计原则

1. **单一产品**：无模式开关；移除酒馆 UI 与角色卡主导航。
2. **Markdown SSOT**：bootstrap 集合与加载顺序固定并文档化。
3. **人设 vs 记忆**：完整初始角色信息在 **会话锚点一次性注入**；**仅记忆语料**（含根备忘与按日日记树）走 **每轮 FTS**。
4. **记忆**：仅 FTS5 + 用户维护的 Markdown；无向量记忆栈。
5. **主会话 + 归档**。
6. **分叉与上游**：择优合并 SAP。

---

## MVP 边界

### 纳入

- SSOT bootstrap：**USER + IDENTITY + SOUL** 三分文件；可选 AGENTS。
- **记忆 FTS** + 每轮注入；索引 **`lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**。
- 主会话、归档、主动归档、重置。
- 移除酒馆路径。

### 首期非目标

- OpenClaw 同款 QMD。
- 完整桌面主动感知（backlog）。

### 记忆索引范围

**`lover/MEMORY.md`** + **`lover/memory/`** 下递归的 `.md`。**不得**将 USER / IDENTITY / SOUL / AGENTS 纳入默认 FTS。

---

## 架构触点

| 区域 | 触点 |
|------|------|
| 配置 | **`USER_DATA_DIR/lover`** = 人设 + 记忆 Markdown + FTS 索引根；**`cc_path`** = 工作区（任务 / `.agent` 待办 / 项目 skills） |
| 后端 | SSOT 从 `lover/` 拼接 bootstrap、记忆 FTS、可监视 `lover/memory/`、移除 `cur_memory` 每轮注入 |
| 前端 | 主会话/归档/重置 |

---

## 已决议清单

1. **人设**：USER、IDENTITY、SOUL **三分文件，IDENTITY 与 SOUL 不合并**；无单独设定书流水线。
2. **日记**：推荐 `lover/memory/YYYY/MM/<文件>.md`，实现收录 `lover/memory/` 下任意 `.md`（递归），对用户可见。
3. **会话**：主会话 + 归档 + 主动归档 + 重置。
4. **`lover/`**：位于 **`USER_DATA_DIR`**；人设与日记树、**`memory_index.sqlite`** 均在此树下。**`cc_path`** 仅工作区能力。
5. **品牌**：lover。
6. **无 loverMode**。

---

## Git 与分支策略（建议）

- **`origin`**：super-agent-lover；**`upstream`**：super-agent-party。

---

## 风险

- **上游合并**：删除 UI 后 diff 大。
- **重置语义**：区分对话上下文 vs 持久记忆存储。
