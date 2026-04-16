# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

**ashare-sync** is a Python CLI tool for synchronizing A-share (Chinese stock market) data. It
supports downloading stock and index lists, as well as historical daily price data from multiple
data sources (Sina Finance and East Money).

## Architecture

The project follows a modular CLI architecture using Typer:

- **Core CLI App** (`src/ashare_sync/app.py`): Main Typer application with configuration management
- **Commands** (`src/ashare_sync/commands/`): Modular command implementations
    - `sync_list.py`: Synchronizes stock and index listing data
    - `sync_hist.py`: Synchronizes historical daily price data
  - `health_check.py`: Validates data integrity and optionally fixes issues
- **Configuration** (`src/ashare_sync/config.py`): Dataclass-based configuration with
  platform-appropriate paths
- **Utilities** (`src/ashare_sync/utils.py`): Logger initialization

## Key Dependencies

- **akshare**: Financial data API for Chinese markets
- **typer**: CLI framework
- **pandas**: Data manipulation
- **loguru**: Logging
- **tqdm**: Progress bars
- **platformdirs**: Platform-appropriate directory management

## Common Development Commands

### Environment Setup

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Running the Application
```bash
# Show help
uv run ashare-sync --help

# Sync stock and index lists
uv run ashare-sync sync-list

# Sync stock lists only
uv run ashare-sync sync-list --skip-index

# Sync index lists only
uv run ashare-sync sync-list --skip-stock

# Sync historical data
uv run ashare-sync sync-hist

# Check data integrity
uv run ashare-sync health-check

# Check and fix data issues
uv run ashare-sync health-check --fix

# Show current configuration
uv run ashare-sync --show-config

# Run with custom config file
uv run ashare-sync --config /path/to/config.json sync-list

# Use East Money as data source
uv run ashare-sync --data-source em sync-hist
```

### Development Tasks

```bash
# Format code
uv run scripts/format.py

# Run tests with coverage
uv run scripts/test_all.py

# Run specific test
uv run scripts/test_all.py tests/test_specific.py

# Release management
uv run scripts/release.py
```

### Code Quality

```bash
# Manual ruff formatting
ruff format .

# Manual ruff linting with fixes
ruff check --fix .
```

## Configuration System

The app uses a hierarchical configuration system:

1. **Defaults**: Hardcoded in `Config` dataclass
2. **Config File**: JSON file at platform-specific config path
3. **CLI Arguments**: Command-line overrides

Configuration includes:

- `data_dir`: Where to store downloaded CSV files
- `data_source`: 'sina' or 'em' (East Money)
- Logger settings (levels, paths, etc.)

## Data Storage Structure

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

## Key Data Processing Patterns

1. **Incremental Updates**: Commands check existing data dates and only fetch new data
2. **Error Handling**: Individual stock failures don't stop the entire sync process
3. **Progress Tracking**: Uses tqdm for progress bars during bulk operations
4. **Data Validation**: Handles missing/empty files gracefully
5. **Cross-source Compatibility**: Supports both Sina Finance and East Money data sources with
   unified schemas

## Data Schema

### Stock Data Fields

All stock data files contain the following fields:

- `date`: Trading date (YYYY-MM-DD format)
- `symbol`: Stock symbol with exchange prefix (e.g., 'sh600000', 'sz000001')
- `open`: Opening price
- `close`: Closing price
- `high`: Highest price
- `low`: Lowest price
- `volume`: Trading volume (shares)
- `turnover`: Trading amount (currency)
- `amplitude`: Price amplitude percentage
- `cp`: Price change percentage
- `ca`: Price change amount
- `tr`: Turnover rate percentage
- `outstanding_share`: Outstanding shares (calculated from volume and turnover rate)

### Index Data Fields

Index data files contain a simplified schema:

- `date`: Trading date
- `symbol`: Index symbol
- `open`: Opening price
- `close`: Closing price
- `high`: Highest price
- `low`: Lowest price

## Health Check Capabilities

The health check system validates and optionally fixes:

1. **Trading Date Alignment**: Ensures stock data dates align with the official trading calendar
2. **Missing Fields**: Detects and attempts to derive missing calculated fields (amplitude, cp, ca,
   tr, outstanding_share)
3. **Data Integrity**: Checks for negative prices/volumes and infinite values
4. **Automatic Fixes**: When `--fix` flag is used:
    - Fills missing trading dates using previous day's data
    - Fills missing open prices using previous close or daily average
    - Fills missing close prices using next day's open or daily average
    - Derives missing calculated fields from available data

## Data Source Handling

### Sina Finance (`sina`)

- Uses `ak.stock_zh_a_daily()` for stock data
- Provides raw price and volume data
- Requires calculation of derived metrics (amplitude, change %, turnover rate)
- Includes outstanding share information

### East Money (`em`)

- Uses `ak.stock_zh_a_hist()` for stock data
- Provides pre-calculated derived metrics
- Outstanding shares calculated from volume and turnover rate
- Different column naming requiring mapping

## Testing Strategy

- Tests are located in `tests/` directory
- Uses pytest with coverage reporting
- Includes pytest-dependency for test ordering
- Generates HTML coverage reports in `htmlcov/`

## Release Process

The project uses automated version management through `scripts/release.py` which handles semantic
versioning and changelog generation.

## Important Implementation Notes

- The app uses platform-appropriate directories via `platformdirs`
- Data sources have different schemas requiring column mapping
- Derived metrics (change %, amplitude, turnover) are calculated consistently across sources
- The tool handles both full historical sync and incremental updates
- Health check validates data integrity and can automatically fix common issues like missing trading
  dates and null values
- Trading date calendar is automatically updated during health checks to ensure accurate date
  alignment
- All data operations are fault-tolerant - individual failures don't stop the entire process
- Progress tracking with tqdm provides real-time feedback during bulk operations
