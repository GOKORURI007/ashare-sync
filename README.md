# ashare-sync

[![License](https://img.shields.io/github/license/GOKORURI007/ashare-sync)](https://github.com/GOKORURI007/ashare-sync/blob/master/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

[English](./README.md) | [简体中文](./docs/README-zhCN.md)

A Python CLI tool for synchronizing A-share (Chinese stock market) data. It supports downloading
stock and index lists, as well as historical daily price data from multiple data sources (Sina
Finance and East Money).

## Features

- 📊 **Multi-source Data**: Supports both Sina Finance and East Money data sources
- 📈 **Complete Coverage**: Downloads all A-share stocks and major indices
- 🔄 **Incremental Updates**: Smart incremental synchronization to minimize data transfer
- 🛡️ **Data Validation**: Built-in health check with automatic error detection and fixing
- 📱 **CLI Interface**: User-friendly command-line interface with comprehensive options
- 📁 **Platform-aware**: Automatic platform-appropriate directory management
- 📊 **Progress Tracking**: Real-time progress bars for bulk operations
- 🔧 **Fault Tolerant**: Individual failures don't stop the entire synchronization process

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install from Source

```bash
# Clone the repository
git clone https://github.com/GOKORURI007/ashare-sync.git
cd ashare-sync

# Install using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Quick Start

### Synchronize All Data

```bash
# Sync stock and index lists
uv run ashare-sync sync-list

# Sync historical price data for all stocks and indices
uv run ashare-sync sync-hist

# Check data integrity
uv run ashare-sync health-check
```

### Advanced Usage

```bash
# Use East Money as data source
uv run ashare-sync --data-source em sync-hist

# Sync only stock lists (skip indices)
uv run ashare-sync sync-list --skip-index

# Check and automatically fix data issues
uv run ashare-sync health-check --fix

# Show current configuration
uv run ashare-sync --show-config

# Use custom configuration file
uv run ashare-sync --config /path/to/config.json sync-list
```

## Configuration

The tool uses a hierarchical configuration system:

1. **Defaults**: Hardcoded in the application
2. **Config File**: JSON file at platform-specific config path
3. **CLI Arguments**: Command-line overrides

### Configuration Options

| Option             | Description            | Default                         | Options                                                  |
|--------------------|------------------------|---------------------------------|----------------------------------------------------------|
| `data_dir`         | Data storage directory | Platform-specific user data dir | Any valid path                                           |
| `data_source`      | Data source selection  | `sina`                          | `sina`, `em`                                             |
| `log_level_file`   | File log level         | `WARNING`                       | `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `log_level_stdout` | Console log level      | `INFO`                          | Same as above                                            |

### Data Sources

- **sina** (Sina Finance): Raw price data with calculated metrics
- **em** (East Money): Pre-calculated metrics with different schema

## Data Structure

After synchronization, your data directory will contain:

```
data_dir/
├── a_code_name.csv          # All A-share stocks
├── a_index_code_name.csv    # All indices
├── sz_code_name.csv         # Shenzhen stocks
├── sh_code_name.csv         # Shanghai stocks
├── bj_code_name.csv         # Beijing stocks
├── trade_date.csv           # Trading calendar
├── stocks/                  # Individual stock data
│   └── {symbol}.csv
└── index/                   # Individual index data
    └── {symbol}.csv
```

### Stock Data Schema

All stock data files contain:

- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Stock symbol with exchange prefix (e.g., 'sh600000', 'sz000001')
- `open`, `close`, `high`, `low`: Price data
- `volume`: Trading volume (shares)
- `turnover`: Trading amount (currency)
- `amplitude`: Price amplitude percentage
- `cp`: Price change percentage
- `ca`: Price change amount
- `tr`: Turnover rate percentage
- `outstanding_share`: Outstanding shares

### Index Data Schema

Index data files contain:

- `date`: Trading date
- `symbol`: Index symbol
- `open`, `close`, `high`, `low`: Price data

## Health Check Features

The built-in health check system provides:

### Validation

- ✅ Trading date alignment with official calendar
- ✅ Required field completeness
- ✅ Data integrity (no negative prices/volumes, infinite values)
- ✅ Missing field detection and derivation

### Automatic Fixes (with `--fix` flag)

- 🔧 Fill missing trading dates using previous day's data
- 🔧 Fill missing open prices using previous close or daily average
- 🔧 Fill missing close prices using next day's open or daily average
- 🔧 Derive missing calculated fields from available data
- 🔧 Update trading calendar automatically

## Development

### Project Structure

```
.
├── src/ashare_sync/
│   ├── app.py              # Main CLI application
│   ├── config.py           # Configuration management
│   ├── utils.py            # Utility functions
│   └── commands/
│       ├── sync_list.py    # Stock/index list synchronization
│       ├── sync_hist.py    # Historical data synchronization
│       └── health_check.py # Data validation and fixing
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

### Development Commands

```bash
# Format code
uv run scripts/format.py

# Run tests with coverage
uv run scripts/test_all.py

# Run specific test
uv run scripts/test_all.py tests/test_specific.py

# Release management
uv run scripts/release.py

# Manual code formatting
ruff format .

# Manual linting with fixes
ruff check --fix .
```

## Key Dependencies

- **akshare**: Financial data API for Chinese markets
- **typer**: CLI framework
- **pandas**: Data manipulation
- **loguru**: Logging
- **tqdm**: Progress bars
- **platformdirs**: Platform-appropriate directory management

## Data Processing Patterns

1. **Incremental Updates**: Only fetches new data since last synchronization
2. **Error Handling**: Individual stock failures don't stop the entire process
3. **Progress Tracking**: Real-time progress bars during bulk operations
4. **Data Validation**: Graceful handling of missing/empty files
5. **Cross-source Compatibility**: Unified schemas across different data sources

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the AGPL-3.0-or-later License - see the [LICENSE](LICENSE) file for
details.

## Acknowledgments

- [akshare](https://github.com/akfamily/akshare) for providing the financial data API
- All contributors who have helped shape this project
