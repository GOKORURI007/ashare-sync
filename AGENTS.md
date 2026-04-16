# AGENTS.md

## Project Overview

ashare-sync is a Python library for synchronizing A-share (Chinese stock market) data. It fetches
stock and index information from akshare and stores it locally as CSV files.

## Architecture

```
src/ashare_sync/
├── __init__.py    # Version management
├── __main__.py    # CLI entry point
├── app.py         # Typer CLI application
├── config.py      # Configuration dataclass
├── update.py      # Data synchronization logic
└── utils.py       # Logger initialization
```

## Key Components

### app.py

- CLI application using Typer
- Configuration priority: CLI arguments > config file > defaults
- Config file location: `user_config_path('ashare_sync')/config.json`

### config.py

- `Config` dataclass with fields: `data_dir`, `logger_name`, `log_dir`, `log_file`,
  `log_level_file`, `log_level_stdout`
- `LogLevel` type: `Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']`

### update.py

Main data sync functions:

- `update_stock_info_a_code_name()`: Fetches all A-share stock codes/names (SH/SZ/BJ exchanges)
- `update_index_info_a_code_name()`: Fetches all A-share index codes/names
- `update_a_hist_daily()`: Incremental update of historical daily data for stocks and indices

Data sources: akshare library

### utils.py

- `init_logger()`: Configures loguru with stdout (colored) and file handlers (with rotation)

## Data Storage

- Stock list: `{data_dir}/a_code_name.csv`
- Index list: `{data_dir}/a_index_code_name.csv`
- Stock history: `{data_dir}/stocks/{code}.csv`
- Index history: `{data_dir}/index/{symbol}.csv`

## Dependencies

- typer: CLI framework
- loguru: Logging
- akshare: A-share data source
- pandas: Data processing
- platformdirs: Cross-platform paths

## Commands

Run the CLI:

```bash
python -m ashare_sync
```

Options:

- `--config`: Path to config file
- `--data-dir`: Data directory
- `--log-dir`: Log directory
- `--log-file`: Log file name
- `--log-level-file`: File log level
- `--log-level-stdout`: Console log level
- `-v, --version`: Show version
