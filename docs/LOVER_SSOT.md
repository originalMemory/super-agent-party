# Super-Agent-Lover：工作区 Markdown SSOT 约定

本文档定义 **lover 分支 / super-agent-lover** 演进中的 **单一真相源（SSOT）** 文件职责、bootstrap 组装顺序，以及与 **记忆 FTS** 的边界。实现以 OpenSpec `openspec/changes/lover-sap-foundation/` 为准。

## 路径根目录

- 默认相对 **CLI 工作目录**（设置中的项目根 / `cwd`）下的 **`.agent/`**。
- 若实现选择「工作区根并列 `.agent`」以外的布局，须在代码与本文同步更新。

## 文件职责

| 文件 | 职责 | Bootstrap | FTS 索引 |
|------|------|-----------|----------|
| **`USER.md`** | 人类用户档案（事实、偏好、作息等） | ✅ 必选 | ❌ 不索引 |
| **`IDENTITY.md`** | Agent 叙事内身份（外貌、人设、相处方式等） | ✅ 与下栏二选一或并存 | ❌ 不索引 |
| **`SOUL.md`** | 元层运行原则（反机械回复、主动性、记忆维护约定等） | ✅ 与 IDENTITY **可同时存在**；亦可合并进单一文件两节 | ❌ 不索引 |
| **`AGENTS.md`** | 工具 / 协作元指令（非戏内台词） | ✅ 可选；建议有 CLI/工具链时保留 | ❌ 不索引 |
| **`MEMORY.md`** | 长期可复述事实 | ⚙️ 可选是否额外常驻摘要（须与 FTS 白名单一致） | ✅ **必须纳入** FTS |

### IDENTITY 与 SOUL：要不要合并？

- **推荐**：两文件并存（与常见 OpenClaw 工作区一致），分层清晰。
- **若要减少文件**：合并为 **`IDENTITY.md`（或 `CHARACTER.md`）** 内两大节：`## 角色与叙事`、`## 原则与运行方式`，并删除独立 `SOUL.md`，避免重复注入。
- **`USER.md` 不建议与上述任一方合并**，以免用户档案与伴侣人设混编。

## Bootstrap 加载顺序（建议）

会话锚点 **一次性注入**（会话级固定，不随每条用户消息倍增）：

1. **`AGENTS.md`**（若存在）
2. **`USER.md`**
3. **`IDENTITY.md`**（若采用合并方案，则含原 SOUL 章节）
4. **`SOUL.md`**（若仍为独立文件且存在）
5. **`MEMORY.md`**（**若**产品约定「常驻摘要」则在此插入；否则仅靠 FTS 片段）

原酒馆「设定书」级内容 **并入** 上述人设/bootstrap，**不设**单独关键词按需流水线。

## 记忆 FTS（每轮）

- **时机**：每次用户发送消息后、调用模型前（对齐原长期记忆注入点）。
- **语料白名单**：至少 **`MEMORY.md`**、**按日落盘日记**（路径以实现为准，例如 `.agent/memory/daily/YYYY-MM-DD.md`）。
- **分词器**：倾向 [wangfenjin/simple](https://github.com/wangfenjin/simple)（`tokenize='simple'`）。
- **排除**：`USER.md`、`IDENTITY.md`、`SOUL.md`、`AGENTS.md` **默认不进入** FTS 索引。

检索结果以「相关回忆」等与 **人设 bootstrap 分区隔离** 的形式注入。

## 与上游 Super Agent Party 的差异（产品层）

- **无 `loverMode`**：lover 为单一产品路径，不保留酒馆双轨 UI。
- **详细设计与任务**：见 `openspec/changes/lover-sap-foundation/`。

## 品牌与仓库

- 计划将 **`super-agent-party`** 更名为 **`super-agent-lover`**（与发布节奏同步）。
