"""Operating system and machine information."""
from __future__ import annotations

import platform
from datetime import datetime


def collect_system_info() -> dict[str, str]:
    """Return system metadata without assuming every field is available."""
    try:
        boot_timestamp = __import__("psutil").boot_time()
        boot_time = datetime.fromtimestamp(boot_timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except (OSError, ValueError, ImportError):
        boot_time = "Unavailable"

    return {
        "Operating system": platform.system() or "Unavailable",
        "OS version": platform.version() or "Unavailable",
        "Release": platform.release() or "Unavailable",
        "Architecture": platform.machine() or "Unavailable",
        "Processor": platform.processor() or "Unavailable",
        "Computer name": platform.node() or "Unavailable",
        "Boot time": boot_time,
    }
