"""Asynchronous filesystem operations — portable move / delete."""
import os
import stat
import asyncio
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("mediakeeper.media_manager")


def _same_device(p1: Path, p2: Path) -> bool:
    """Check whether two paths share the same filesystem device."""
    try:
        return os.stat(p1).st_dev == os.stat(p2).st_dev
    except OSError:
        return False


def _sync_move(src: str, target: str) -> None:
    """
    Move portable :
    - Same device -> os.replace(): atomic, instant (simple kernel-level rename)
    - Different devices -> shutil.move() in a thread (physical copy unavoidable)
    os.replace() functionne sur Linux, macOS et Windows.
    """
    src_p = Path(src)
    target_p = Path(target)
    dest_ref = target_p.parent if not target_p.exists() else target_p
    if _same_device(src_p, dest_ref):
        logger.debug(f"[MOVE] os.replace : {src!r} → {target!r}")
        os.replace(src, target)
    else:
        logger.debug(f"[MOVE] shutil.move (cross-device) : {src!r} → {target!r}")
        shutil.move(src, target)


async def _fast_move(src: str, target: str) -> None:
    """Move asynchrone — non-blocking for uvicorn."""
    await asyncio.to_thread(_sync_move, src, target)


def _sync_delete(path: Path) -> None:
    """
    Deletion portable with management des permissions en playback seule.
    Functionne sur Linux, macOS et Windows.
    """
    def _onerror(func, fpath, _exc):
        try:
            logger.warning(f"[DELETE] Permission refusede sur {fpath!r}, attempting chmod")
            os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
            func(fpath)
        except Exception as e:
            raise OSError(f"Impossible de supprimer {fpath} : {e}")

    if path.is_dir():
        logger.debug(f"[DELETE] rmtree : {path!r}")
        shutil.rmtree(str(path), onerror=_onerror)
    else:
        logger.debug(f"[DELETE] unlink : {path!r}")
        try:
            path.unlink()
        except PermissionError:
            logger.warning(f"[DELETE] Permission refusede sur {path!r}, attempting chmod")
            os.chmod(str(path), stat.S_IWRITE | stat.S_IREAD)
            path.unlink()


async def _force_delete(path: Path) -> None:
    """Deletion asynchrone — non-blocking for uvicorn."""
    await asyncio.to_thread(_sync_delete, path)
