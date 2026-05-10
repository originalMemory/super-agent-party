"""
Fetch/cache a prebuilt `wangfenjin/simple` release matching the host OS/arch
(fixed tag in this module). Used by ``lover_memory_options`` for FTS5 tokenization.

Caches under ``USER_DATA_DIR/lover/_fts5_simple/<tag>/``. Before downloading, every
extract subfolder under ``<tag>/`` is probed with ``load_extension`` so a manually
unzipped arch (e.g. ``libsimple-windows-arm64``) is picked up even when
``platform.machine()`` suggests a different zip.

Load may still fail if no binary matches this process ABI — then FTS falls back to
trigram/unicode61 (existing behavior).
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

# Pinned release — bump when verifying new assets / ABI notes upstream.
SIMPLE_RELEASE_TAG = "v0.7.1"
_DOWNLOAD_BASE = f"https://github.com/wangfenjin/simple/releases/download/{SIMPLE_RELEASE_TAG}"

_AUTO_SIMPLE_DONE = False
_AUTO_SIMPLE_PATH = ""


def _pick_asset_zip() -> str | None:
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


_LIB_NAMES = (
    "simple.dll",
    "libsimple.dll",
    "simple.so",
    "libsimple.so",
    "simple.dylib",
)


def _discover_binary(root: Path) -> Path | None:
    for name in _LIB_NAMES:
        for p in root.rglob(name):
            if p.is_file():
                return p
    return None


def _simple_release_tag_root() -> Path:
    return Path(LOVER_DATA_DIR) / "_fts5_simple" / SIMPLE_RELEASE_TAG


def _preferred_extract_dir_name() -> str | None:
    asset = _pick_asset_zip()
    return asset[:-4] if asset else None


def _sorted_extract_dirs_under_tag() -> list[Path]:
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
    Try every extracted folder under this release tag (any arch zip stem).

    On Windows, ``platform.machine()`` is often ``AMD64`` even on ARM machines when
    running an x64 Python build, so the preferred folder may not exist while another
    arch's extract (e.g. ``libsimple-windows-arm64``) is present — but only a DLL that
    actually ``load_extension``s in *this* process is returned.
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
    """True if ``path`` exists and can be ``load_extension``'d by this Python's sqlite3."""
    if not path or not Path(path).is_file():
        return False
    return _probe_load(Path(path))


def _probe_load(lib_path: Path) -> bool:
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
    """Return an already-extracted loadable binary path, or ``\"\"``. No network I/O."""
    if not _pick_asset_zip():
        return ""
    found = _pick_first_loadable_cached_simple(log_choice=False)
    return str(found) if found else ""


def _ensure_extracted(asset: str) -> Path | None:
    cached = _pick_first_loadable_cached_simple(log_choice=True)
    if cached:
        return cached

    stem = asset[:-4]
    dest_dir = Path(LOVER_DATA_DIR) / "_fts5_simple" / SIMPLE_RELEASE_TAG / stem
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

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
            tf.write(data)
            tmp_zip = tf.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(dest_dir)
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
        logger.warning("[lover/simple] 解压目录中未找到 simple.dll / simple.so")
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
    """Download/extract/cache if needed; return path to loadable library or ``\"\"``."""
    asset = _pick_asset_zip()
    if not asset:
        logger.info("[lover/simple] 当前平台未配置对应的发行 zip 资源")
        return ""
    lib = _ensure_extracted(asset)
    return str(lib) if lib else ""


def get_auto_simple_extension_path() -> str:
    """Run download/logic at most once per process."""
    global _AUTO_SIMPLE_DONE, _AUTO_SIMPLE_PATH
    if _AUTO_SIMPLE_DONE:
        return _AUTO_SIMPLE_PATH
    _AUTO_SIMPLE_DONE = True
    _AUTO_SIMPLE_PATH = ensure_simple_extension_downloaded()
    return _AUTO_SIMPLE_PATH
