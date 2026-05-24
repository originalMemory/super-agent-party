"""
按主机 OS/架构下载并缓存 wangfenjin/simple 预编译发行包（本模块固定 tag）。
供 ``lover_memory_options`` 用于 FTS5 中文分词。

缓存目录：``USER_DATA_DIR/lover/_fts5_simple/<tag>/``。下载前会先探测 ``<tag>/`` 下
各解压子目录能否 ``load_extension``，以便在 ``platform.machine()`` 推断 zip 不准时
（例如 Windows ARM 上跑 x64 Python）仍能复用手动解压的其他架构包。

若本进程 ABI 无匹配二进制，加载失败则 FTS 回退到 trigram/unicode61（既有行为）。
"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from py.get_setting import LOVER_DATA_DIR

logger = logging.getLogger(__name__)

# 固定发行版本；上游验证新资源/ABI 后手动 bump
SIMPLE_RELEASE_TAG = "v0.7.1"
_DOWNLOAD_BASE = f"https://github.com/wangfenjin/simple/releases/download/{SIMPLE_RELEASE_TAG}"

_AUTO_SIMPLE_DONE = False
_AUTO_SIMPLE_PATH = ""


def _pick_asset_zip() -> str | None:
    """按当前平台与 CPU 架构选择对应的 zip 资源名。"""
    plat = sys.platform
    mach = platform.machine().lower()
    if plat == "win32":
        if mach in ("amd64", "x86_64"):
            return "libsimple-windows-x64.zip"
        if mach in ("arm64", "aarch64"):
            return "libsimple-windows-arm64.zip"
        if mach in ("x86", "i386", "i686"):
            return "libsimple-windows-x86.zip"
        return "libsimple-windows-x64.zip"
    if plat == "darwin":
        if mach in ("arm64", "aarch64"):
            return "libsimple-osx-arm64.zip"
        return "libsimple-osx-x64.zip"
    if plat.startswith("linux"):
        if mach in ("aarch64", "arm64"):
            return "libsimple-linux-ubuntu-24.04-arm.zip"
        return "libsimple-linux-ubuntu-latest.zip"
    return None


# 各平台 simple 扩展库可能的文件名
_LIB_NAMES = (
    "simple.dll",
    "libsimple.dll",
    "simple.so",
    "libsimple.so",
    "simple.dylib",
    "libsimple.dylib",
)


def _discover_binary(root: Path) -> Path | None:
    """在目录树中递归查找 simple 扩展库二进制。"""
    for name in _LIB_NAMES:
        for p in root.rglob(name):
            if p.is_file():
                return p
    return None


def _simple_release_tag_root() -> Path:
    """当前发行 tag 的缓存根目录。"""
    return Path(LOVER_DATA_DIR) / "_fts5_simple" / SIMPLE_RELEASE_TAG


def _preferred_extract_dir_name() -> str | None:
    """按平台推断的首选解压目录名（zip 去掉 .zip 后缀）。"""
    asset = _pick_asset_zip()
    return asset[:-4] if asset else None


def _sorted_extract_dirs_under_tag() -> list[Path]:
    """列出 tag 下所有解压目录，首选目录排在前面。"""
    root = _simple_release_tag_root()
    if not root.is_dir():
        return []
    pref = _preferred_extract_dir_name()
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(
        key=lambda d: (0 if pref and d.name == pref else 1, d.name.lower()),
    )
    return dirs


def _pick_first_loadable_cached_simple(*, log_choice: bool) -> Path | None:
    """
    遍历本 tag 下各解压目录，返回第一个能被本进程 load_extension 的库路径。

    Windows 上即使用 ARM 机器，x64 Python 的 platform.machine() 也常返回 AMD64，
    推断 zip 目录可能不存在，但其他架构的手动解压目录仍可能被选中——
    只有真正能在当前进程加载的 DLL 才会返回。
    """
    pref = _preferred_extract_dir_name()
    for dest_dir in _sorted_extract_dirs_under_tag():
        found = _discover_binary(dest_dir)
        if not found or not _probe_load(found):
            continue
        if log_choice:
            if pref and dest_dir.name != pref:
                logger.info(
                    "[lover/simple] 使用本地缓存 %s（解压目录=%s；platform.machine()=%s，推断 zip 目录名=%s）",
                    found,
                    dest_dir.name,
                    platform.machine(),
                    pref,
                )
            else:
                logger.info("[lover/simple] 使用本地缓存 %s", found)
        return found
    return None


def probe_simple_extension_loads(path: str) -> bool:
    """路径存在且能被当前 Python 自带 sqlite3 load_extension 时为 True。"""
    if not path or not Path(path).is_file():
        return False
    return _probe_load(Path(path))


def _probe_load(lib_path: Path) -> bool:
    """尝试 load_extension，验证二进制是否与本进程 SQLite ABI 兼容。"""
    try:
        import sqlite3

        conn = sqlite3.connect(":memory:")
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            conn.close()
            return False
        try:
            conn.load_extension(str(lib_path))
        except sqlite3.OperationalError:
            conn.close()
            return False
        conn.close()
        return True
    except Exception:
        return False


def get_cached_simple_extension_path() -> str:
    """返回已解压且可加载的库路径，无则返回空字符串；不发起网络请求。"""
    if not _pick_asset_zip():
        return ""
    found = _pick_first_loadable_cached_simple(log_choice=False)
    return str(found) if found else ""


def _ensure_extracted(asset: str) -> Path | None:
    """确保 zip 已下载解压且库可加载；失败返回 None。"""
    cached = _pick_first_loadable_cached_simple(log_choice=True)
    if cached:
        return cached

    stem = asset[:-4]
    tag_root = _simple_release_tag_root()
    dest_dir = tag_root / stem
    if dest_dir.is_dir():
        found = _discover_binary(dest_dir)
        if found and _probe_load(found):
            logger.info("[lover/simple] 使用本地缓存 %s", found)
            return found
        shutil.rmtree(dest_dir, ignore_errors=True)

    url = f"{_DOWNLOAD_BASE}/{asset}"
    logger.info("[lover/simple] 正在下载 %s", url)
    try:
        req = Request(url, headers={"User-Agent": "Super-Agent-Party/lover-fts-simple"})
        with urlopen(req, timeout=180) as resp:
            data = resp.read()
    except URLError as e:
        logger.warning("[lover/simple] 下载失败：%s", e)
        return None
    except Exception as e:
        logger.warning("[lover/simple] 下载失败：%s", e)
        return None

    tag_root.mkdir(parents=True, exist_ok=True)
    tmp_zip = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
            tf.write(data)
            tmp_zip = tf.name
        # zip 内已含名为 stem 的顶层目录，解压到 tag 根即可，避免目录重名嵌套
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(tag_root)
    except zipfile.BadZipFile as e:
        logger.warning("[lover/simple] zip 文件损坏：%s", e)
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None
    finally:
        if tmp_zip:
            try:
                Path(tmp_zip).unlink(missing_ok=True)
            except OSError:
                pass

    found = _discover_binary(dest_dir)
    if not found:
        logger.warning("[lover/simple] 解压目录中未找到 simple 扩展库（.dll / .so / .dylib）")
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None
    if not _probe_load(found):
        logger.warning(
            "[lover/simple] 扩展无法用当前 Python 自带的 SQLite 加载，将使用 FTS 内置分词回退"
        )
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None
    logger.info("[lover/simple] 就绪 %s", found)
    return found


def ensure_simple_extension_downloaded() -> str:
    """按需下载/解压/缓存；返回可加载库路径，失败返回空字符串。"""
    asset = _pick_asset_zip()
    if not asset:
        logger.info("[lover/simple] 当前平台未配置对应的发行 zip 资源")
        return ""
    lib = _ensure_extracted(asset)
    return str(lib) if lib else ""


def get_auto_simple_extension_path() -> str:
    """进程内至多执行一次下载逻辑。"""
    global _AUTO_SIMPLE_DONE, _AUTO_SIMPLE_PATH
    if _AUTO_SIMPLE_DONE:
        return _AUTO_SIMPLE_PATH
    _AUTO_SIMPLE_DONE = True
    _AUTO_SIMPLE_PATH = ensure_simple_extension_downloaded()
    return _AUTO_SIMPLE_PATH
