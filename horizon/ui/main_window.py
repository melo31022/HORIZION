"""Main HORIZON desktop window."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QVBoxLayout, QWidget,
)

from horizon.collectors.performance import collect_cpu_usage, collect_memory_info, format_bytes
from horizon.collectors.system import collect_system_info

DARK_STYLE = """
QWidget { background: #11151b; color: #e6edf5; font-family: Segoe UI; font-size: 10pt; }
QMainWindow { background: #11151b; }
QFrame#Panel { background: #1a212b; border: 1px solid #293545; border-radius: 10px; }
QLabel#Muted { color: #91a0b3; }
QLabel#Metric { color: #f2f6fc; font-size: 23pt; font-weight: 600; }
QLabel#Heading { color: #80b7ff; font-size: 11pt; font-weight: 600; }
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
        layout.addWidget(heading)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HORIZON — System Monitor")
        self.resize(980, 680)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("HORIZON")
        title.setStyleSheet("font-size: 25pt; font-weight: 700; letter-spacing: 2px;")
        subtitle = QLabel("SYSTEM MONITOR  /  VERSION 0.1")
        subtitle.setObjectName("Muted")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.mode = QComboBox()
        self.mode.addItems(["Basic mode", "Advanced mode"])
        self.mode.currentIndexChanged.connect(self._change_mode)
        header.addWidget(self.mode)
        root.addLayout(header)

        cards = QGridLayout()
        cards.setSpacing(14)
        self.cpu = MetricPanel("PROCESSOR LOAD")
        self.memory = MetricPanel("MEMORY USAGE")
        cards.addWidget(self.cpu, 0, 0)
        cards.addWidget(self.memory, 0, 1)
        root.addLayout(cards)

        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setFormat("Memory utilization: %p%")
        root.addWidget(self.memory_bar)

        system_panel = QFrame()
        system_panel.setObjectName("Panel")
        system_layout = QVBoxLayout(system_panel)
        system_heading = QLabel("SYSTEM INFORMATION")
        system_heading.setObjectName("Heading")
        system_layout.addWidget(system_heading)
        self.system_labels: dict[str, QLabel] = {}
        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(24)
        info_grid.setVerticalSpacing(10)
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
        root.addStretch()

        self.status = QLabel("Local collection active • Refreshing every 1 second")
        self.status.setObjectName("Muted")
        root.addWidget(self.status)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(1000)
        self.refresh_metrics()

    def _change_mode(self, index: int) -> None:
        advanced = index == 1
        for key, label in self.system_labels.items():
            label.setVisible(advanced or key in {"Operating system", "Processor", "Architecture"})
        self.status.setText("Advanced mode" if advanced else "Basic mode")

    def refresh_metrics(self) -> None:
        try:
            cpu = collect_cpu_usage()
            memory = collect_memory_info()
            self.cpu.value_label.setText(f"{cpu:.0f}%")
            self.cpu.detail_label.setText(f"{__import__('psutil').cpu_count(logical=True) or '—'} logical processors")
            self.memory.value_label.setText(f"{memory['percent']:.0f}%")
            self.memory.detail_label.setText(
                f"{format_bytes(memory['used'])} used / {format_bytes(memory['total'])}"
            )
            self.memory_bar.setValue(round(memory["percent"]))
        except (OSError, RuntimeError) as exc:
            self.status.setText(f"Collection unavailable: {exc}")
