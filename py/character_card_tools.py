import json
from py.get_setting import load_settings, save_settings

WRITABLE_FIELDS = {"soul", "memoryNotes", "description", "personality", "systemPrompt", "mesExample"}


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

    result["userProfile"] = memory_settings.get("userProfile", "")
    return json.dumps(result, ensure_ascii=False)


async def update_character_card(field: str, value: str) -> str:
    if field not in WRITABLE_FIELDS:
        return json.dumps({
            "error": f"字段 '{field}' 不可修改，可写字段：{', '.join(sorted(WRITABLE_FIELDS))}"
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
    settings = await load_settings()
    settings.setdefault("memorySettings", {})["userProfile"] = value
    await save_settings(settings)
    return json.dumps({
        "success": True,
        "field": "userProfile",
        "length": len(value),
    }, ensure_ascii=False)


get_character_card_tool = {
    "type": "function",
    "function": {
        "name": "get_character_card",
        "description": "读取当前角色卡的信息。可指定字段名获取特定内容，不指定则返回全部。同时返回全局用户档案（_userProfile）。",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要读取的字段列表，如 ['soul', 'memoryNotes', 'description']。不传则返回全部字段。",
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
        "description": "修改当前角色卡的指定字段。可写字段：soul、memoryNotes、description、personality、systemPrompt、mesExample。修改后自动保存。",
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
        "description": "修改所有角色共享的用户档案（userProfile）。修改后自动保存。",
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
