"""Lover / 角色卡 system 上下文拼接（供聊天、桌面主动感知、心跳复用）。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SKIP_WINDOW_MINUTES = 20
DEFAULT_HEARTBEAT_SKIP_WINDOW_MINUTES = 10


def _skip_window_ms(cfg: dict, default_minutes: int) -> int:
    try:
        minutes = max(1, int(cfg.get("skipWindowMinutes", default_minutes)))
    except (TypeError, ValueError):
        minutes = default_minutes
    return minutes * 60 * 1000


def desktop_awareness_skip_window_ms(settings: dict) -> int:
    return _skip_window_ms(
        settings.get("desktopAwareness") or {}, DEFAULT_SKIP_WINDOW_MINUTES
    )


def heartbeat_skip_window_ms(settings: dict) -> int:
    return _skip_window_ms(
        settings.get("heartbeat") or {}, DEFAULT_HEARTBEAT_SKIP_WINDOW_MINUTES
    )


def message_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
        return "".join(parts)
    return str(content)


def _get_target_message(messages: list, role: str) -> dict | None:
    for msg in messages:
        if msg.get("role") == role:
            return msg
    return None


def content_append(messages: list, role: str, content: str) -> None:
    target = _get_target_message(messages, role)
    if target is None:
        target = {"role": role, "content": ""}
        messages.insert(0, target)
    target["content"] = (target.get("content") or "") + content


def content_prepend(messages: list, role: str, content: str) -> None:
    target = _get_target_message(messages, role)
    if target is None:
        target = {"role": role, "content": ""}
        messages.insert(0, target)
    target["content"] = content + (target.get("content") or "")


def ensure_system_message(messages: list) -> None:
    if not _get_target_message(messages, "system"):
        messages.insert(0, {"role": "system", "content": ""})


def prepend_global_system_prompt(messages: list, settings: dict) -> None:
    ensure_system_message(messages)
    if settings.get("system_prompt"):
        content_prepend(messages, "system", settings["system_prompt"] + "\n\n")


def get_default_main_conversation(conversations: list) -> dict | None:
    return next(
        (
            c
            for c in (conversations or [])
            if c.get("kind") == "main" and (c.get("groupId") or "default") == "default"
        ),
        None,
    )


def conversation_last_activity_ms(conv: dict) -> int:
    last = int(conv.get("timestamp") or 0)
    for msg in conv.get("messages") or []:
        ts = msg.get("timestamp")
        if ts:
            last = max(last, int(ts))
    return last


def is_conversation_recently_active(conv: dict, window_ms: int) -> bool:
    last = conversation_last_activity_ms(conv)
    if not last:
        return False
    return (int(time.time() * 1000) - last) < window_ms


def is_default_group_recently_active(
    conversations: list,
    window_ms: int,
    group_id: str = "default",
) -> bool:
    for conv in conversations or []:
        if (conv.get("groupId") or "default") != group_id:
            continue
        if is_conversation_recently_active(conv, window_ms):
            return True
    return False


def is_awareness_no_action(reply: str) -> bool:
    normalized = (reply or "").strip()
    if not normalized:
        return True
    if normalized == "[NO_ACTION]":
        return True
    stripped = normalized.strip("`").strip()
    return stripped == "[NO_ACTION]"


def select_recent_chat_messages(raw_messages: list, limit: int = 20) -> list[dict]:
    useful = [m for m in (raw_messages or []) if m.get("role") in ("user", "assistant")]
    result = []
    for m in useful[-limit:]:
        text = message_text_content(m.get("pure_content") or m.get("content")).strip()
        if not text:
            continue
        result.append({"role": m["role"], "content": text})
    return result


def _resolve_cur_memory(settings: dict):
    mem_settings = settings.get("memorySettings") or {}
    if not mem_settings.get("is_memory") or not mem_settings.get("selectedMemory"):
        return None
    memory_id = mem_settings["selectedMemory"]
    for memory in settings.get("memories") or []:
        if memory.get("id") == memory_id:
            return memory
    return None


async def append_character_card_context(
    messages: list,
    settings: dict,
    *,
    user_prompt: str = "",
    assistant_reply: str = "",
    include_diary_summary: bool = False,
    is_sub_agent: bool = False,
) -> None:
    """向 messages 的 system 追加角色卡 / lover 相关上下文（与 generate_stream_response 一致）。"""
    if is_sub_agent:
        return
    mem_settings = settings.get("memorySettings") or {}
    if not mem_settings.get("is_memory") or not mem_settings.get("selectedMemory"):
        return

    cur_memory = _resolve_cur_memory(settings)
    if not cur_memory:
        return

    ensure_system_message(messages)
    _user_name = mem_settings.get("userName", "")
    _char_name = cur_memory.get("name") or ""

    from py.lover_memory_fts import lover_data_root as _lover_root

    _lover_dir = _lover_root()

    def _read_lover_file_sync(name: str) -> str:
        p = _lover_dir / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                pass
        return ""

    _user_profile_raw, _soul_raw, _memory_notes_raw = await asyncio.gather(
        asyncio.to_thread(_read_lover_file_sync, "USER.md"),
        asyncio.to_thread(_read_lover_file_sync, "SOUL.md"),
        asyncio.to_thread(_read_lover_file_sync, "MEMORY.md"),
    )

    _user_profile = _user_profile_raw or mem_settings.get("userProfile", "")
    if _user_profile:
        _user_profile = _user_profile.replace("{{user}}", _user_name).replace("{{char}}", _char_name)
        content_append(messages, "system", "\n## 用户档案\n" + _user_profile + "\n")

    _soul = _soul_raw or cur_memory.get("soul", "")
    if _soul:
        _soul = _soul.replace("{{user}}", _user_name).replace("{{char}}", _char_name)
        content_append(messages, "system", "\n## 元层原则\n" + _soul + "\n")

    if mem_settings.get("userName"):
        content_append(
            messages,
            "system",
            "与你交流的默认用户名为：\n\n"
            + mem_settings["userName"]
            + "\n\n注意！除非用户消息中提到了是其他用户发送，否则视为默认用户发送的消息\n\n",
        )

    lore_content = ""
    for lore in cur_memory.get("characterBook") or []:
        lore_keys = [k for k in (lore.get("keysRaw") or "").split("\n") if k != ""]
        if lore_keys and any(key in user_prompt or key in assistant_reply for key in lore_keys):
            lore_content += lore.get("content", "") + "\n\n"

    if lore_content:
        if mem_settings.get("userName"):
            lore_content = lore_content.replace("{{user}}", mem_settings["userName"])
        lore_content = lore_content.replace("{{char}}", cur_memory["name"])
        content_append(
            messages,
            "system",
            "世界观设定：\n\n" + lore_content + "\n\n世界观设定结束\n\n",
        )

    for field, label in (
        ("description", "角色设定"),
        ("personality", "性格设定"),
    ):
        value = cur_memory.get(field)
        if value:
            if mem_settings.get("userName"):
                value = value.replace("{{user}}", mem_settings["userName"])
            value = value.replace("{{char}}", cur_memory["name"])
            content_append(messages, "system", f"{label}：\n\n{value}\n\n{label}结束\n\n")

    mes_example = cur_memory.get("mesExample")
    if mes_example:
        if mem_settings.get("userName"):
            mes_example = mes_example.replace("{{user}}", mem_settings["userName"])
        mes_example = mes_example.replace("{{char}}", cur_memory["name"])
        content_append(messages, "system", "对话示例：\n\n" + mes_example + "\n\n对话示例结束\n\n")

    system_prompt = cur_memory.get("systemPrompt")
    if system_prompt:
        if mem_settings.get("userName"):
            system_prompt = system_prompt.replace("{{user}}", mem_settings["userName"])
        system_prompt = system_prompt.replace("{{char}}", cur_memory["name"])
        content_append(messages, "system", "\n\n" + system_prompt + "\n\n")

    generic = mem_settings.get("genericSystemPrompt")
    if generic:
        if mem_settings.get("userName"):
            generic = generic.replace("{{user}}", mem_settings["userName"])
        generic = generic.replace("{{char}}", cur_memory["name"])
        content_append(messages, "system", "\n\n" + generic + "\n\n")

    _memory_notes = _memory_notes_raw or mem_settings.get("memoryNotes", "")
    if _memory_notes:
        _memory_notes = _memory_notes.replace("{{user}}", _user_name).replace("{{char}}", _char_name)
        content_append(messages, "system", "\n## 记忆笔记\n" + _memory_notes + "\n")

    if include_diary_summary:
        _user_msgs = [m for m in messages if m.get("role") == "user"]
        if len(_user_msgs) <= 1:
            try:
                from py.lover_diary_summary import build_recent_diary_summary
                from py.lover_memory_fts import workspace_root_from_settings as _diary_ws

                _diary_root = _diary_ws(settings)
                if _diary_root and _diary_root.is_dir():
                    _diary_block = await asyncio.to_thread(
                        build_recent_diary_summary, _diary_root, 7
                    )
                    if _diary_block:
                        content_append(messages, "system", "\n" + _diary_block)
            except Exception as err:
                logger.warning("[日记概要] 注入失败: %s", err)



async def read_heartbeat_md(settings: dict) -> str:
    """读取 lover 数据目录下的 HEARTBEAT.md，不存在则返回空串。"""
    try:
        from py.lover_memory_fts import lover_data_root as _lover_root

        _lover_dir = _lover_root()
        p = _lover_dir / "HEARTBEAT.md"
        if not p.is_file():
            return ""
        return await asyncio.to_thread(
            lambda: p.read_text(encoding="utf-8", errors="replace").strip()
        )
    except Exception as err:
        logger.warning("[HEARTBEAT.md] 读取失败: %s", err)
        return ""


async def build_lover_system_messages(
    settings: dict,
    *,
    user_prompt: str = "",
    assistant_reply: str = "",
    include_diary_summary: bool = False,
    is_sub_agent: bool = False,
) -> list:
    """构建含全局 system_prompt + 角色卡上下文的 messages（仅 system 条）。"""
    messages: list[dict] = [{"role": "system", "content": ""}]
    prepend_global_system_prompt(messages, settings)
    await append_character_card_context(
        messages,
        settings,
        user_prompt=user_prompt,
        assistant_reply=assistant_reply,
        include_diary_summary=include_diary_summary,
        is_sub_agent=is_sub_agent,
    )
    return messages


FTS_DEFAULT_TOP_K = 10


async def search_fts_for_context(
    settings: dict, user_prompt: str, *, top_k: int = FTS_DEFAULT_TOP_K
) -> str:
    """执行 FTS 检索，返回格式化的相关回忆文本块；无结果或异常时返回空串。"""
    if not user_prompt:
        return ""
    try:
        from py.lover_memory_fts import (
            lover_memory_options as fts_opts,
            search_memory,
            workspace_root_from_settings as fts_ws,
        )

        _fts_ws = fts_ws(settings)
        if not (_fts_ws and _fts_ws.is_dir()):
            return ""
        _fts_results = await asyncio.to_thread(
            search_memory, _fts_ws, user_prompt, top_k, fts_opts(settings)
        )
        if not _fts_results:
            return ""
        block = "## 相关回忆\n"
        for hit in _fts_results:
            block += f"- [{hit['path']}] {hit['snippet']}\n"
        return block
    except Exception as err:
        logger.warning("[FTS] 检索异常: %s", err)
        return ""


def inject_fts_before_last_user(messages: list, fts_block: str) -> None:
    """将 fts_block 作为独立 system 消息插入到最后一条 user 消息正前方。"""
    if not fts_block:
        return
    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break
    if last_user_idx is not None:
        messages.insert(last_user_idx, {"role": "system", "content": fts_block})


def last_user_and_assistant_text(raw_messages: list) -> tuple[str, str]:
    user_prompt = ""
    assistant_reply = ""
    for m in reversed(raw_messages or []):
        role = m.get("role")
        text = message_text_content(m.get("pure_content") or m.get("content"))
        if role == "user" and not user_prompt:
            user_prompt = text
        elif role == "assistant" and not assistant_reply:
            assistant_reply = text
        if user_prompt and assistant_reply:
            break
    return user_prompt, assistant_reply
