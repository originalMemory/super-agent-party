# OpenClaw 上下文文件注入机制

## 概述

OpenClaw 在每次用户发消息时，都会从工作区根目录重新加载 8 类特殊的 Markdown 文件，并将其嵌入到系统提示词中，发送给 Claude。这确保 agent 始终看到最新的工作区配置、用户偏好和心跳状态。

**关键结论：所有上下文文件都在每条消息时从磁盘重新读取，但系统提示词的稳定前缀会被 LRU 缓存以优化 prompt cache 命中率。**

---

## 8 类上下文文件

| 文件名 | 优先级 | 用途 | 类型 |
|--------|--------|------|------|
| **AGENTS.md** | 10 | 工作区规则、agent 配置 | 稳定 |
| **SOUL.md** | 20 | persona、语调、行为风格 | 稳定 |
| **IDENTITY.md** | 30 | agent 身份信息 | 稳定 |
| **USER.md** | 40 | 用户信息、偏好 | 稳定 |
| **TOOLS.md** | 50 | 工具用法指南 | 稳定 |
| **BOOTSTRAP.md** | 60 | 初始化工作流 | 稳定 |
| **MEMORY.md** | 70 | 持久化记忆 | 稳定 |
| **HEARTBEAT.md** | 动态 | 心跳任务（每次轮询可能不同） | 动态 |

### 文件定义位置

**源代码位置**：`src/agents/workspace.ts:21-28`

```typescript
export const DEFAULT_AGENTS_FILENAME = "AGENTS.md";
export const DEFAULT_SOUL_FILENAME = "SOUL.md";
export const DEFAULT_TOOLS_FILENAME = "TOOLS.md";
export const DEFAULT_IDENTITY_FILENAME = "IDENTITY.md";
export const DEFAULT_USER_FILENAME = "USER.md";
export const DEFAULT_HEARTBEAT_FILENAME = "HEARTBEAT.md";
export const DEFAULT_BOOTSTRAP_FILENAME = "BOOTSTRAP.md";
export const DEFAULT_MEMORY_FILENAME = CANONICAL_ROOT_MEMORY_FILENAME;
```

---

## 执行流程

### 完整的调用链

```
用户发送消息
  ↓
dispatchInboundMessage()
  【src/auto-reply/dispatch.ts】
  ↓
runEmbeddedPiAgent()
  【src/agents/pi-embedded-runner/run.ts:342】
  ↓
runEmbeddedAttemptWithBackend() → runEmbeddedAttempt()
  【src/agents/pi-embedded-runner/run/backend.ts】
  ↓
resolveAttemptBootstrapContext()
  【src/agents/pi-embedded-runner/run/attempt.ts:963】
  ↓
resolveBootstrapContextForRun()  ← ⚠️  从磁盘读取所有文件
  【src/agents/bootstrap-files.ts:268】
  ├─ 调用 resolveBootstrapFilesForRun() 加载文件
  ├─ 调用 applyBootstrapHookOverrides() 应用插件修改
  └─ 调用 buildBootstrapContextForFiles() 转换为 EmbeddedContextFile[]
  ↓
buildAgentSystemPrompt()  ← 构建系统提示词
  【src/agents/system-prompt.ts:553】
  ├─ 将文件内容嵌入系统提示词
  ├─ 计算稳定前缀的 hash
  ├─ LRU 缓存查询（hashStablePromptInput 函数）
  └─ 附加动态部分（HEARTBEAT.md）
  ↓
系统提示词 → 发送给 Claude
```

---

## 关键代码位置

### 1. 文件加载

| 功能 | 源代码位置 |
|------|-----------|
| 主加载函数 | `src/agents/bootstrap-files.ts:268` - `resolveBootstrapContextForRun()` |
| 从文件系统读取 | `src/agents/workspace.ts:56-89` - `readWorkspaceFileWithGuards()` |
| 应用插件 Hook | `src/agents/bootstrap-files.ts:253` - `applyBootstrapHookOverrides()` |
| 按优先级排序 | `src/agents/system-prompt.ts:118-134` - `sortContextFilesForPrompt()` |
| 转换为嵌入对象 | `src/agents/bootstrap-files.ts:286` - `buildBootstrapContextForFiles()` |

### 2. 系统提示词构建

| 功能 | 源代码位置 |
|------|-----------|
| 主构建函数 | `src/agents/system-prompt.ts:553` - `buildAgentSystemPrompt()` |
| 缓存查询 | `src/agents/system-prompt.ts:68-86` - `cacheStablePromptPrefix()` |
| Hash 计算 | `src/agents/system-prompt.ts:88-92` - `hashStablePromptInput()` |
| 稳定文件注入 | `src/agents/system-prompt.ts:1082-1087` |
| 动态文件注入 | `src/agents/system-prompt.ts:1113-1118` |
| 缓存边界标记 | `src/agents/system-prompt-cache-boundary.ts` - `SYSTEM_PROMPT_CACHE_BOUNDARY` |

### 3. 文件内容处理

| 功能 | 源代码位置 |
|------|-----------|
| 内容清理 | `src/agents/system-prompt.ts:111-116` - `sanitizeContextFileContentForPrompt()` |
| 项目上下文章节 | `src/agents/system-prompt.ts:136-166` - `buildProjectContextSection()` |
| SOUL.md 特殊处理 | `src/agents/system-prompt.ts:151-159` |
| HEARTBEAT.md 处理 | `src/agents/system-prompt.ts:168-179` - `buildHeartbeatSection()` |
| MEMORY.md 处理 | `src/agents/system-prompt.ts:803` - `buildMemoryPromptSection()` |

### 4. 配置控制

| 功能 | 源代码位置 |
|------|-----------|
| 注入模式控制 | `src/agents/bootstrap-files.ts:54-56` - `resolveContextInjectionMode()` |
| 大小限制 | `src/agents/pi-embedded-helpers.ts` - `resolveBootstrapMaxChars()` 和 `resolveBootstrapTotalMaxChars()` |
| 文件缓存 | `src/agents/workspace.ts:42-43` - `workspaceFileCache` |
| LRU 缓存 | `src/agents/system-prompt.ts:60-86` - `stablePromptPrefixCache` |

---

## 详细时间线

### 启动时
- 无特殊加载
- 工作区文件尚未读取

### 第一条用户消息
1. **触发** `runEmbeddedPiAgent()` (行 342)
2. **加载** `resolveBootstrapContextForRun()` 从磁盘读取所有 8 类文件 (行 268)
3. **构建** `buildAgentSystemPrompt()` 将文件嵌入系统提示词 (行 553)
4. **缓存** 计算稳定前缀 hash，存入 LRU 缓存（最多 64 条）(行 68-86)
5. **发送** 系统提示词 + 消息 → Claude

### 第二条消息及以后
1. **再次触发** `runEmbeddedPiAgent()`
2. **重新加载** `resolveBootstrapContextForRun()` **从磁盘重新读取所有 8 类文件**（即使文件未变）
3. **计算新 hash** `buildAgentSystemPrompt()` 计算稳定前缀 hash
4. **缓存命中检查**
   - 若 hash 与缓存中某条相同 → 复用缓存前缀（节省重拼接，提升 prompt cache 命中率）
   - 若 hash 不同（文件被编辑）→ 重新拼接前缀，更新缓存
5. **发送** 系统提示词 + 消息 → Claude

---

## 缓存策略

### LRU 缓存（稳定前缀）

**源代码**：`src/agents/system-prompt.ts:60-86`

```typescript
const stablePromptPrefixCache = new Map<string, StablePromptPrefixCacheEntry>();
const SYSTEM_PROMPT_STABLE_PREFIX_CACHE_LIMIT = 64;

function cacheStablePromptPrefix(key: string, build: () => string): string {
  const cached = stablePromptPrefixCache.get(key);
  if (cached) {
    // 移到末尾（最近使用）
    stablePromptPrefixCache.delete(key);
    stablePromptPrefixCache.set(key, cached);
    return cached.value;
  }
  
  const value = build();
  stablePromptPrefixCache.set(key, { value });
  
  // 移出最旧的条目
  while (stablePromptPrefixCache.size > SYSTEM_PROMPT_STABLE_PREFIX_CACHE_LIMIT) {
    const oldestKey = stablePromptPrefixCache.keys().next().value;
    if (oldestKey) {
      stablePromptPrefixCache.delete(oldestKey);
    }
  }
  return value;
}
```

### 缓存 Key 生成

**源代码**：`src/agents/system-prompt.ts:835-871`

缓存 key 包含以下内容的 SHA256 hash：
- `workspaceDir`
- `promptMode`（full/minimal/none）
- `toolLines`
- `providerSectionOverrides`
- `ownerLine`
- `reasoningLevel`
- `userTimezone`
- `stableContextFiles`（稳定工作区文件列表）
- 其他配置参数

**不包含动态内容**（心跳状态、消息时间戳等），确保同一工作区的相同配置可以命中缓存。

### Prompt Cache 边界

**源代码**：`src/agents/system-prompt.ts:1106` 和 `src/agents/system-prompt-cache-boundary.ts`

系统提示词分为两部分：

```
┌─────────────────────────────────────────────┐
│  稳定前缀（缓存边界之前）                    │
├─ 工具列表、工作空间信息、权限等基本配置     │
├─ # Project Context                          │
├─ 所有稳定文件内容（嵌入）                   │
└─────────────────────────────────────────────┤ ← SYSTEM_PROMPT_CACHE_BOUNDARY
│  动态部分（缓存边界之后）                    │
├─ # Dynamic Project Context                  │
├─ HEARTBEAT.md（动态）                       │
├─ 频道/会话特定指导                          │
└─ ## Runtime 信息                            │
```

**优势**：
- 稳定前缀字节一致 → Claude 的 prompt cache 可以命中
- 动态部分每次新鲜 → 心跳、会话状态总是最新

---

## 特殊文件处理

### SOUL.md
**源代码**：`src/agents/system-prompt.ts:151-159`

如果 SOUL.md 存在：
- 系统提示词会明确指示 agent："embody its persona and tone"
- 避免 stiff、generic 的回复风格
- 优先级高（20），排在 AGENTS.md 之后、IDENTITY.md 之前

### HEARTBEAT.md
**源代码**：`src/agents/system-prompt.ts:57-59, 168-179`

- 标记为 **动态文件**，始终放在缓存边界后
- 包含特殊提示："如果是心跳轮询且无需注意，回复 HEARTBEAT_OK"
- 可通过 `shouldIncludeHeartbeatGuidanceForSystemPrompt()` 禁用
- 内容每次轮询时可能不同

### MEMORY.md
**源代码**：`src/agents/system-prompt.ts:10, 803` 和 `src/plugins/memory-state.js`

- 通过 `buildMemoryPromptSection()` 单独处理（非直接嵌入）
- 集成到系统提示词的 `## Memory` 章节
- 支持引用模式配置（`memoryCitationsMode`）
- 从 `.openclaw/memory/` 目录读取

### BOOTSTRAP.md
**源代码**：`src/agents/system-prompt.ts:262-321` 和 `src/agents/bootstrap-files.ts:282-307`

- 仅在 bootstrap 未完成时注入
- 特殊提示："follow BOOTSTRAP.md before replying normally"
- Bootstrap 完成后从系统提示词移除
- 检查函数：`hasCompletedBootstrapTurn()` (行 58)

---

## 配置控制

### 注入模式（contextInjection）

**源代码**：`src/agents/bootstrap-files.ts:54-56`

```typescript
contextInjection: "always" | "lightweight" | "never"
```

| 模式 | 说明 |
|------|------|
| **always** | 默认模式，注入所有 8 类文件 |
| **lightweight** | 仅用于心跳/cron 模式，只包含 HEARTBEAT.md |
| **never** | 完全禁用注入 |

在 `src/agents/pi-embedded-runner/run/attempt.ts:966` 处根据 `isRawModelRun` 自动设为 "never"（模型探针不加载工作区上下文）。

### 大小限制

| 参数 | 默认值 | 源代码位置 |
|------|--------|-----------|
| 单文件限制 | ~12,000 字符 | `src/agents/pi-embedded-helpers.ts` - `resolveBootstrapMaxChars()` |
| 总文件限制 | ~50,000 字符 | `src/agents/pi-embedded-helpers.ts` - `resolveBootstrapTotalMaxChars()` |
| 工作区文件最大 | 2 MB | `src/agents/workspace.ts:40` - `MAX_WORKSPACE_BOOTSTRAP_FILE_BYTES` |

超出限制时：
- 文件被截断
- 生成警告消息（去重限制 1024 个）
- 用户收到 `[...truncated...]` 提示

---

## 文件内容清理

**源代码**：`src/agents/system-prompt.ts:111-116`

加载文件后的清理步骤：

1. **移除默认 HEARTBEAT 提示**
   - 避免与 `buildHeartbeatSection()` 生成的提示冲突
   - 移除精确匹配的字符串 `DEFAULT_HEARTBEAT_PROMPT_CONTEXT_BLOCK`

2. **压缩换行符**
   - 正则表达式：`/\n{3,}/g` → `\n\n`
   - 保持一致的格式

3. **格式化文件头**
   - 每个文件前加 `## 文件路径` 标记
   - 例如：`## agents.md`

---

## 注入形式示例

系统提示词的相关部分：

```markdown
## Project Context

The following project context files have been loaded:
If SOUL.md is present, embody its persona and tone. Avoid stiff, generic replies; follow its guidance unless higher-priority instructions override it.

## agents.md

[agents.md 的完整内容 — 按优先级排序后的第一个文件]

## soul.md

[soul.md 的完整内容 — 第二个文件]

## identity.md

[identity.md 的完整内容]

... 其他文件 ...

## memory.md

[memory.md 的完整内容]

[SYSTEM_PROMPT_CACHE_BOUNDARY 标记 — 缓存边界]

# Dynamic Project Context

The following frequently-changing project context files are kept below the cache boundary when possible:

## heartbeat.md

[heartbeat.md 的内容 — 每次构建时新鲜生成]

## Channels / Messages
[频道特定的指导]

## Runtime
[运行时信息]
```

---

## 性能考量

### 磁盘读取开销
- **每条消息都读一次** — 8 个文件从磁盘加载
- **文件缓存** — `workspaceFileCache` 按 inode/dev/size/mtime 缓存，避免重复读取
- 通常 < 10ms（SSD 上）

### 内存开销
- **LRU 缓存** — 最多 64 条缓存前缀，通常 < 10MB
- **EmbeddedContextFile 对象** — 每条消息新建，消息完成后 GC

### Prompt Cache 优化
- 稳定前缀字节一致 → Claude 的 prompt cache 命中率高
- 减少重复发送相同的系统提示词前缀
- 节省 API 使用成本（缓存命中时不计 tokens）

---

## 诊断和调试

### 系统提示词报告

**源代码**：`src/agents/system-prompt-report.ts`

生成诊断报告：

```typescript
buildSystemPromptReport({
  source: "run",
  generatedAt: Date.now(),
  systemPrompt: appendPrompt,
  bootstrapFiles: hookAdjustedBootstrapFiles,
  injectedFiles: contextFiles,
  bootstrapMaxChars,
  bootstrapTotalMaxChars,
  // ...
});
```

### 调试日志

| 位置 | 内容 |
|------|------|
| `src/agents/pi-embedded-runner/run/attempt.ts:993` | Bootstrap 上下文加载标记 |
| `src/agents/bootstrap-files.ts:144` | Bootstrap 警告（文件大小超限等） |
| `src/agents/system-prompt-stability.test.ts` | 缓存稳定性测试 |

### 测试

**源代码**：
- `src/agents/system-prompt.test.ts` — 系统提示词构建测试
- `src/agents/bootstrap-files.test.ts` — 文件加载测试
- `src/agents/system-prompt-stability.test.ts` — LRU 缓存稳定性测试

---

## 总结

### 核心事实

1. **每条消息都重新加载** — 所有 8 类文件都在 `resolveBootstrapContextForRun()` 中从磁盘读取
2. **按优先级排序** — AGENTS.md (10) → SOUL.md (20) → ... → MEMORY.md (70) → HEARTBEAT.md (动态)
3. **嵌入系统提示词** — 文件内容作为 `## Project Context` 和 `# Dynamic Project Context` 部分
4. **LRU 缓存优化** — 64 条缓存条目，缓存稳定前缀而非文件本身
5. **Prompt Cache 友好** — 缓存边界分离稳定和动态部分

### 设计目的

- **及时性**：用户在另一个编辑器中修改 AGENTS.md，下一条消息立即反映
- **效率**：LRU 缓存和 prompt cache 边界设计减少重复发送
- **灵活性**：大小限制、注入模式、插件 Hook 允许自定义行为
- **可靠性**：文件缓存、大小检查、截断警告确保系统稳定

---

## 相关文档

- 上下文文件格式指南：`docs/concepts/context-files.md`（如存在）
- Bootstrap 工作流：`docs/concepts/bootstrap.md`
- 系统提示词设计：`docs/concepts/system-prompts.md`
- 心跳机制：`docs/concepts/heartbeats.md`

---

**文档版本**：1.0  
**最后更新**：2025-05-12  
**关键版本**：openclaw main
