"""Local SQLite telemetry history."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    """Use the current user's local application data directory."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base) / "HORIZION"
    else:
        root = Path.home() / ".local" / "share" / "HORIZION"
    root.mkdir(parents=True, exist_ok=True)
    return root / "history.sqlite3"


class MetricsHistory:
    """Persist timestamped metric snapshots in a local SQLite database."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path) if database_path else default_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=5)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_read_bytes INTEGER,
                    disk_write_bytes INTEGER,
                    network_sent_bytes INTEGER,
                    network_received_bytes INTEGER
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_metric_samples_timestamp "
                "ON metric_samples(timestamp)"
            )

    def record(self, metrics: dict[str, Any]) -> None:
        """Store one snapshot; missing values remain NULL."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO metric_samples (
                    timestamp, cpu_percent, memory_percent, disk_read_bytes,
                    disk_write_bytes, network_sent_bytes, network_received_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    metrics.get("cpu_percent"),
                    metrics.get("memory_percent"),
                    metrics.get("disk_read_bytes"),
                    metrics.get("disk_write_bytes"),
                    metrics.get("network_sent_bytes"),
                    metrics.get("network_received_bytes"),
                ),
            )

    def recent(self, limit: int = 300) -> list[dict[str, Any]]:
        """Return the newest samples in chronological order."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT timestamp, cpu_percent, memory_percent, disk_read_bytes,
                       disk_write_bytes, network_sent_bytes, network_received_bytes
                FROM metric_samples
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        keys = (
            "timestamp", "cpu_percent", "memory_percent", "disk_read_bytes",
            "disk_write_bytes", "network_sent_bytes", "network_received_bytes",
        )
        return [dict(zip(keys, row)) for row in reversed(rows)]
