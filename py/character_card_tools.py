import json
from pathlib import Path
from py.get_setting import load_settings, save_settings
from py.lover_system_context import LOVER_FILES

WRITABLE_FIELDS = {"description", "personality", "systemPrompt", "mesExample"}

LOVER_CONTEXT_KEYS = ("soul", "userProfile", "memoryNotes")


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
            if f in cur_memory:
                result[f] = cur_memory[f]
            else:
                result[f] = None
    else:
        result = {k: v for k, v in cur_memory.items() if k not in ("api_key",)}
    return json.dumps(result, ensure_ascii=False)


async def get_lover_context(fields: list = None) -> str:
    keys = [f for f in fields if f in LOVER_CONTEXT_KEYS] if fields else list(LOVER_CONTEXT_KEYS)
    result = {k: _read_lover_file(LOVER_FILES[k]) for k in keys}
    return json.dumps(result, ensure_ascii=False)


async def update_character_card(field: str, value: str) -> str:
    if field not in WRITABLE_FIELDS:
        return json.dumps({
            "error": f"字段 '{field}' 不可修改，可写字段：{', '.join(sorted(WRITABLE_FIELDS))}。全局共享内容请使用 update_lover_context"
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


async def update_lover_context(field: str, value: str) -> str:
    if field not in LOVER_CONTEXT_KEYS:
        return json.dumps({
            "error": f"字段 '{field}' 不可修改，可写字段：{', '.join(LOVER_CONTEXT_KEYS)}"
        }, ensure_ascii=False)
    p = _write_lover_file(LOVER_FILES[field], value)
    return json.dumps({
        "success": True, "field": field, "file": str(p), "length": len(value),
    }, ensure_ascii=False)


get_character_card_tool = {
    "type": "function",
    "function": {
        "name": "get_character_card",
        "description": "读取当前角色卡的信息（description、personality、systemPrompt 等角色级字段）。全局共享内容（元层原则、用户档案、记忆笔记）请使用 get_lover_context。",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要读取的角色卡字段列表，如 ['description', 'personality']。不传则返回全部字段。",
                },
            },
            "required": [],
        },
    },
}

get_lover_context_tool = {
    "type": "function",
    "function": {
        "name": "get_lover_context",
        "description": "读取全局共享上下文：元层原则（SOUL.md）、用户档案（USER.md）、记忆笔记（MEMORY.md）。这些内容所有角色共享，不属于单个角色卡。",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["soul", "userProfile", "memoryNotes"]},
                    "description": "要读取的字段列表。不传则返回全部三项。",
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
        "description": "修改当前角色卡的指定字段。可写字段：description、personality、systemPrompt、mesExample。全局共享内容（元层原则、用户档案、记忆笔记）请使用 update_lover_context。",
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

update_lover_context_tool = {
    "type": "function",
    "function": {
        "name": "update_lover_context",
        "description": "修改全局共享上下文。soul = 元层原则（SOUL.md），userProfile = 用户档案（USER.md），memoryNotes = 记忆笔记（MEMORY.md）。所有角色共享，修改后自动保存。",
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": ["soul", "userProfile", "memoryNotes"],
                    "description": "要修改的字段：soul（元层原则）、userProfile（用户档案）、memoryNotes（记忆笔记）",
                },
                "value": {
                    "type": "string",
                    "description": "新的内容（Markdown）",
                },
            },
            "required": ["field", "value"],
        },
    },
}
