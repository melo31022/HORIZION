from horizon.collectors.hardware import (
    collect_disk_info, collect_gpu_info, collect_network_info,
    collect_temperature_info,
)
from horizon.collectors.performance import collect_memory_info, format_bytes
from horizon.collectors.system import collect_system_info
from horizon.history import MetricsHistory


def test_memory_collector_returns_valid_values():
    result = collect_memory_info()
    assert result["total"] > 0
    assert 0 <= result["percent"] <= 100
    assert result["used"] >= 0
    assert result["available"] >= 0


def test_system_collector_returns_expected_fields():
    result = collect_system_info()
    assert "Operating system" in result
    assert "Architecture" in result
    assert all(isinstance(value, str) and value for value in result.values())


def test_format_bytes():
    assert format_bytes(0) == "0.0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"


def test_disk_collector_returns_list():
    result = collect_disk_info()
    assert isinstance(result, list)
    for disk in result:
        assert 0 <= disk["percent"] <= 100
        assert disk["total"] >= disk["used"]


def test_network_collector_returns_counters():
    result = collect_network_info()
    assert result["bytes_sent"] >= 0
    assert result["bytes_received"] >= 0
    assert isinstance(result["interfaces"], list)


def test_optional_hardware_collectors_return_lists_or_dicts():
    assert isinstance(collect_gpu_info(), list)
    assert isinstance(collect_temperature_info(), dict)


def test_metrics_history_round_trip(tmp_path):
    history = MetricsHistory(tmp_path / "history.sqlite3")
    history.record({
        "cpu_percent": 12.5,
        "memory_percent": 42.0,
        "network_sent_bytes": 100,
    })
    samples = history.recent()
    assert len(samples) == 1
    assert samples[0]["cpu_percent"] == 12.5
    assert samples[0]["memory_percent"] == 42.0
    assert samples[0]["network_sent_bytes"] == 100
