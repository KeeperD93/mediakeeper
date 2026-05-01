import asyncio
import logging
import psutil
import shutil

logger = logging.getLogger("mediakeeper.system")


def _collect_stats() -> dict:
    """Collect system stats (blocking — called from a thread)."""
    cpu_percent = psutil.cpu_percent(interval=1)

    ram = psutil.virtual_memory()
    ram_used_gb  = round(ram.used / (1024 ** 3), 1)
    ram_total_gb = round(ram.total / (1024 ** 3), 1)

    disk = shutil.disk_usage("/")
    disk_used_gb  = round(disk.used / (1024 ** 3), 1)
    disk_total_gb = round(disk.total / (1024 ** 3), 1)
    disk_free_gb  = round(disk.free / (1024 ** 3), 1)
    disk_percent  = round((disk.used / disk.total) * 100, 1)

    return {
        "cpu": {
            "percent": cpu_percent,
            "label": f"{cpu_percent}%",
        },
        "ram": {
            "used_gb":  ram_used_gb,
            "total_gb": ram_total_gb,
            "percent":  ram.percent,
            "label":    f"{ram_used_gb} Go / {ram_total_gb} Go",
        },
        "storage": {
            "used_gb":  disk_used_gb,
            "total_gb": disk_total_gb,
            "free_gb":  disk_free_gb,
            "percent":  disk_percent,
            "label":    f"{disk_free_gb} Go libres",
        },
    }


async def get_system_stats() -> dict:
    """Version async — execute la collecte in un thread for ne pas bloquer l'event loop."""
    try:
        return await asyncio.to_thread(_collect_stats)
    except Exception as e:
        logger.error(f"[SYSTEM] Error collecte stats: {e}")
        return {"cpu": {}, "ram": {}, "storage": {}}
