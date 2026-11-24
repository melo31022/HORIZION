from horizon.collectors.performance import collect_memory_info, format_bytes
from horizon.collectors.system import collect_system_info


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
