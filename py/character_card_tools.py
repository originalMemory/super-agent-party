import json
from pathlib import Path
from py.get_setting import load_settings, save_settings

WRITABLE_FIELDS = {"soul", "description", "personality", "systemPrompt", "mesExample"}

_LOVER_FILE_MAP = {
    "userProfile": "USER.md",
    "memoryNotes": "MEMORY.md",
    "soul": "SOUL.md",
}


def _lover_dir() -> Path:
    from py.lover_memory_fts import lover_data_root
    return lover_data_root()


def _read_lover_file(name: str) -> str:
    p = _lover_dir() / name
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            pass
    return ""


def _write_lover_file(name: str, content: str) -> Path:
    p = _lover_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


async def get_character_card(fields: list = None) -> str:
    settings = await load_settings()
    memory_settings = settings.get("memorySettings", {})
    selected_id = memory_settings.get("selectedMemory")

    if not memory_settings.get("is_memory") or not selected_id:
        return json.dumps({"error": "当前未启用或未选中角色卡"}, ensure_ascii=False)

    cur_memory = None
    for m in settings.get("memories", []):
        if m["id"] == selected_id:
            cur_memory = m
            break

    if not cur_memory:
        return json.dumps({"error": f"未找到 id={selected_id} 的角色卡"}, ensure_ascii=False)

    result = {}
    if fields:
        for f in fields:
            if f in _LOVER_FILE_MAP:
                result[f] = _read_lover_file(_LOVER_FILE_MAP[f]) or memory_settings.get(f, "") or cur_memory.get(f, "")
            elif f in cur_memory:
                result[f] = cur_memory[f]
            else:
                result[f] = None
    else:
        result = {k: v for k, v in cur_memory.items() if k not in ("api_key",)}

    result["userProfile"] = _read_lover_file("USER.md") or memory_settings.get("userProfile", "")
    result["memoryNotes"] = _read_lover_file("MEMORY.md") or memory_settings.get("memoryNotes", "")
    return json.dumps(result, ensure_ascii=False)


async def update_character_card(field: str, value: str) -> str:
    if field not in WRITABLE_FIELDS:
        return json.dumps({
            "error": f"字段 '{field}' 不可修改，可写字段：{', '.join(sorted(WRITABLE_FIELDS))}"
        }, ensure_ascii=False)

    if field == "soul":
        p = _write_lover_file("SOUL.md", value)
        return json.dumps({
            "success": True,
            "field": field,
            "file": str(p),
            "length": len(value),
        }, ensure_ascii=False)

    settings = await load_settings()
    memory_settings = settings.get("memorySettings", {})
    selected_id = memory_settings.get("selectedMemory")

    if not memory_settings.get("is_memory") or not selected_id:
        return json.dumps({"error": "当前未启用或未选中角色卡"}, ensure_ascii=False)

    for m in settings.get("memories", []):
        if m["id"] == selected_id:
            m[field] = value
            await save_settings(settings)
            return json.dumps({
                "success": True,
                "name": m.get("name", ""),
                "field": field,
                "length": len(value),
            }, ensure_ascii=False)

    return json.dumps({"error": f"未找到 id={selected_id} 的角色卡"}, ensure_ascii=False)


async def update_user_profile(value: str) -> str:
    p = _write_lover_file("USER.md", value)
    return json.dumps({
        "success": True,
        "field": "userProfile",
        "file": str(p),
        "length": len(value),
    }, ensure_ascii=False)


async def update_memory_notes(value: str) -> str:
    p = _write_lover_file("MEMORY.md", value)
    return json.dumps({
        "success": True,
        "field": "memoryNotes",
        "file": str(p),
        "length": len(value),
    }, ensure_ascii=False)


get_character_card_tool = {
    "type": "function",
    "function": {
        "name": "get_character_card",
        "description": "读取当前角色卡的信息。可指定字段名获取特定内容，不指定则返回全部。同时返回全局用户档案（USER.md）和记忆笔记（MEMORY.md）。",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要读取的字段列表，如 ['soul', 'description', 'userProfile', 'memoryNotes']。不传则返回全部字段。",
                },
            },
            "required": [],
        },
    },
}

update_character_card_tool = {
    "type": "function",
    "function": {
        "name": "update_character_card",
        "description": "修改当前角色卡的指定字段。可写字段：soul（写入 SOUL.md）、description、personality、systemPrompt、mesExample。修改后自动保存。",
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "要修改的字段名",
                },
                "value": {
                    "type": "string",
                    "description": "新的字段值",
                },
            },
            "required": ["field", "value"],
        },
    },
}

update_user_profile_tool = {
    "type": "function",
    "function": {
        "name": "update_user_profile",
        "description": "修改用户档案（写入 lover/USER.md）。修改后自动保存。",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "新的用户档案内容（Markdown）",
                },
            },
            "required": ["value"],
        },
    },
}

update_memory_notes_tool = {
    "type": "function",
    "function": {
        "name": "update_memory_notes",
        "description": "修改记忆笔记（写入 lover/MEMORY.md）——长期事实与约定。修改后自动保存。",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "新的记忆笔记内容（Markdown）",
                },
            },
            "required": ["value"],
        },
    },
}
