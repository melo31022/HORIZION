# HORIZON

HORIZON is a Windows desktop application for local hardware identification and system monitoring.

## Version 0.1

This first foundation release includes:
- A PySide6 desktop interface with Basic and Advanced modes.
- Live CPU usage and memory usage collection through psutil.
- Operating system, machine, processor, and boot-time information.
- Graceful handling of unavailable values.
- Initial automated tests for the collectors.

No cloud services, external APIs, or AI are used. System information is collected locally.

## Requirements

- Windows 10/11 (64-bit)
- Python 3.11 or newer

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Tests

```powershell
pytest
```

## Project status

Version 0.1 is the foundation. GPU details, sensor readings, process management, graphs, benchmarks, reports, and history are planned for later versions and are not implemented yet.

## License

MIT. See [LICENSE](LICENSE).
