# OpenClaw 新会话自动回复机制

## 概述

当用户在 OpenClaw 中创建新会话（通过 `/new` 命令或首次消息），系统会自动生成一条 AI 的欢迎回复。这不是通过预定义的模板实现的，而是通过**在后台注入特殊的系统提示词**，告诉 Claude 这是一个新会话启动，需要执行启动序列。

**关键机制**：系统自动在用户输入中注入提示词 → Claude 读取工作区文件 → Claude 自动生成欢迎消息。

---

## 执行流程

### 完整的调用链

```
用户创建新会话（/new 命令或首次消息）
  ↓
dispatchInboundMessage()
  【src/auto-reply/dispatch.ts】
  ↓
gateway/server-methods/agent.ts:946-949
  检测 isNewSession
  ↓
session-reset-prompt.ts:60-93
  调用 resolveBareSessionResetPromptState()
  生成会话重置提示词 (BARE_SESSION_RESET_PROMPT_*)
  ↓
startup-context.ts:17-30
  判断 shouldApplyStartupContext()
  是否加载每日启动记忆
  ↓
get-reply-run.ts:585-648
  组装最终提示词
  ↓
Claude 自动生成欢迎消息
```

---

## 关键概念

### 1. 新会话检测

**源代码**：`src/gateway/server-methods/agent.ts:946-949`

```typescript
isNewSession =
  !entry ||
  (!canReuseSession && !usableRequestedSessionId) ||
  Boolean(usableRequestedSessionId && entry?.sessionId !== usableRequestedSessionId);
```

新会话的判断条件：
- 不存在会话记录（`!entry`）
- 会话不可重用且没有指定的会话 ID
- 指定了新的会话 ID（与当前会话不同）

### 2. 会话重置提示词

**源代码**：`src/auto-reply/reply/session-reset-prompt.ts`

当检测到新会话时，系统会生成一个特殊的提示词注入到系统中。有 3 种变体取决于 bootstrap 状态：

#### 变体 1：基础新会话提示 (行 11-12)

```typescript
const BARE_SESSION_RESET_PROMPT_BASE =
  "A new session was started via /new or /reset. Execute your Session Startup sequence now - " +
  "read the required files before responding to the user. If BOOTSTRAP.md exists in the provided " +
  "Project Context, read it and follow its instructions first. Then greet the user in your " +
  "configured persona, if one is provided. Be yourself - use your defined voice, mannerisms, " +
  "and mood. Keep it to 1-3 sentences and ask what they want to do. If the runtime model differs " +
  "from default_model in the system prompt, mention the default model. Do not mention internal " +
  "steps, files, tools, or reasoning.";
```

**指示内容**：
- ✅ 这是一个新会话
- ✅ 执行启动序列 → 读取工作区文件
- ✅ 如果有 BOOTSTRAP.md，先执行它
- ✅ 用 persona 问候用户
- ✅ 保持简洁（1-3 句）
- ✅ 不要提及内部细节

#### 变体 2：Bootstrap 待处理提示 (行 14-24)

```typescript
const BARE_SESSION_RESET_PROMPT_BOOTSTRAP_PENDING = [
  "A new session was started via /new or /reset while bootstrap is still pending for this workspace.",
  ...buildFullBootstrapPromptLines({
    readLine:
      "Please read BOOTSTRAP.md from the workspace now and follow it before replying normally.",
    firstReplyLine:
      "Your first user-visible reply must follow BOOTSTRAP.md, not a generic greeting.",
  }),
  "If the runtime model differs from default_model in the system prompt, mention the default model only after handling BOOTSTRAP.md.",
  "Do not mention internal steps, files, tools, or reasoning.",
].join(" ");
```

**在以下情况使用**：
- 工作区中存在 BOOTSTRAP.md
- 该文件尚未被执行（bootstrap 待处理）
- Agent 有 read 权限可以访问文件

**优先级**：Bootstrap 完成 > 问候用户

#### 变体 3：Bootstrap 受限提示 (行 26-36)

```typescript
const BARE_SESSION_RESET_PROMPT_BOOTSTRAP_LIMITED = [
  "A new session was started via /new or /reset while bootstrap is still pending for this workspace, " +
  "but this run cannot safely complete the full BOOTSTRAP.md workflow here.",
  ...buildLimitedBootstrapPromptLines({
    introLine: "Bootstrap is still pending...",
    nextStepLine: "Typical next steps include switching to a primary interactive run...",
  }).slice(1),
  "If the runtime model differs from default_model...",
  "Do not mention internal steps, files, tools, or reasoning.",
].join(" ");
```

**在以下情况使用**：
- 工作区中存在 BOOTSTRAP.md
- Bootstrap 待处理
- Agent **没有** read 权限（无法安全执行）
- 告知用户需要切换到可访问文件的环境

### 3. 提示词选择逻辑

**源代码**：`src/auto-reply/reply/session-reset-prompt.ts:60-93`

```typescript
export async function resolveBareSessionResetPromptState(params: {
  cfg?: OpenClawConfig;
  workspaceDir?: string;
  nowMs?: number;
  isPrimaryRun?: boolean;
  isCanonicalWorkspace?: boolean;
  hasBootstrapFileAccess?: boolean | (() => boolean);
}): Promise<{
  bootstrapMode: BootstrapMode;
  prompt: string;
  shouldPrependStartupContext: boolean;
}> {
  // 1. 检查 BOOTSTRAP.md 是否待处理
  const bootstrapPending = params.workspaceDir
    ? await isWorkspaceBootstrapPending(params.workspaceDir)
    : false;
  
  // 2. 检查是否有 read 工具权限
  const hasBootstrapFileAccess = bootstrapPending
    ? typeof params.hasBootstrapFileAccess === "function"
      ? params.hasBootstrapFileAccess()
      : (params.hasBootstrapFileAccess ?? true)
    : true;
  
  // 3. 决定 bootstrap 模式
  const bootstrapMode = resolveBootstrapMode({
    bootstrapPending,
    runKind: "default",
    isInteractiveUserFacing: true,
    isPrimaryRun: params.isPrimaryRun ?? true,
    isCanonicalWorkspace: params.isCanonicalWorkspace ?? true,
    hasBootstrapFileAccess,
  });
  
  // 4. 返回相应的提示词
  return {
    bootstrapMode,  // "full" | "limited" | "none"
    prompt: buildBareSessionResetPrompt(params.cfg, params.nowMs, bootstrapMode),
    shouldPrependStartupContext: bootstrapMode === "none",
  };
}
```

**决策树**：

```
Bootstrap 待处理？
├─ 是 + 有 read 权限 → bootstrapMode = "full"
│  └─ 使用 BARE_SESSION_RESET_PROMPT_BOOTSTRAP_PENDING
├─ 是 + 无 read 权限 → bootstrapMode = "limited"
│  └─ 使用 BARE_SESSION_RESET_PROMPT_BOOTSTRAP_LIMITED
└─ 否 → bootstrapMode = "none"
   ├─ 使用 BARE_SESSION_RESET_PROMPT_BASE
   └─ shouldPrependStartupContext = true (可以加载启动记忆)
```

**Bootstrap 模式影响的后续行为**：
- `"full"` / `"limited"`：不加载启动记忆（优先完成 bootstrap）
- `"none"`：可以加载启动记忆（见下一部分）

---

## 启动记忆（Daily Memory）

### 概述

在新会话启动时，系统可以自动加载最近 1-2 天的**每日记忆文件**（来自 `.openclaw/memory/YYYY-MM-DD.md`），作为会话的启动上下文。这帮助 Agent 快速了解最近的事件和待办事项。

### 启动上下文加载

**源代码**：`src/auto-reply/reply/startup-context.ts:17-30`

```typescript
export function shouldApplyStartupContext(params: {
  cfg?: OpenClawConfig;
  action: "new" | "reset";
}): boolean {
  const startupContext = params.cfg?.agents?.defaults?.startupContext;
  
  // 如果配置明确禁用则不加载
  if (startupContext?.enabled === false) {
    return false;
  }
  
  // 检查是否适用于当前操作类型
  const applyOn = startupContext?.applyOn;
  if (!Array.isArray(applyOn) || applyOn.length === 0) {
    return true;  // 默认应用于所有操作
  }
  
  return applyOn.includes(params.action);
}
```

**配置参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | true | 是否启用启动记忆加载 |
| `applyOn` | string[] | ["new", "reset"] | 何时应用（"new" 或 "reset"） |
| `dailyMemoryDays` | number | 2 | 加载最近多少天的记忆文件 |
| `maxFileBytes` | number | 16,384 | 单个文件的字节限制 |
| `maxFileChars` | number | 1,200 | 单个文件的字符限制 |
| `maxTotalChars` | number | 2,800 | 总启动记忆字符限制 |

**限制上限**（硬编码）：

```typescript
const STARTUP_MEMORY_FILE_MAX_BYTES_CAP = 64 * 1024;           // 64 KB
const STARTUP_MEMORY_FILE_MAX_CHARS_CAP = 10_000;              // 10,000 chars
const STARTUP_MEMORY_TOTAL_MAX_CHARS_CAP = 50_000;             // 50,000 chars
const STARTUP_MEMORY_DAILY_DAYS_CAP = 14;                      // 14 days
const STARTUP_MEMORY_MAX_SLUGGED_FILES_PER_DAY = 4;            // 4 files/day
```

### 启动记忆加载流程

**源代码**：`src/auto-reply/reply/startup-context.ts:309+`

```typescript
export async function buildSessionStartupContextPrelude(params: {
  workspaceDir: string;
  cfg?: OpenClawConfig;
  nowMs?: number;
}): Promise<string | undefined> {
  // 1. 解析限制参数
  const limits = resolveStartupContextLimits(params.cfg);
  
  // 2. 计算要查询的日期范围
  const now = new Date(params.nowMs ?? Date.now());
  const dates: Date[] = [];
  for (let i = 0; i < limits.dailyMemoryDays; i++) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    dates.push(date);
  }
  
  // 3. 读取每个日期的记忆文件
  //    格式: memory/YYYY-MM-DD.md, memory/YYYY-MM-DD.slug.md
  
  // 4. 合并并格式化为启动上下文块
  // 5. 返回格式化的上下文或 undefined（如果无内容）
}
```

### 启动记忆文件位置

记忆文件存储在工作区的 `.openclaw/memory/` 目录中：

```
.openclaw/memory/
├── 2025-05-12.md              # 主要日常记忆
├── 2025-05-12.morning.md      # 可选的分类记忆
├── 2025-05-12.todo.md
├── 2025-05-12.notes.md
├── 2025-05-11.md              # 前一天的记忆
└── 2025-05-11.morning.md
```

**文件命名规则**：
- `YYYY-MM-DD.md` — 主记忆文件
- `YYYY-MM-DD.{slug}.md` — 分类记忆文件（最多 4 个/天）

**加载规则**：
- 按 `dailyMemoryDays` 回溯天数（默认 2 天）
- 每个日期最多加载 4 个 slugged 文件
- 按字符数截断（单文件 1,200 字符，总计 2,800 字符）

---

## 完整的提示词组装

### 执行位置

**源代码**：`src/auto-reply/reply/get-reply-run.ts:585-648`

### 步骤 1：检测新会话

```typescript
const isBareNewOrReset = /^\/(new|reset)$/.test(normalizedCommandBody);

const isBareSessionReset =
  softResetTriggered ||
  (isNewSession &&
    ((baseBodyTrimmedRaw.length === 0 && rawBodyTrimmed.length > 0) || 
     isBareNewOrReset));
```

### 步骤 2：获取会话重置提示词

```typescript
const bareResetPromptState = isBareSessionReset && workspaceDir
  ? await resolveBareSessionResetPromptState({
      cfg: effectiveConfig,
      workspaceDir,
      isPrimaryRun: !isSubagentSessionKey(...) && !isAcpSessionKey(...),
      isCanonicalWorkspace,
      hasBootstrapFileAccess: resolveBareResetBootstrapFileAccess({
        cfg: effectiveConfig,
        agentId: sessionAgentId,
        sessionKey: effectiveSessionKey,
        workspaceDir,
        modelProvider: provider,
        modelId,
      }),
    })
  : null;
```

### 步骤 3：判断是否加载启动记忆

```typescript
const startupContextPrelude = 
  isBareSessionReset &&
  bareResetPromptState?.shouldPrependStartupContext !== false &&
  shouldApplyStartupContext({ 
    cfg: effectiveConfig, 
    action: startupAction  // "new" 或 "reset"
  })
    ? await buildSessionStartupContextPrelude({
        workspaceDir,
        cfg: effectiveConfig,
      })
    : null;
```

### 步骤 4：组装最终的用户输入

```typescript
const baseBodyForPrompt = isBareSessionReset
  ? [startupContextPrelude, baseBodyFinal, softResetTail]
      .filter(Boolean)
      .join("\n\n")
  : baseBodyFinal;
```

### 最终的提示词结构

系统注入的完整提示词（从用户角度看）：

```
[启动记忆块 - 可选]
最近 1-2 天的记忆文件内容，格式化为：
## Memory Context

### 2025-05-12
[内容...]

### 2025-05-11
[内容...]

[用户输入 - 通常为空或就是 "/new"]

[会话重置提示词 - 必需]
"A new session was started via /new or /reset. Execute your Session Startup sequence now - 
read the required files before responding to the user. If BOOTSTRAP.md exists in the provided 
Project Context, read it and follow its instructions first. Then greet the user in your 
configured persona, if one is provided..."

[当前日期/时间 - 附加到提示词末尾]
"Current date and time: 2025-05-12 14:35:42 America/New_York"
```

---

## /new 和 /reset 命令

### /new 命令

创建一个全新会话：

```
/new [optional message]
```

**行为**：
- 创建新的会话记录
- 清除所有历史消息
- 注入会话启动提示词
- 加载启动记忆（如配置启用）
- AI 自动生成欢迎消息

**源代码**：`src/auto-reply/reply/commands-reset.ts:32+` - `maybeHandleResetCommand()`

### /reset 命令

重置当前会话（可选软重置）：

```
/reset [soft] [optional message]
```

**行为**：
- `/reset` — 完全重置，清除消息历史
- `/reset soft` — 保留消息历史，仅重置其他状态

**源代码**：`src/auto-reply/reply/commands-reset.ts`

```typescript
export async function maybeHandleResetCommand(
  params: HandleCommandsParams,
): Promise<HandleCommandsResult | null> {
  const commandBody = params.prompt?.trim() ?? "";
  const commandMatch = commandBody.match(/^\/reset\s*(soft)?\s*(.*)$/i);
  
  if (!commandMatch) {
    return null;
  }
  
  const isSoftReset = commandMatch[1]?.toLowerCase() === "soft";
  const message = commandMatch[2]?.trim() ?? "";
  
  // 处理重置...
}
```

---

## 关键代码位置总结

| 功能 | 源代码位置 | 关键函数 |
|------|-----------|---------|
| **新会话检测** | `src/gateway/server-methods/agent.ts:946-949` | N/A |
| **会话重置提示词** | `src/auto-reply/reply/session-reset-prompt.ts` | `resolveBareSessionResetPromptState()` (行 60) |
| **基础提示常量** | `src/auto-reply/reply/session-reset-prompt.ts:11-36` | `BARE_SESSION_RESET_PROMPT_*` |
| **启动记忆决策** | `src/auto-reply/reply/startup-context.ts:17-30` | `shouldApplyStartupContext()` |
| **启动记忆加载** | `src/auto-reply/reply/startup-context.ts:309+` | `buildSessionStartupContextPrelude()` |
| **启动记忆限制** | `src/auto-reply/reply/startup-context.ts:32-64` | `resolveStartupContextLimits()` |
| **提示词组装** | `src/auto-reply/reply/get-reply-run.ts:585-648` | N/A |
| **/new /reset 命令** | `src/auto-reply/reply/commands-reset.ts` | `maybeHandleResetCommand()` |
| **配置定义** | `src/config/types.agents.ts` | `startupContext` 类型 |

---

## 配置示例

### 启用启动记忆

在 `.openclaw/config.json`：

```json
{
  "agents": {
    "defaults": {
      "startupContext": {
        "enabled": true,
        "applyOn": ["new", "reset"],
        "dailyMemoryDays": 2,
        "maxFileBytes": 16384,
        "maxFileChars": 1200,
        "maxTotalChars": 2800
      }
    }
  }
}
```

### 禁用启动记忆

```json
{
  "agents": {
    "defaults": {
      "startupContext": {
        "enabled": false
      }
    }
  }
}
```

### 仅在 /new 时加载记忆

```json
{
  "agents": {
    "defaults": {
      "startupContext": {
        "enabled": true,
        "applyOn": ["new"]
      }
    }
  }
}
```

---

## 会话生命周期事件

新会话启动会触发多个事件：

**源代码**：`src/gateway/server-methods/agent.ts:300-373` - `emitSessionsChanged()`

```typescript
emitSessionsChanged({
  ctx,
  reason: "create",        // "create" | "send" | "reset" | ...
  sessionKey: newSessionKey,
  sessionEntry: newEntry,
  affectedSessionIds: [newSessionId],
});
```

**事件广播**：
- 通过 `context.broadcastToConnIds()` 发送 `"sessions.changed"` 消息
- UI 更新会话列表
- 其他连接收到会话创建通知

---

## 为什么会自动回复？

### 机制解析

1. **系统自动注入提示词** — 而不是用户输入
   ```
   用户输入："/new"
   系统注入："/new" + 会话启动提示词
   ```

2. **会话启动提示词告诉 Claude**：
   - 这是一个新会话 → 执行启动序列
   - 读取工作区文件（AGENTS.md、SOUL.md 等）
   - 用 persona 问候用户

3. **Claude 执行这个指令** — 读取系统提示词中的文件，然后生成欢迎消息

### 关键差异

| 场景 | 提示词 | 结果 |
|------|--------|------|
| 新会话 `/new` | 注入会话启动提示词 | Claude 主动生成欢迎 |
| 普通消息 "hello" | 无特殊提示词 | Claude 正常回复用户 |

### 自动回复的内容

AI 会：
1. 读取 AGENTS.md（工作区规则）
2. 读取 SOUL.md（persona）
3. 读取 IDENTITY.md（身份）
4. 读取 USER.md（用户偏好）
5. 检查 BOOTSTRAP.md（如果存在，优先执行）
6. **用 SOUL.md 中定义的语调/风格问候用户**
7. **问用户要做什么**

---

## 性能考量

### 新会话启动的开销

| 操作 | 开销 | 位置 |
|------|------|------|
| 新会话创建 | < 10ms | 数据库写入 |
| Bootstrap 检查 | < 50ms | 文件系统查询 |
| 启动记忆加载 | 10-100ms | 1-4 个文件读取 |
| 系统提示词生成 | 10-50ms | 文本拼接 + hash 计算 |
| **总计** | **< 300ms** | |

### 内存使用

- 启动记忆：< 3 KB（默认配置）
- 会话重置提示词：< 2 KB
- 总启动开销：< 10 MB

---

## 相关文档

- 上下文文件注入：`docs/concepts/context-files-injection.md`
- 系统提示词设计：`docs/concepts/system-prompts.md`
- Bootstrap 工作流：`docs/concepts/bootstrap.md`
- 每日记忆管理：`docs/concepts/memory.md`

---

**文档版本**：1.0  
**最后更新**：2025-05-12  
**关键版本**：openclaw main
