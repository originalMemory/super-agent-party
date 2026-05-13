"""
Lover bootstrap — 每次发消息时从磁盘重新加载人设文件，拼装 system prompt。

结构（对齐 OpenClaw context-files-injection）
---------------------------------------------
  STABLE BLOCK
    # Project Context
    [If SOUL.md is present, embody its persona and tone...]
    ## AGENTS.md（lover/）   ← main/dev 均强制；不存在时打 warning
    ## USER.md
    ## IDENTITY.md
    ## SOUL.md
    ## MEMORY.md            ← 可选摘要
  <!-- LOVER_PROMPT_CACHE_BOUNDARY -->

  DYNAMIC BLOCK
    # Dynamic Project Context
    ## Memory Recall (FTS)  ← 每轮基于最新 user 消息检索
    ## Workspace            ← workspace_path 有效时注入
      .agent/AGENTS.md（项目级）
      .agent/ai_todos.json
      skills 索引
    ## Runtime              ← 时间 / kind / workspace_path

入口：`build_lover_system_prompt()`
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
from functools import partial
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _lover_root() -> Path:
    from py.lover_memory_fts import lover_data_root
    return lover_data_root()


def _read_file(path: Path) -> str:
    """同步读取文件全文；不存在或读取失败时返回空串。"""
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        logger.warning("[lover/bootstrap] 读取 %s 失败: %s", path, e)
        return ""


def _section(heading: str, content: str) -> str:
    """将 content 包裹为带 heading 的 Markdown 段落；content 为空则返回空串。"""
    if not content.strip():
        return ""
    return f"{heading}\n\n{content}\n\n"


# ---------------------------------------------------------------------------
# Stable Block
# ---------------------------------------------------------------------------

def _build_stable_block(lover_root: Path) -> str:
    """构建 STABLE BLOCK（对齐 OpenClaw buildProjectContextSection）。"""
    parts: list[str] = ["# Project Context\n\n"]

    soul = _read_file(lover_root / "SOUL.md")
    # 仅当 SOUL.md 存在时才加入 persona 指令（对齐 OpenClaw 特殊处理逻辑）
    if soul:
        parts.append(
            "The following project context files have been loaded:\n"
            "If SOUL.md is present, embody its persona and tone. "
            "Avoid stiff, generic replies; follow its guidance unless "
            "higher-priority instructions override it.\n\n"
        )
    else:
        parts.append("The following project context files have been loaded:\n\n")

    # AGENTS.md — 强制注入；不存在时打 warning（不静默跳过）
    agents = _read_file(lover_root / "AGENTS.md")
    if agents:
        parts.append(_section("## AGENTS.md", agents))
    else:
        logger.warning(
            "[lover/bootstrap] AGENTS.md 不存在或为空: %s — 请检查 lover/ 目录",
            lover_root / "AGENTS.md",
        )

    user = _read_file(lover_root / "USER.md")
    if user:
        parts.append(_section("## USER.md", user))

    identity = _read_file(lover_root / "IDENTITY.md")
    if identity:
        parts.append(_section("## IDENTITY.md", identity))

    if soul:
        parts.append(_section("## SOUL.md", soul))

    memory = _read_file(lover_root / "MEMORY.md")
    if memory:
        parts.append(_section("## MEMORY.md", memory))

    return "".join(parts)


# ---------------------------------------------------------------------------
# Dynamic Block — FTS 记忆召回
# ---------------------------------------------------------------------------

async def _build_fts_section(user_query: str, settings: dict) -> str:
    """基于 user_query 做 FTS 检索，返回 ## Memory Recall (FTS) 块。"""
    if not user_query.strip():
        return ""
    try:
        from py.lover_memory_fts import lover_data_root, lover_memory_options, search_memory

        lover_root = lover_data_root()
        mem_limit: int = (settings.get("memorySettings") or {}).get("memoryLimit", 6)
        opts = lover_memory_options(settings)

        hits: list[dict[str, Any]] = await asyncio.to_thread(
            partial(search_memory, lover_root, user_query, mem_limit, opts)
        )
        if not hits:
            return ""
        lines = [f"- [{h['path']}] {h['snippet']}" for h in hits]
        return "## Memory Recall (FTS)\n\n" + "\n".join(lines) + "\n\n"
    except Exception as e:
        logger.warning("[lover/bootstrap] FTS 检索失败: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Dynamic Block — Workspace
# ---------------------------------------------------------------------------

def _build_workspace_section(workspace_path: str) -> str:
    """
    构建 ## Workspace 块（workspace_path 有效时注入）：
      - .agent/AGENTS.md（项目级操作约束）
      - .agent/ai_todos.json（未完成事项）
      - .agent/skills/ 索引
    """
    if not workspace_path:
        return ""
    cwd = Path(workspace_path)
    if not cwd.is_dir():
        logger.info(
            "[lover/bootstrap] workspace_path 不存在，跳过 Workspace 块: %s",
            workspace_path,
        )
        return ""

    sub_parts: list[str] = []

    # 项目级 AGENTS.md
    project_agents = _read_file(cwd / ".agent" / "AGENTS.md")
    if project_agents:
        sub_parts.append(_section("### .agent/AGENTS.md", project_agents))

    # ai_todos.json（仅未完成事项）
    todos_path = cwd / ".agent" / "ai_todos.json"
    if todos_path.is_file():
        try:
            raw = todos_path.read_text(encoding="utf-8")
            todos: list[dict] = json.loads(raw) if raw.strip() else []
            pending = [t for t in todos if isinstance(t, dict) and t.get("status") != "done"]
            if pending:
                status_icons = {"pending": "⏳", "in_progress": "🔄", "cancelled": "❌"}
                priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                lines = []
                for t in pending:
                    icon = status_icons.get(t.get("status", "pending"), "⏳")
                    pri = priority_icons.get(t.get("priority", "medium"), "🟡")
                    text = (t.get("content") or "")[:60]
                    lines.append(f"{icon} {pri} {text}")
                sub_parts.append(
                    "### 📋 Project TODOs (.agent/ai_todos.json)\n\n"
                    + "\n".join(lines)
                    + "\n\n"
                )
        except Exception as e:
            logger.warning("[lover/bootstrap] 读取 ai_todos.json 失败: %s", e)

    # .agent/skills/ 索引
    skills_root = cwd / ".agent" / "skills"
    if skills_root.is_dir():
        skill_lines: list[str] = []
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_id = skill_dir.name
            first_line = ""
            for name in ("SKILL.md", "skill.md", "SKILLS.md", "skills.md"):
                doc = skill_dir / name
                if doc.is_file():
                    try:
                        raw_lines = doc.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                        first_line = raw_lines[0] if raw_lines else ""
                    except Exception:
                        pass
                    break
            skill_lines.append(f"- **{skill_id}**" + (f": {first_line}" if first_line else ""))
        if skill_lines:
            sub_parts.append(
                "### 🛠️ Project Skills (.agent/skills)\n\n"
                + "\n".join(skill_lines)
                + "\n\n"
            )

    if not sub_parts:
        return ""
    return "## Workspace\n\n" + "".join(sub_parts)


# ---------------------------------------------------------------------------
# Dynamic Block — Runtime
# ---------------------------------------------------------------------------

def _build_runtime_section(workspace_path: str | None) -> str:
    """构建 ## Runtime 块（时间、工作区路径）。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"Current time: {now}"]
    if workspace_path:
        lines.append(f"Workspace: {workspace_path}")
    return "## Runtime\n\n" + "\n".join(lines) + "\n\n"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def build_lover_system_prompt(
    user_query: str,
    settings: dict,
    workspace_path: str | None = None,
) -> str:
    """
    每次发消息时覆盖式重建 system prompt（稳定块 + 缓存边界 + 动态块）。

    参数
    ----
    user_query     : 本轮用户消息文本，用于 FTS 检索（空串则跳过 FTS）
    settings       : 全局 settings dict
    workspace_path : 当前工作区路径（cc_path）；``None`` = 未绑定
    """
    lover_root = _lover_root()

    # STABLE BLOCK（同步，人设文件通常在 page cache，< 10ms）
    stable = _build_stable_block(lover_root)

    # CACHE BOUNDARY
    boundary = "<!-- LOVER_PROMPT_CACHE_BOUNDARY -->\n\n"

    # DYNAMIC BLOCK
    dynamic_parts: list[str] = ["# Dynamic Project Context\n\n"]

    fts_section = await _build_fts_section(user_query, settings)
    if fts_section:
        dynamic_parts.append(fts_section)

    workspace_section = _build_workspace_section(workspace_path or "")
    if workspace_section:
        dynamic_parts.append(workspace_section)

    dynamic_parts.append(_build_runtime_section(workspace_path))

    dynamic = "".join(dynamic_parts)

    return stable + boundary + dynamic
