# ashare-sync

[![GitHub License](https://img.shields.io/github/license/GOKORURI007/ashare-sync)](https://github.com/GOKORURI007/ashare-sync/blob/master/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)

[English](../README.md) | [简体中文](./README-zhCN.md)

一个用于同步 A 股（中国股市）数据的 Python CLI 工具。支持从多个数据源（新浪财经和东方财富）下载股票和指数列表，以及历史日行情数据。

## 功能特性

- 📊 **多数据源支持**：同时支持新浪财经和东方财富数据源
- 📈 **全面覆盖**：下载所有 A 股股票和主要指数
- 🔄 **增量更新**：智能增量同步，最小化数据传输
- 🛡️ **数据验证**：内置健康检查，自动检测和修复错误
- 📱 **CLI 界面**：用户友好的命令行界面，提供丰富的选项
- 📁 **平台适配**：自动管理平台特定的目录结构
- 📊 **进度追踪**：批量操作时显示实时进度条
- 🔧 **容错处理**：单个失败不影响整体同步流程

## 安装

### 前置要求

- Python 3.11 或更高版本
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/GOKORURI007/ashare-sync.git
cd ashare-sync

# 使用 uv 安装（推荐）
uv sync

# 或使用 pip
pip install -e .
```

## 快速开始

### 同步所有数据

```bash
# 同步股票和指数列表
uv run ashare-sync sync-list

# 同步所有股票和指数的历史价格数据
uv run ashare-sync sync-hist

# 检查数据完整性
uv run ashare-sync health-check
```

### 高级用法

```bash
# 使用东方财富作为数据源
uv run ashare-sync --data-source em sync-hist

# 仅同步股票列表（跳过指数）
uv run ashare-sync sync-list --skip-index

# 检查并自动修复数据问题
uv run ashare-sync health-check --fix

# 显示当前配置
uv run ashare-sync --show-config

# 使用自定义配置文件
uv run ashare-sync --config /path/to/config.json sync-list
```

## 配置

本工具采用分层配置系统：

1. **默认值**：硬编码在应用程序中
2. **配置文件**：平台特定配置路径下的 JSON 文件
3. **CLI 参数**：命令行参数可覆盖上述配置

### 配置选项

| 选项                 | 说明      | 默认值         | 可选值                                                      |
|--------------------|---------|-------------|----------------------------------------------------------|
| `data_dir`         | 数据存储目录  | 平台特定的用户数据目录 | 任意有效路径                                                   |
| `data_source`      | 数据源选择   | `sina`      | `sina`, `em`                                             |
| `log_level_file`   | 文件日志级别  | `WARNING`   | `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `log_level_stdout` | 控制台日志级别 | `INFO`      | 同上                                                       |

### 数据源说明

- **sina**（新浪财经）：原始价格数据，附带计算指标
- **em**（东方财富）：预计算指标，使用不同的数据结构

## 数据结构

同步完成后，数据目录将包含以下内容：

```
data_dir/
├── a_code_name.csv          # 所有 A 股股票
├── a_index_code_name.csv    # 所有指数
├── sz_code_name.csv         # 深圳股票
├── sh_code_name.csv         # 上海股票
├── bj_code_name.csv         # 北京股票
├── trade_date.csv           # 交易日历
├── stocks/                  # 个股数据
│   └── {symbol}.csv
└── index/                   # 指数数据
    └── {symbol}.csv
```

### 股票数据字段

所有股票数据文件包含以下字段：

- `date`: 交易日期（YYYY-MM-DD）
- `symbol`: 股票代码，带交易所前缀（如 'sh600000', 'sz000001'）
- `open`, `close`, `high`, `low`: 价格数据
- `volume`: 成交量（股数）
- `turnover`: 成交额（货币单位）
- `amplitude`: 振幅百分比
- `cp`: 涨跌幅百分比
- `ca`: 涨跌额
- `tr`: 换手率百分比
- `outstanding_share`: 流通股本

### 指数数据字段

指数数据文件包含以下字段：

- `date`: 交易日期
- `symbol`: 指数代码
- `open`, `close`, `high`, `low`: 价格数据

## 健康检查功能

内置的健康检查系统提供以下功能：

### 数据验证

- ✅ 交易日与官方日历对齐检查
- ✅ 必需字段完整性检查
- ✅ 数据完整性检查（无负价格/成交量、无穷大值）
- ✅ 缺失字段检测和推导

### 自动修复（使用 `--fix` 参数）

- 🔧 使用前一日数据填充缺失的交易日
- 🔧 使用前收盘价或日均价填充缺失的开盘价
- 🔧 使用次日开盘价或日均价填充缺失的收盘价
- 🔧 从可用数据推导缺失的计算字段
- 🔧 自动更新交易日历

## 开发指南

### 项目结构

```
.
├── src/ashare_sync/
│   ├── app.py              # 主 CLI 应用程序
│   ├── config.py           # 配置管理
│   ├── utils.py            # 工具函数
│   └── commands/
│       ├── sync_list.py    # 股票/指数列表同步
│       ├── sync_hist.py    # 历史数据同步
│       └── health_check.py # 数据验证和修复
├── tests/                 # 测试套件
├── scripts/               # 实用脚本
├── docs/                  # 文档
└── pyproject.toml         # 项目配置
```

### 开发命令

```bash
# 格式化代码
uv run scripts/format.py

# 运行测试并生成覆盖率报告
uv run scripts/test_all.py

# 运行特定测试
uv run scripts/test_all.py tests/test_specific.py

# 发布管理
uv run scripts/release.py

# 手动格式化代码
ruff format .

# 手动 lint 检查并自动修复
ruff check --fix .
```

## 核心依赖

- **akshare**: 中国市场金融数据 API
- **typer**: CLI 框架
- **pandas**: 数据处理
- **loguru**: 日志记录
- **tqdm**: 进度条
- **platformdirs**: 平台特定目录管理

## 数据处理模式

1. **增量更新**：仅获取上次同步后的新数据
2. **错误处理**：单个股票失败不会中断整个流程
3. **进度追踪**：批量操作时显示实时进度条
4. **数据验证**：优雅处理缺失/空文件
5. **跨源兼容**：不同数据源使用统一的数据结构

## 贡献指南

欢迎贡献！请随时提交 Pull Request。

## 许可证

本项目采用 AGPL-3.0-or-later 许可证 - 详见 [LICENSE](../LICENSE) 文件。

## 致谢

- [akshare](https://github.com/akfamily/akshare) 提供金融数据 API
- 所有帮助塑造本项目的贡献者
