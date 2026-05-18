"""
Workspace Markdown memory index (SQLite FTS5).

Indexes:
  - {lover_root}/MEMORY.md
  - {lover_root}/memory/ 下任意 ``.md``（递归子目录）

Index DB: {lover_root}/memory_index.sqlite

**Root directory**: ``USER_DATA_DIR/lover``（``py.get_setting.LOVER_DATA_DIR``）。与 ``CLISettings.cc_path`` **无关**；索引与人设/记忆 Markdown 同属用户数据目录下的 ``lover/``。

Tokenizer:
  - Prefer loading [wangfenjin/simple](https://github.com/wangfenjin/simple) from a
    release binary auto-downloaded/cached under ``lover/_fts5_simple/`` (see
    ``py/lover_fts_simple_auto.py``). New DBs then use ``tokenize='simple'`` and
    queries use ``simple_query()`` per upstream docs.
  - If download/load fails: built-in **trigram** → **unicode61** → default.

**Sync**: ``sync_memory_index(lover_root, options)`` — interval from settings via
``lover_memory_options``. **Search**: ``search_memory(..., options)`` loads the
extension when the existing table uses ``simple``.

If the **wangfenjin/simple** binary becomes loadable after the DB was built with a
built-in tokenizer (or vice versa), ``memory_fts`` is **dropped**, ``doc_meta`` is
cleared, and the next sync **re-indexes all** Markdown so tokens match the new
tokenizer (aligned with upstream README: ``tokenize = 'simple'`` + ``simple_query()``).
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any, NamedTuple

from py.get_setting import LOVER_DATA_DIR
from py.lover_fts_simple_auto import (
    get_auto_simple_extension_path,
    get_cached_simple_extension_path,
    probe_simple_extension_loads,
)

logger = logging.getLogger(__name__)

# Minimum sync interval (seconds) when settings are invalid.
_DEFAULT_SYNC_INTERVAL_SEC = 600

# Log tokenizer / extension path once per process (avoid spam on periodic sync).
_MEMORY_TOKENIZER_LOGGED = False


def _describe_memory_fts_tokenizer(conn: sqlite3.Connection) -> str:
    sql = _memory_fts_create_sql(conn)
    if not sql:
        return "none"
    if _memory_fts_uses_simple_tokenizer(conn):
        return "simple"
    m = re.search(r"tokenize\s*=\s*['\"]([^'\"]+)['\"]", sql, re.I)
    if m:
        return m.group(1).strip().lower()
    return "default"


def _tokenizer_label_zh(tok: str) -> str:
    return {
        "simple": "simple（wangfenjin 插件）",
        "trigram": "trigram（SQLite 内置）",
        "unicode61": "unicode61（SQLite 内置）",
        "default": "默认（SQLite 内置）",
        "none": "无",
    }.get(tok, tok)


def _log_memory_fts_tokenizer_once(conn: sqlite3.Connection, simple_extension_path: str) -> None:
    global _MEMORY_TOKENIZER_LOGGED
    if _MEMORY_TOKENIZER_LOGGED:
        return
    if not _memory_fts_create_sql(conn):
        return
    _MEMORY_TOKENIZER_LOGGED = True
    tok = _describe_memory_fts_tokenizer(conn)
    logger.info(
        "[lover/FTS] memory_index.sqlite 分词器=%s simple 扩展路径=%s",
        _tokenizer_label_zh(tok),
        simple_extension_path if simple_extension_path else "（无）",
    )


def lover_memory_options(settings: dict | None) -> dict[str, Any]:
    """Options from settings['memorySettings']; defaults match settings_template.json."""
    ms = (settings or {}).get("memorySettings") or {}
    minutes = ms.get("memoryIndexSyncMinutes", 10)
    try:
        interval_sec = int(float(minutes) * 60)
    except (TypeError, ValueError):
        interval_sec = _DEFAULT_SYNC_INTERVAL_SEC
    interval_sec = max(60, interval_sec)

    # Avoid network/download on the asyncio thread — sync_memory_index resolves full path in a worker.
    ext_path = get_cached_simple_extension_path()

    return {
        "fts5_simple_extension_path": ext_path,
        "sync_interval_sec": interval_sec,
    }


def lover_data_root() -> Path:
    """Lover SSOT + FTS 语料根目录：``USER_DATA_DIR/lover``。"""
    p = Path(LOVER_DATA_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def workspace_root_from_settings(settings: dict) -> Path | None:
    """Return memoryDirPath from settings if set, otherwise default lover_data_root()."""
    ms = (settings or {}).get("memorySettings") or {}
    custom = (ms.get("memoryDirPath") or "").strip()
    if custom:
        p = Path(custom)
        if p.is_absolute():
            p.mkdir(parents=True, exist_ok=True)
            return p
    return lover_data_root()


def _db_path(workspace: Path) -> Path:
    return workspace / "memory_index.sqlite"


def _list_memory_files(workspace: Path) -> list[Path]:
    """MEMORY.md + every ``.md`` under ``memory/`` (recursive)."""
    root = workspace.resolve()
    out: list[Path] = []
    mem = root / "MEMORY.md"
    if mem.is_file():
        out.append(mem)
    memory_root = root / "memory"
    if not memory_root.is_dir():
        return sorted(out)
    for p in memory_root.rglob("*.md"):
        if not p.is_file():
            continue
        try:
            p.relative_to(root)
        except ValueError:
            continue
        out.append(p)
    return sorted(out)


def _connect(workspace: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path(workspace)), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _try_load_fts_simple_extension(conn: sqlite3.Connection, path: str) -> bool:
    if not path or not Path(path).is_file():
        return False
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        return False
    try:
        conn.load_extension(path)
        return True
    except sqlite3.OperationalError:
        return False


def _memory_fts_create_sql(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_fts'"
    ).fetchone()
    return row[0] if row else None


def _memory_fts_uses_simple_tokenizer(conn: sqlite3.Connection) -> bool:
    sql = _memory_fts_create_sql(conn)
    if not sql:
        return False
    s = sql.lower()
    return "tokenize" in s and "simple" in s


def _maybe_rebuild_fts_for_tokenizer_change(
    conn: sqlite3.Connection, simple_extension_path: str
) -> None:
    """Drop FTS + doc_meta when simple vs built-in tokenizer no longer matches stored schema."""
    if not _memory_fts_create_sql(conn):
        return
    want_simple = probe_simple_extension_loads(simple_extension_path)
    have_simple = _memory_fts_uses_simple_tokenizer(conn)
    if want_simple == have_simple:
        return
    logger.info(
        "[lover/FTS] 分词目标已变更（当前表是否为 simple=%s，期望使用 simple=%s），正在重建 memory_fts",
        have_simple,
        want_simple,
    )
    conn.execute("DROP TABLE IF EXISTS memory_fts")
    conn.execute("DELETE FROM doc_meta")


def _ensure_schema(conn: sqlite3.Connection, simple_extension_path: str = "") -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS doc_meta(
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            size INTEGER NOT NULL
        )
        """
    )
    _maybe_rebuild_fts_for_tokenizer_change(conn, simple_extension_path)
    if _memory_fts_create_sql(conn):
        # 每张连接都要 load_extension，否则会句「no such tokenizer: simple」
        if _memory_fts_uses_simple_tokenizer(conn):
            if simple_extension_path and _try_load_fts_simple_extension(
                conn, simple_extension_path
            ):
                return
            logger.warning(
                "[lover/FTS] 库中 memory_fts 使用 simple 分词，但本连接未能加载扩展（路径=%s），"
                "将删除 FTS 表并清空 doc_meta，改用内置分词重建",
                simple_extension_path or "（无）",
            )
            conn.execute("DROP TABLE IF EXISTS memory_fts")
            conn.execute("DELETE FROM doc_meta")
        else:
            return

    if simple_extension_path and _try_load_fts_simple_extension(
        conn, simple_extension_path
    ):
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    path UNINDEXED,
                    body,
                    tokenize = 'simple'
                )
                """
            )
            return
        except sqlite3.OperationalError:
            pass

    for tokenize in ("trigram", "unicode61"):
        try:
            conn.execute(
                f"""
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    path UNINDEXED,
                    body,
                    tokenize = '{tokenize}'
                )
                """
            )
            return
        except sqlite3.OperationalError:
            continue
    conn.execute(
        """
        CREATE VIRTUAL TABLE memory_fts USING fts5(
            path UNINDEXED,
            body
        )
        """
    )


class _SyncDocStats(NamedTuple):
    listed: int
    updated: int
    unchanged: int
    removed: int
    skipped_failed: int


def _sync_docs(conn: sqlite3.Connection, workspace: Path) -> _SyncDocStats:
    workspace = workspace.resolve()
    meta = {
        row[0]: (row[1], row[2])
        for row in conn.execute("SELECT path, mtime, size FROM doc_meta")
    }
    files = _list_memory_files(workspace)
    listed = len(files)
    updated = 0
    unchanged = 0
    skipped_failed = 0
    seen: set[str] = set()
    for fp in files:
        fp = fp.resolve()
        try:
            st = fp.stat()
        except OSError:
            skipped_failed += 1
            continue
        try:
            rel = str(fp.relative_to(workspace)).replace("\\", "/")
        except ValueError:
            skipped_failed += 1
            continue
        seen.add(rel)
        key = (st.st_mtime, st.st_size)
        if meta.get(rel) == key:
            unchanged += 1
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped_failed += 1
            continue
        conn.execute("DELETE FROM memory_fts WHERE path = ?", (rel,))
        conn.execute(
            "INSERT INTO memory_fts(path, body) VALUES (?, ?)", (rel, text)
        )
        conn.execute(
            """
            INSERT INTO doc_meta(path, mtime, size) VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime, size = excluded.size
            """,
            (rel, st.st_mtime, st.st_size),
        )
        updated += 1
    removed = 0
    for path in meta:
        if path not in seen:
            conn.execute("DELETE FROM memory_fts WHERE path = ?", (path,))
            conn.execute("DELETE FROM doc_meta WHERE path = ?", (path,))
            removed += 1
    return _SyncDocStats(
        listed=listed,
        updated=updated,
        unchanged=unchanged,
        removed=removed,
        skipped_failed=skipped_failed,
    )


def sync_memory_index(workspace: Path, options: dict | None = None) -> None:
    """Scan Markdown sources and update FTS rows (mtime/size)."""
    if not workspace.is_dir():
        return
    opts = options or {}
    ext_path = opts.get("fts5_simple_extension_path") or ""
    if not ext_path:
        ext_path = get_auto_simple_extension_path()
    workspace = workspace.resolve()
    conn = _connect(workspace)
    try:
        _ensure_schema(conn, ext_path)
        _log_memory_fts_tokenizer_once(conn, ext_path)
        stats = _sync_docs(conn, workspace)
        conn.commit()
        logger.info(
            "[lover/FTS] 记忆索引同步完成：扫描 %s 个 Markdown，写入/更新 %s 个，未变化跳过 %s 个，"
            "从索引移除 %s 个，读取或路径异常跳过 %s 个",
            stats.listed,
            stats.updated,
            stats.unchanged,
            stats.removed,
            stats.skipped_failed,
        )
    finally:
        conn.close()


def _fts5_quote_term(term: str) -> str:
    return '"' + term.replace('"', '""') + '"'


def _match_query_builtin(query: str) -> str:
    q = query.strip()
    if not q:
        return ""
    parts = [p for p in re.split(r"\s+", q) if p]
    if not parts:
        parts = [q]
    return " AND ".join(_fts5_quote_term(p) for p in parts)


def search_memory(
    workspace: Path,
    query: str,
    limit: int = 6,
    options: dict | None = None,
) -> list[dict[str, Any]]:
    """FTS5 search; load simple extension when table uses tokenize=simple."""
    if not workspace.is_dir():
        return []
    opts = options or {}
    ext_path = opts.get("fts5_simple_extension_path") or ""

    qraw = query.strip()
    if not qraw:
        return []

    workspace = workspace.resolve()
    conn = _connect(workspace)
    try:
        _ensure_schema(conn, ext_path)
        _log_memory_fts_tokenizer_once(conn, ext_path or get_cached_simple_extension_path())

        lim = max(1, int(limit))
        if _memory_fts_uses_simple_tokenizer(conn):
            if not ext_path or not _try_load_fts_simple_extension(conn, ext_path):
                return []
            try:
                cur = conn.execute(
                    """
                    SELECT path, snippet(memory_fts, 1, '【', '】', ' … ', 24) AS snip,
                           bm25(memory_fts) AS rank
                    FROM memory_fts
                    WHERE memory_fts MATCH simple_query(?)
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (qraw, lim),
                )
            except sqlite3.OperationalError:
                return []
        else:
            mq = _match_query_builtin(qraw)
            if not mq:
                return []
            try:
                cur = conn.execute(
                    """
                    SELECT path, snippet(memory_fts, 1, '【', '】', ' … ', 24) AS snip,
                           bm25(memory_fts) AS rank
                    FROM memory_fts
                    WHERE memory_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (mq, lim),
                )
            except sqlite3.OperationalError:
                return []

        rows = cur.fetchall()
        return [{"path": r[0], "snippet": r[1], "rank": r[2]} for r in rows]
    finally:
        conn.close()
