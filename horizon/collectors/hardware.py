"""Cross-platform hardware telemetry with graceful Windows fallbacks."""
from __future__ import annotations

import csv
import io
import shutil
import subprocess
from typing import Any

import psutil


def collect_disk_info() -> list[dict[str, Any]]:
    """Return usage and I/O counters for mounted disks."""
    disks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for partition in psutil.disk_partitions(all=False):
        mount = partition.mountpoint
        if mount in seen:
            continue
        seen.add(mount)
        try:
            usage = psutil.disk_usage(mount)
            disks.append({
                "device": partition.device or mount,
                "mountpoint": mount,
                "filesystem": partition.fstype or "Unknown",
                "total": int(usage.total),
                "used": int(usage.used),
                "free": int(usage.free),
                "percent": float(usage.percent),
            })
        except (PermissionError, OSError):
            continue

    try:
        io = psutil.disk_io_counters()
    except (OSError, RuntimeError):
        io = None
    if io is not None:
        for disk in disks:
            disk["read_bytes"] = int(io.read_bytes)
            disk["write_bytes"] = int(io.write_bytes)
    return disks


def collect_network_info() -> dict[str, Any]:
    """Return aggregate network traffic counters and per-interface status."""
    counters = psutil.net_io_counters()
    interfaces = psutil.net_if_stats()
    per_interface = []
    for name, stats in interfaces.items():
        per_interface.append({
            "name": name,
            "is_up": bool(stats.isup),
            "speed_mbps": int(stats.speed or 0),
        })
    return {
        "bytes_sent": int(counters.bytes_sent),
        "bytes_received": int(counters.bytes_recv),
        "packets_sent": int(counters.packets_sent),
        "packets_received": int(counters.packets_recv),
        "interfaces": per_interface,
    }


def collect_temperature_info() -> dict[str, list[dict[str, Any]]]:
    """Read temperatures exposed by platform sensor drivers.

    Windows systems often require vendor drivers/utilities to expose sensors.
    An empty result means the operating system did not expose readable sensors.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False) or {}
    except (AttributeError, NotImplementedError, OSError):
        return result

    for sensor_group, readings in sensors.items():
        result[sensor_group] = [
            {
                "label": reading.label or sensor_group,
                "current": float(reading.current),
                "high": float(reading.high) if reading.high is not None else None,
                "critical": float(reading.critical) if reading.critical is not None else None,
            }
            for reading in readings
            if reading.current is not None
        ]
    return result


def collect_gpu_info() -> list[dict[str, Any]]:
    """Collect NVIDIA telemetry when the official nvidia-smi utility is available."""
    executable = shutil.which("nvidia-smi")
    if not executable:
        return []
    command = [
        executable,
        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=3, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []

    gpus: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(completed.stdout)):
        if len(row) != 5:
            continue
        try:
            gpus.append({
                "name": row[0].strip(),
                "utilization": float(row[1].strip()),
                "memory_used_mb": float(row[2].strip()),
                "memory_total_mb": float(row[3].strip()),
                "temperature_c": float(row[4].strip()),
            })
        except ValueError:
            continue
    return gpus
