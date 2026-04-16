import os

import akshare as ak
import numpy as np
import pandas as pd
import typer
from loguru import logger
from pandas import DataFrame
from tqdm import tqdm

from .. import config

app = typer.Typer(help='检查数据集的数据完整性和正确性。')

# Required fields for stock data
STOCK_REQUIRED_FIELDS = {
    'date', 'symbol', 'open', 'close', 'high', 'low',
    'volume', 'turnover', 'amplitude', 'cp', 'ca', 'tr', 'outstanding_share'
}

# Required fields for index data (simpler)
INDEX_REQUIRED_FIELDS = {
    'date', 'symbol', 'open', 'close', 'high', 'low'
}


def update_trade_date(cfg: config.Config) -> DataFrame:
    """更新交易日日历"""
    df = ak.tool_trade_date_hist_sina()
    df.to_csv(cfg.data_dir / 'trade_date.csv', index=False)
    return df


def derive_missing_fields(df: DataFrame) -> DataFrame:
    """尝试推导缺失的字段"""
    result_df = df.copy()

    # Calculate derived fields if missing
    if 'ca' not in result_df.columns or result_df['ca'].isna().any():
        last_close = result_df['close'].shift(1)
        result_df['ca'] = result_df['close'] - last_close
        result_df['ca'] = result_df['ca'].fillna(0)

    if 'cp' not in result_df.columns or result_df['cp'].isna().any():
        last_close = result_df['close'].shift(1)
        result_df['cp'] = (result_df['ca'] / last_close) * 100
        result_df['cp'] = result_df['cp'].fillna(0)

    if 'amplitude' not in result_df.columns or result_df['amplitude'].isna().any():
        last_close = result_df['close'].shift(1)
        result_df['amplitude'] = (result_df['high'] - result_df['low']) / last_close * 100
        result_df['amplitude'] = result_df['amplitude'].fillna(0)

    # Calculate turnover rate if we have volume and outstanding_share
    if 'tr' not in result_df.columns or result_df['tr'].isna().any():
        if 'outstanding_share' in result_df.columns and 'volume' in result_df.columns:
            result_df['tr'] = (result_df['volume'] / result_df['outstanding_share']) * 100
            result_df['tr'] = result_df['tr'].fillna(0)

    # Calculate turnover (amount) if missing but we have other data
    if 'turnover' not in result_df.columns or result_df['turnover'].isna().any():
        # Can't reliably calculate turnover without additional info, leave as is
        pass

    # Calculate outstanding_share if missing but we have volume and tr
    if 'outstanding_share' not in result_df.columns or result_df['outstanding_share'].isna().any():
        if 'volume' in result_df.columns and 'tr' in result_df.columns:
            # outstanding_share = volume * 100 / tr (since tr = volume/outstanding_share * 100)
            result_df['outstanding_share'] = (result_df['volume'] * 100) / result_df['tr']
            result_df['outstanding_share'] = result_df['outstanding_share'].replace(
                [np.inf, -np.inf], np.nan)
            result_df['outstanding_share'] = result_df['outstanding_share'].fillna(
                method='ffill').fillna(method='bfill')

    return result_df


def check_trading_date_alignment(df: DataFrame, trade_dates: DataFrame, symbol: str) -> list[str]:
    """检查交易日对齐"""
    errors = []

    if df.empty or 'date' not in df.columns:
        errors.append(f"Missing date column")
        return errors

    # Convert dates to datetime for comparison
    df_dates = pd.to_datetime(df['date']).dt.date
    min_date = df_dates.min()
    max_date = df_dates.max()

    # Get expected trading dates in range
    trade_dates_dt = pd.to_datetime(trade_dates['trade_date']).dt.date
    expected_dates = trade_dates_dt[
        (trade_dates_dt >= min_date) & (trade_dates_dt <= max_date)
        ].tolist()

    actual_dates = df_dates.tolist()
    missing_dates = set(expected_dates) - set(actual_dates)

    if missing_dates:
        errors.append(
            f"Missing {len(missing_dates)} trading dates in range {min_date} to {max_date}")

    return errors


def check_missing_fields(df: DataFrame, symbol: str, required_fields: set) -> list[str]:
    """检查缺失字段"""
    errors = []

    # Check for completely missing columns
    missing_columns = required_fields - set(df.columns)
    if missing_columns:
        errors.append(f"Missing columns: {missing_columns}")

    # Check for columns with null values
    for col in required_fields:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append(f"Column '{col}' has {null_count} null values")

    return errors


def check_invalid_values(df: DataFrame, symbol: str) -> list[str]:
    """检查非法值"""
    errors = []

    # Check for negative prices
    price_cols = ['open', 'close', 'high', 'low']
    for col in price_cols:
        if col in df.columns:
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                errors.append(f"Column '{col}' has {negative_count} negative values")

    # Check for negative volume
    if 'volume' in df.columns:
        negative_volume = (df['volume'] < 0).sum()
        if negative_volume > 0:
            errors.append(f"Column 'volume' has {negative_volume} negative values")

    # Check for infinite values
    for col in df.columns:
        if df[col].dtype in ['float64', 'int64']:
            inf_count = np.isinf(df[col]).sum()
            if inf_count > 0:
                errors.append(f"Column '{col}' has {inf_count} infinite values")

    return errors


def fix_data_issues(df: DataFrame, trade_dates: DataFrame) -> DataFrame:
    """修复数据问题"""
    result_df = df.copy()

    # Ensure date column is datetime
    result_df['date'] = pd.to_datetime(result_df['date']).dt.date

    # Fill missing trading dates
    min_date = result_df['date'].min()
    max_date = result_df['date'].max()

    trade_dates_dt = pd.to_datetime(trade_dates['trade_date']).dt.date
    expected_dates = trade_dates_dt[
        (trade_dates_dt >= min_date) & (trade_dates_dt <= max_date)
        ].tolist()

    # Create complete date range
    complete_df = pd.DataFrame({'date': expected_dates})
    result_df = complete_df.merge(result_df, on='date', how='left')

    # Fill missing open with previous close
    if 'open' in result_df.columns and 'close' in result_df.columns:
        result_df['open'] = result_df['open'].fillna(method='ffill')
        # For first row, if open is still missing, use close
        result_df['open'] = result_df['open'].fillna(result_df['close'])

    # Fill missing close with next open
    if 'close' in result_df.columns and 'open' in result_df.columns:
        result_df['close'] = result_df['close'].fillna(method='bfill')
        # For last row, if close is still missing, use open
        result_df['close'] = result_df['close'].fillna(result_df['open'])

    # Forward fill symbol if missing
    if 'symbol' in result_df.columns:
        result_df['symbol'] = result_df['symbol'].fillna(method='ffill').fillna(method='bfill')

    return result_df


def health_check(cfg: config.Config, fix: bool = False):
    """ 检查数据集的数据完整性和正确性。
    1. 检查每支股票的交易日与交易日历的对齐，即股票最早日期到最终日期应当与交易日历中对应的时间段一致，不应当缺少某些日期
    2. 检查股票是否存在缺失字段，股票应当包含以下字段：
        - date: 交易日期
        - symbol: 股票代码
        - open: 开盘价
        - close: 收盘价
        - high: 最高价
        - low: 最低价
        - volume: 成交量
        - turnover: 成交额
        - amplitude: 振幅 (%)
        - cp: 涨跌幅 (%)
        - ca: 涨跌额
        - tr: 换手率 (%)
        - outstanding_share: 流通股本

        如果 turnover, amplitude, cp, ca, tr 缺失，尝试通过outstanding_share补全。
        如果尝试通过outstanding_share补全缺失，尝试通过volume和tr补全。
        无论fix是否为True，均尝试补全。如果无法补全，标记为缺失。

    3. 检查数据中是否存在空值/非法值。

    当fix==False时，仅输出[symbol]->[error]报告。
    当fix==True时：
    1. 对缺失的交易日，用前一个交易日的信息作为填补
    2. 对缺失的open字段，用前一个交易日的close填补
       对缺失的close字段，用下一个交易日的open填补
       缺失的high/low/volume字段不处理
    """
    logger.info("Starting health check...")

    # Update trading date calendar
    trade_dates = update_trade_date(cfg)
    logger.info(f"Updated trading date calendar with {len(trade_dates)} dates")

    # Get all stock files
    stocks_dir = cfg.data_dir / 'stocks'
    index_dir = cfg.data_dir / 'index'

    all_files = []
    if stocks_dir.exists():
        all_files.extend(list(stocks_dir.glob('*.csv')))
    if index_dir.exists():
        all_files.extend(list(index_dir.glob('*.csv')))

    if not all_files:
        logger.warning("No data files found to check")
        return

    logger.info(f"Checking {len(all_files)} data files...")

    total_errors = 0
    fixed_files = 0

    for file_path in tqdm(all_files, desc="Health checking"):
        symbol = file_path.stem
        errors = []

        # Determine if this is an index or stock file
        is_index_file = 'index' in str(file_path.parent)
        required_fields = INDEX_REQUIRED_FIELDS if is_index_file else STOCK_REQUIRED_FIELDS

        try:
            # Read data
            if os.path.getsize(file_path) == 0:
                errors.append("Empty file")
                continue

            df = pd.read_csv(file_path)
            if df.empty:
                errors.append("Empty dataframe")
                continue

            # Always try to derive missing fields (only for stocks)
            if not is_index_file:
                df = derive_missing_fields(df)

            # Run all checks
            date_errors = check_trading_date_alignment(df, trade_dates, symbol)
            field_errors = check_missing_fields(df, symbol, required_fields)
            invalid_errors = check_invalid_values(df, symbol)

            errors.extend(date_errors)
            errors.extend(field_errors)
            errors.extend(invalid_errors)

            if errors:
                total_errors += len(errors)
                logger.warning(f"[{symbol}] -> {errors}")

                if fix:
                    # Apply fixes
                    df_fixed = fix_data_issues(df, trade_dates)
                    df_fixed = derive_missing_fields(df_fixed)

                    # Save fixed data
                    df_fixed.to_csv(file_path, index=False)
                    fixed_files += 1
                    logger.info(f"Fixed {symbol} - saved {len(df_fixed)} records")
            else:
                logger.debug(f"[{symbol}] -> OK")

        except Exception as e:
            error_msg = f"Error processing {symbol}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            total_errors += 1

    # Summary
    logger.info(f"Health check completed. Total errors: {total_errors}")
    if fix:
        logger.info(f"Fixed {fixed_files} files")

    if total_errors == 0:
        logger.success("All data files are healthy!")
    elif fix:
        logger.success(f"Applied fixes to {fixed_files} files")


@app.command()
def cmd(
    ctx: typer.Context,
    fix: bool = typer.Option(False, '--fix', help='自动修复错误')
):
    """检查数据集的数据完整性和正确性"""
    cfg: config.Config = ctx.obj
    health_check(cfg, fix)
