"""CPU and memory usage collectors."""
from __future__ import annotations

import psutil


def collect_cpu_usage(interval: float | None = None) -> float:
    """Return total CPU utilization as a percentage."""
    return float(psutil.cpu_percent(interval=interval))


def collect_memory_info() -> dict[str, float | int]:
    """Return memory totals and utilization in bytes and percent."""
    memory = psutil.virtual_memory()
    return {
        "total": int(memory.total),
        "available": int(memory.available),
        "used": int(memory.used),
        "percent": float(memory.percent),
    }


def format_bytes(value: int) -> str:
    """Format a byte count using binary units."""
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"
