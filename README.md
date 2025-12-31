## LogAnalyzer 🔍

A fast, configurable **Python CLI** for extracting and reporting events from structured log files - with support for **filters**, **regex**, **time ranges**, and **.gz** logs.

---

## 📖 Overview

**LogAnalyzer** scans log files and reports event data based on a simple, user-defined filter configuration file.  
It supports filtering by:

* **Event type**
* **Log level**
* **Regex pattern**
* **Optional time range**

Works with both:
* `.log`
* `.log.gz`

---

## ✨ Features

* **Advanced Filtering:** Filter events by type, level, regex, and time window.
* **Compression Support:** Works with both plain and compressed logs (`.log`, `.log.gz`).
* **Flexible Output Modes:**
    * **Count matches** (`--count`)
    * **Print matching lines** (Default)
* **High Performance:** Clean, modular implementation with **unit tests**.
* **Robust CLI:** Built-in input validation and clear error messaging.

---

## 🛠️ Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
# Linux/Mac:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
## 🚀 Usage (Command-line)

### Arguments

| Argument | Description |
|---|---|
| `--log-dir <path>` | **Required.** Path to directory containing logs. |
| `--events-file <path>` | **Required.** Path to filter configuration file. |
| `--from <timestamp>` | Optional. Start time (Format: `YYYY-MM-DDTHH:MM:SS`). |
| `--to <timestamp>` | Optional. End time (Format: `YYYY-MM-DDTHH:MM:SS`). |

### Running the Script

```bash
python LogAnalyzer.py \
  --log-dir logs \
  --events-file events_sample.txt \
  --from 2025-06-01T10:00:00 \
  --to 2025-06-01T15:00:00
```
## ⚙️ Filter Configuration (events.txt)

Each line in the configuration file describes one filter rule.

# Examples
```txt
TELEMETRY --count --pattern ^Iteration time:\s\d+\.\d+\ssec$
DEVICE --count --level WARNING
GNMI --level ERROR
```
## Supported Flags

--count: Output only the number of matches.

--level <LEVEL>: Match lines with a specific level (e.g., INFO, WARNING, ERROR).

--pattern <REGEX>: Regex match on the log message.

## 📋 Log Format Assumption

The tool expects the following structured log format:
```txt
<TIMESTAMP> <LEVEL> <EVENT> <MESSAGE...>
```
Example
```txt
2025-06-01T14:03:05 INFO TELEMETRY Iteration time: 1793.845 sec
```
## 🏗️ Project Structure
```txt
.
├── LogAnalyzer.py          # Main CLI entry point
├── helper.py               # Parsing + filtering helpers
├── test_log_analyzer.py    # Unit tests
├── events_sample.txt       # Example filter file
├── logs/                   # Example log directory
└── requirements.txt        # Project dependencies
```

Developed by Amit Tzur 
