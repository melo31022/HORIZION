"""Main HORIZION desktop window with live hardware telemetry and history charts."""
from __future__ import annotations

from collections import deque
from typing import Iterable

import psutil
from PySide6.QtCore import QTimer, Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from horizon.collectors.hardware import (
    collect_disk_info, collect_gpu_info, collect_network_info,
    collect_temperature_info,
)
from horizon.collectors.performance import collect_cpu_usage, collect_memory_info, format_bytes
from horizon.collectors.system import collect_system_info
from horizon.history import MetricsHistory

DARK_STYLE = """
QWidget { background: #11151b; color: #e6edf5; font-family: Segoe UI; font-size: 10pt; }
QMainWindow { background: #11151b; }
QFrame#Panel { background: #1a212b; border: 1px solid #293545; border-radius: 10px; }
QLabel#Muted { color: #91a0b3; }
QLabel#Metric { color: #f2f6fc; font-size: 21pt; font-weight: 600; }
QLabel#Heading { color: #80b7ff; font-size: 10pt; font-weight: 600; }
QComboBox { background: #202a36; border: 1px solid #35465a; padding: 6px; border-radius: 5px; }
QProgressBar { background: #263241; border: 0; border-radius: 4px; text-align: center; min-height: 12px; }
QProgressBar::chunk { background: #5598e8; border-radius: 4px; }
"""


class MetricPanel(QFrame):
    def __init__(self, title: str, value: str = "—") -> None:
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("Heading")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("Metric")
        self.detail_label = QLabel("Waiting for first reading")
        self.detail_label.setObjectName("Muted")
        self.detail_label.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)


class HistoryChart(QWidget):
    """Small dependency-free line chart rendered with Qt."""

    def __init__(self, title: str, color: str, suffix: str = "%") -> None:
        super().__init__()
        self.title = title
        self.color = QColor(color)
        self.suffix = suffix
        self.values: deque[float] = deque(maxlen=90)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def add_value(self, value: float) -> None:
        self.values.append(max(0.0, float(value)))
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#80b7ff"))
        painter.drawText(4, 16, self.title)
        area = self.rect().adjusted(8, 26, -8, -18)
        painter.setPen(QPen(QColor("#344252"), 1))
        for fraction in (0.0, 0.5, 1.0):
            y = area.bottom() - fraction * area.height()
            painter.drawLine(area.left(), int(y), area.right(), int(y))
        if len(self.values) < 2:
            painter.setPen(QColor("#91a0b3"))
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "Collecting history…")
            return
        maximum = max(max(self.values), 1.0)
        points = [
            QPointF(
                area.left() + i * area.width() / (len(self.values) - 1),
                area.bottom() - (value / maximum) * area.height(),
            )
            for i, value in enumerate(self.values)
        ]
        painter.setPen(QPen(self.color, 2))
        for first, second in zip(points, points[1:]):
            painter.drawLine(first, second)
        painter.setPen(QColor("#c5d1df"))
        painter.drawText(area.adjusted(0, 0, -2, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                         f"{self.values[-1]:.1f}{self.suffix}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HORIZION — System Monitor")
        self.resize(1100, 850)
        self.setMinimumSize(800, 650)
        self.setStyleSheet(DARK_STYLE)
        self.history = MetricsHistory()
        self._previous_disk = psutil.disk_io_counters()
        self._previous_network = psutil.net_io_counters()
        self._previous_tick = 0

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 16, 18, 12)
        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("HORIZION")
        title.setStyleSheet("font-size: 25pt; font-weight: 700; letter-spacing: 2px;")
        subtitle = QLabel("SYSTEM MONITOR  /  VERSION 0.1 DEV")
        subtitle.setObjectName("Muted")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.mode = QComboBox()
        self.mode.addItems(["Basic mode", "Advanced mode"])
        self.mode.currentIndexChanged.connect(self._change_mode)
        header.addWidget(self.mode)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(12)

        cards = QGridLayout()
        cards.setSpacing(12)
        self.cpu = MetricPanel("PROCESSOR LOAD")
        self.memory = MetricPanel("MEMORY USAGE")
        self.gpu = MetricPanel("GPU")
        self.network = MetricPanel("NETWORK")
        for i, panel in enumerate((self.cpu, self.memory, self.gpu, self.network)):
            cards.addWidget(panel, i // 2, i % 2)
        root.addLayout(cards)

        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setFormat("Memory utilization: %p%")
        root.addWidget(self.memory_bar)

        chart_grid = QGridLayout()
        self.cpu_chart = HistoryChart("CPU HISTORY", "#59a5ff")
        self.memory_chart = HistoryChart("MEMORY HISTORY", "#b18cff")
        self.network_chart = HistoryChart("NETWORK RECEIVE", "#52c7a5", " MB/s")
        self.disk_chart = HistoryChart("DISK READ", "#e5b65c", " MB/s")
        for i, chart in enumerate((self.cpu_chart, self.memory_chart, self.network_chart, self.disk_chart)):
            panel = QFrame()
            panel.setObjectName("Panel")
            layout = QVBoxLayout(panel)
            layout.addWidget(chart)
            chart_grid.addWidget(panel, i // 2, i % 2)
        root.addLayout(chart_grid)

        self.advanced_panel = QFrame()
        self.advanced_panel.setObjectName("Panel")
        advanced_layout = QVBoxLayout(self.advanced_panel)
        heading = QLabel("HARDWARE DETAILS")
        heading.setObjectName("Heading")
        advanced_layout.addWidget(heading)
        self.hardware_details = QLabel("Collecting hardware information…")
        self.hardware_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.hardware_details.setWordWrap(True)
        advanced_layout.addWidget(self.hardware_details)
        root.addWidget(self.advanced_panel)

        system_panel = QFrame()
        system_panel.setObjectName("Panel")
        system_layout = QVBoxLayout(system_panel)
        system_heading = QLabel("SYSTEM INFORMATION")
        system_heading.setObjectName("Heading")
        system_layout.addWidget(system_heading)
        self.system_labels: dict[str, QLabel] = {}
        info_grid = QGridLayout()
        for index, (key, value) in enumerate(collect_system_info().items()):
            name = QLabel(key)
            name.setObjectName("Muted")
            content = QLabel(value)
            content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content.setWordWrap(True)
            info_grid.addWidget(name, index, 0)
            info_grid.addWidget(content, index, 1)
            self.system_labels[key] = content
        system_layout.addLayout(info_grid)
        root.addWidget(system_panel)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.status = QLabel("Local collection active • Refreshing every second • History saved on this PC")
        self.status.setObjectName("Muted")
        outer.addWidget(self.status)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(1000)
        self.refresh_metrics()

    def _change_mode(self, index: int) -> None:
        advanced = index == 1
        self.advanced_panel.setVisible(advanced)
        for key, label in self.system_labels.items():
            label.setVisible(advanced or key in {"Operating system", "Processor", "Architecture"})

    def refresh_metrics(self) -> None:
        try:
            cpu = collect_cpu_usage()
            memory = collect_memory_info()
            network = collect_network_info()
            disks = collect_disk_info()
            gpus = collect_gpu_info()
            temperatures = collect_temperature_info()

            self.cpu.value_label.setText(f"{cpu:.0f}%")
            self.cpu.detail_label.setText(f"{psutil.cpu_count(logical=True) or '—'} logical processors")
            self.memory.value_label.setText(f"{memory['percent']:.0f}%")
            self.memory.detail_label.setText(f"{format_bytes(memory['used'])} used / {format_bytes(memory['total'])}")
            self.memory_bar.setValue(round(memory["percent"]))

            if gpus:
                gpu = gpus[0]
                self.gpu.value_label.setText(f"{gpu['utilization']:.0f}%")
                self.gpu.detail_label.setText(
                    f"{gpu['name']} • {gpu['temperature_c']:.0f} °C • "
                    f"{gpu['memory_used_mb']:.0f}/{gpu['memory_total_mb']:.0f} MB VRAM"
                )
            else:
                self.gpu.value_label.setText("Unavailable")
                self.gpu.detail_label.setText("No supported NVIDIA telemetry source detected")

            sent_rate = received_rate = read_rate = write_rate = 0.0
            current_disk = psutil.disk_io_counters()
            current_network = psutil.net_io_counters()
            if self._previous_network and current_network:
                sent_rate = max(0, current_network.bytes_sent - self._previous_network.bytes_sent) / 1048576
                received_rate = max(0, current_network.bytes_recv - self._previous_network.bytes_recv) / 1048576
            if self._previous_disk and current_disk:
                read_rate = max(0, current_disk.read_bytes - self._previous_disk.read_bytes) / 1048576
                write_rate = max(0, current_disk.write_bytes - self._previous_disk.write_bytes) / 1048576
            self._previous_network, self._previous_disk = current_network, current_disk

            self.network.value_label.setText(f"↓ {received_rate:.2f} MB/s")
            self.network.detail_label.setText(f"↑ {sent_rate:.2f} MB/s sent")
            self.cpu_chart.add_value(cpu)
            self.memory_chart.add_value(float(memory["percent"]))
            self.network_chart.add_value(received_rate)
            self.disk_chart.add_value(read_rate)

            disk_lines = [
                f"{disk['mountpoint']} — {disk['percent']:.0f}% used "
                f"({format_bytes(disk['free'])} free / {format_bytes(disk['total'])})"
                for disk in disks
            ] or ["No readable disk volumes"]
            gpu_lines = [
                f"GPU: {item['name']} — {item['utilization']:.0f}% • {item['temperature_c']:.0f} °C"
                for item in gpus
            ] or ["GPU: telemetry unavailable (NVIDIA nvidia-smi supported in this build)"]
            temp_lines = [
                f"Temperature {reading['label']}: {reading['current']:.1f} °C"
                for group in temperatures.values() for reading in group
            ] or ["Temperatures: no sensors exposed by this OS/driver"]
            interface_lines = [
                f"Network {item['name']}: {'connected' if item['is_up'] else 'disconnected'}"
                for item in network["interfaces"]
            ]
            detail_text = (
                "DISKS\n" + "\n".join(disk_lines) +
                "\n\nDISK I/O\n" + f"Read {read_rate:.2f} MB/s • Write {write_rate:.2f} MB/s" +
                "\n\nGPU\n" + "\n".join(gpu_lines) +
                "\n\nTEMPERATURES\n" + "\n".join(temp_lines) +
                "\n\nNETWORK INTERFACES\n" + ("\n".join(interface_lines) or "No interfaces reported") +
                "\n\nNETWORK TOTALS\n" + f"Received {format_bytes(network['bytes_received'])} • Sent {format_bytes(network['bytes_sent'])}"
            )
            self.hardware_details.setText(detail_text)

            self.history.record({
                "cpu_percent": cpu,
                "memory_percent": memory["percent"],
                "disk_read_bytes": current_disk.read_bytes if current_disk else None,
                "disk_write_bytes": current_disk.write_bytes if current_disk else None,
                "network_sent_bytes": network["bytes_sent"],
                "network_received_bytes": network["bytes_received"],
            })
            self.status.setText("Monitoring active • Local history saved • No data sent over the internet")
        except (OSError, RuntimeError, ValueError) as exc:
            self.status.setText(f"Some metrics are temporarily unavailable: {exc}")
