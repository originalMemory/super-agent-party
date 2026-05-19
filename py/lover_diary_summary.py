"""
从日记树中提取最近 N 天的 frontmatter 概要，用于新会话启动注入。

扫描 memoryDirPath 下的 .md 文件，按修改时间倒序取最近 N 天，
提取 YAML frontmatter 中的「概要」和「心情」字段拼为精简列表。
概要缺失时降级读取「✨ 今日高光」段落；均无则跳过。
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_HIGHLIGHT_RE = re.compile(r"##\s*✨\s*今日高光\s*\n+(.*?)(?=\n##|\Z)", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    """简易 YAML frontmatter 解析（只处理简单 key: value 和列表）。"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: dict = {}
    current_key: Optional[str] = None
    current_list: list[str] = []
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip())
            continue
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val
            else:
                current_key = key
                current_list = []
    if current_key and current_list:
        result[current_key] = current_list
    return result


def _extract_highlight(text: str) -> str:
    """提取「✨ 今日高光」段落首行内容。"""
    m = _HIGHLIGHT_RE.search(text)
    if not m:
        return ""
    content = m.group(1).strip()
    first_line = content.splitlines()[0].strip() if content else ""
    return first_line


def _file_date_key(path: Path) -> str:
    """从文件名中提取日期字符串（如 2026-05-11），用于去重和排序。"""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else ""


def build_recent_diary_summary(
    memory_dir: Path,
    days: int = 7,
) -> str:
    """
    扫描 memory_dir 下所有 .md 文件，提取最近 N 天的日记概要。

    返回格式：
        ## 近期日记概要
        - 05-11 周一｜😮‍💨疲惫、无奈｜加班到九点半…
        - 05-10 周日｜…｜…

    无日记时返回空字符串。
    """
    if not memory_dir or not memory_dir.is_dir():
        return ""

    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    candidates: list[tuple[float, Path]] = []
    try:
        for md_file in memory_dir.rglob("*.md"):
            if not md_file.is_file():
                continue
            try:
                mtime = md_file.stat().st_mtime
                if mtime >= cutoff_ts:
                    candidates.append((mtime, md_file))
            except OSError:
                continue
    except Exception as e:
        logger.warning("[diary-summary] 扫描日记树失败: %s", e)
        return ""

    candidates.sort(key=lambda x: x[0], reverse=True)

    seen_dates: set[str] = set()
    entries: list[str] = []

    for _, md_file in candidates:
        date_key = _file_date_key(md_file)
        if date_key and date_key in seen_dates:
            continue
        if date_key:
            seen_dates.add(date_key)

        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        fm = _parse_frontmatter(text)
        summary = fm.get("概要", "")
        if isinstance(summary, list):
            summary = "；".join(summary)

        mood = fm.get("心情", "")
        if isinstance(mood, list):
            mood = "、".join(mood)

        if not summary:
            summary = _extract_highlight(text)
        if not summary:
            continue

        date_display = date_key[5:] if date_key else md_file.stem[:10]

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = ""
        if date_key:
            try:
                dt = datetime.datetime.strptime(date_key, "%Y-%m-%d")
                weekday = weekday_names[dt.weekday()]
            except ValueError:
                pass

        label = f"{date_display} {weekday}".strip()
        parts = [label]
        if mood:
            parts.append(mood)
        parts.append(summary)
        entries.append("- " + "｜".join(parts))

    if not entries:
        return ""

    return "## 近期日记概要\n\n" + "\n".join(entries) + "\n"
