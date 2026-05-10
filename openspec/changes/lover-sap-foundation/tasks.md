## 1. 范围与 SSOT 清单

- [ ] 1.1 README：固定 **USER 独立**；**IDENTITY + SOUL** 双文件 **或** 单文件两节合并方案；**AGENTS** 可选；**MEMORY + 按日落盘** 仅 FTS；bootstrap **加载顺序**
- [ ] 1.2 删除仓库内对已移除变更 `workspace-memory-diary` 的残余引用（若有）

## 2. 记忆 FTS（仅记忆语料）

- [ ] 2.1 SQLite FTS5 + [wangfenjin/simple](https://github.com/wangfenjin/simple) 与打包说明
- [ ] 2.2 索引白名单：**仅** MEMORY 与按日日记；排除 USER/IDENTITY/SOUL/AGENTS
- [ ] 2.3 每轮用户消息后注入 top-k **回忆片段**，与 bootstrap 分区命名清晰
- [ ] 2.4 （可选）mem0：唯一 Agent id；或移除 mem0

## 3. Bootstrap（完整初始角色信息）

- [ ] 3.1 实现加载顺序：`AGENTS`（若有）→ `USER` → `IDENTITY` / `SOUL`（或合并文件）；内容含 **原设定书级信息**，**无**关键词设定书分支
- [ ] 3.2 （可选）`MEMORY.md` 是否额外常驻 bootstrap —— 与 2.2 一致并文档化
- [ ] 3.3 **删除**酒馆 `cur_memory` 每轮大块注入；**删除** characterBook 关键词按需注入（若有）
- [ ] 3.4 上下文压缩：**保护** bootstrap

## 4. 前端与酒馆移除

- [ ] 4.1 移除角色卡、换卡、酒馆主导航及相关设置
- [ ] 4.2 主会话 / 归档 / 主动归档 / 重置

## 5. 会话数据模型

- [ ] 5.1 主会话与归档状态
- [ ] 5.2 API：归档、重置

## 6. 分叉与文档

- [ ] 6.1 README：上游合并策略
- [ ] 6.2 lover 定位、SSOT、FTS 仅记忆、更名 super-agent-lover

## 7. 冒烟

- [ ] 7.1 连续两轮：bootstrap **无重复膨胀**；FTS 仅记忆命中
- [ ] 7.2 专有名词进 MEMORY/日记 → FTS 命中；simple 失败降级
- [ ] 7.3 归档与重置
