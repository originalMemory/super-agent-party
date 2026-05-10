## 1. 范围与 SSOT 清单

- [x] 1.1 README：固定 **USER 独立**；**IDENTITY.md** 与 **SOUL.md** **必须分文件、不合并**；**AGENTS** 可选；记忆仅 FTS（**`USER_DATA_DIR/lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**）；bootstrap **加载顺序**（见 **`docs/LOVER_SSOT.md`**）
- [x] 1.2 删除仓库内对已移除变更 `workspace-memory-diary` 的残余引用（已检索：无除本任务历史表述外的残留）

## 2. 记忆 FTS（仅记忆语料）

- [x] 2.1 SQLite FTS5：`py/lover_memory_fts.py`；内置 **trigram** / **unicode61** 降级；优先 **[wangfenjin/simple](https://github.com/wangfenjin/simple)**（`py/lover_fts_simple_auto.py` 自动下载 + `tokenize='simple'` + 检索 `simple_query()`）；索引 **`memory_index.sqlite`**
- [x] 2.2 索引白名单：**`lover/MEMORY.md`** + **`lover/memory/` 递归 `.md`**；根目录 = **`USER_DATA_DIR/lover`**；**`sync_memory_index(...)`**
- [x] 2.3 每轮 **`search_memory(..., lover_memory_options(settings))`** 注入【相关回忆】
- [x] 2.4 **已移除 mem0**
- [x] 2.5 **定时 sync**：`lifespan` 启动一次 + 后台循环；间隔 **`loverSettings.memoryIndexSyncIntervalMinutes`**（默认 **10** 分钟，写入 `settings_template.json` / 角色页 **Lover 工作区**）
- [ ] 2.6 **TODO**：校验各平台 **libsimple** 与 Python 自带 SQLite 的兼容性；PyInstaller 打包时一并分发扩展路径说明；可选暴露「重建索引」按钮（删库 + sync）

### TODO — lover 收尾时逐项检查 / 删除

- [ ] **TODO** `server.py`：删除酒馆式 **`cur_memory`** 大块注入（description / personality / mesExample / systemPrompt 等）
- [ ] **TODO** `server.py`：删除 **`characterBook`** 关键词按需注入
- [ ] **TODO** `server.py` / 设置：**`memoryId` / `selectedMemory`** 仅酒馆向量记忆链路若废弃则裁剪；清理 **`MEMORY_CACHE_DIR`** 下不再使用的 faiss 数据
- [ ] **TODO** 前端：角色卡、换卡、酒馆主导航；设置中与 **mem0 / embedding** 相关且已废弃的项
- [ ] **TODO** 文档：README 酒馆能力与 lover 描述分叉清理
- [ ] **TODO** 用户数据：若仍存在早期 **`.agent/lover_memory_fts.sqlite`**，提示删除（当前索引仅为 **`memory_index.sqlite`**）

## 3. Bootstrap（完整初始角色信息）

- [ ] 3.1 实现加载顺序：`AGENTS`（若有）→ `USER` → **`IDENTITY.md`** → **`SOUL.md`**（**两文件强制分离，不合并**）；内容含 **原设定书级信息**，**无**关键词设定书分支
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
- [ ] 6.2 lover 定位、SSOT（**`USER_DATA_DIR/lover`**）、FTS 仅记忆、**`lover/memory/` 递归 `.md`**（推荐按年月子目录）、更名 super-agent-lover

## 7. 冒烟

- [ ] 7.1 连续两轮：bootstrap **无重复膨胀**；FTS 仅记忆命中
- [ ] 7.2 专有名词进 MEMORY 或 **当日日记文件** → FTS 命中；simple / 内置 tokenizer 降级可接受
- [ ] 7.3 归档与重置
