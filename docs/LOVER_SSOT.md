# Super-Agent-Lover：Markdown SSOT 约定

本文档定义 **lover 分支 / super-agent-lover** 演进中的 **单一真相源（SSOT）** 文件职责、bootstrap 组装顺序，以及与 **记忆 FTS** 的边界。实现以 OpenSpec `openspec/changes/lover-sap-foundation/` 为准。

## 路径根目录

- **「Lover 数据根」（FTS 语料）**：**`USER_DATA_DIR/lover`** — **`MEMORY.md`、`memory/`、`memory_index.sqlite`** 仅在此树下索引与检索（Windows 典型为 `%AppData%\Super-Agent-Party\lover`，可通过自定义数据目录变更）。
- **`CLISettings.cc_path`（工作区）**：**`server.py` → `tools_change_messages`** 当前仍从 **`{cc_path}/.agent/`** 注入 **`MEMORY.md`、`AGENTS.md`**（若存在）；CLI 快捷 **`#`** 亦追加到 **`{cc_path}/.agent/MEMORY.md`**。与 **`lover/`** FTS **路径分离**，后续任务可再统一。
- **日记树（FTS）**：**`lover/memory/`**。
- **产品约定上的 USER / IDENTITY / SOUL**：见下表；**当前后端尚未**从磁盘自动注入这三份（仍以酒馆角色卡等通路为准），与 OpenSpec 完整 bootstrap 对齐属后续实现。

## 文件职责

| 文件 | 职责 | Bootstrap | FTS 索引 |
|------|------|-----------|----------|
| **`USER.md`** | 人类用户档案（事实、偏好、作息等） | ✅ 必选 | ❌ 不索引 |
| **`IDENTITY.md`** | Agent 叙事内身份（外貌、人设、相处方式等） | ✅ **必选，独立文件** | ❌ 不索引 |
| **`SOUL.md`** | 元层运行原则（反机械回复、主动性、记忆维护约定等） | ✅ **必选，独立文件** | ❌ 不索引 |
| **`AGENTS.md`** | 工具 / 协作元指令（非戏内台词） | ✅ 可选；建议有 CLI/工具链时保留 | ❌ 不索引 |
| **`MEMORY.md`** | 长期可复述事实 | ⚙️ 可选是否额外常驻摘要（须与 FTS 白名单一致） | ✅ **必须纳入** FTS |

### IDENTITY 与 SOUL：**不合并**（已定稿）

- **必须**各为 **独立 Markdown 文件**，**不得**合并为单文件两节、**不得**二选一省略其一。
- **`USER.md` 不与人设文件合并**。

## 日记树（用户可见）

- **路径约定（推荐）**：仍可用 `lover/memory/YYYY/MM/…` 分层；**实现上**将 **`lover/memory/` 下任意子目录中的全部 `.md`**（递归）纳入 FTS。
- **设计意图**：路径固定在用户数据目录下，与对话、角色卡同属本机配置树；换工作区不误用另一套记忆。
- **FTS**：上述文件与 **`lover/MEMORY.md`** 同属记忆语料白名单。

## Bootstrap 加载顺序（建议 · 与当前实现的差别）

目标顺序（OpenClaw 对齐）：

1. **`AGENTS.md`**（若存在）→ 2. **`USER.md`** → 3. **`IDENTITY.md`** → 4. **`SOUL.md`** → 5. **`MEMORY.md`**（可选常驻摘要）

**当前代码**：在 **`tools_change_messages`** 中仅在工作区 CLI 启用时注入 **`{cc_path}/.agent/AGENTS.md`**、**`MEMORY.md`**（及待办、技能摘要等）；**未**按上表从 **`lover/`** 批量注入 USER/IDENTITY/SOUL。

原酒馆「设定书」级内容 **并入** 上述人设/bootstrap，**不设**单独关键词按需流水线。

## 记忆 FTS（每轮）

- **时机**：每次用户发送消息后、调用模型前（对齐原长期记忆注入点）。
- **语料白名单**：**`lover/MEMORY.md`** + **`lover/memory/` 下递归的所有 `.md`**。
- **实现（当前代码）**：**SQLite FTS5**，索引库 **`{USER_DATA_DIR}/lover/memory_index.sqlite`**。**`loverSettings`**（目前仅 **同步间隔**）保存在 **`super_agent_party.db`**。界面：**角色设置 → Lover 工作区**。运行时 **自动从 GitHub Releases 下载与本机平台匹配的 [wangfenjin/simple](https://github.com/wangfenjin/simple) zip**（版本号见 `py/lover_fts_simple_auto.py`），解压到 **`lover/_fts5_simple/<tag>/`**；与 Python 自带 SQLite **ABI 不兼容**则加载失败并退回 **trigram**。**更换分词器须删除 `memory_index.sqlite` 后重启**。**索引更新**：**启动时** `sync_memory_index` 一次 + 后台按间隔同步；对话仍只 **`search_memory`**。**不**使用 mem0；**不**自动把模型回复写回 Markdown。
- **排除**：`USER.md`、`IDENTITY.md`、`SOUL.md`、`AGENTS.md` **不进入** FTS 索引。

检索结果以「【相关回忆】」等与 **人设 bootstrap 分区隔离** 的形式注入。

## 与上游 Super Agent Party 的差异（产品层）

- **无 `loverMode`**：lover 为单一产品路径，不保留酒馆双轨 UI。
- **详细设计与任务**：见 `openspec/changes/lover-sap-foundation/`。

## 品牌与仓库

- 计划将 **`super-agent-party`** 更名为 **`super-agent-lover`**（与发布节奏同步）。
