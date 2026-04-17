import os

import akshare as ak
import numpy as np
import pandas as pd
import typer
from loguru import logger
from pandas import DataFrame
from tqdm import tqdm

from .. import config
from ..utils import derive_missing_fields

app = typer.Typer(help='检查数据集的数据完整性和正确性。')

# Required fields for stock data
STOCK_REQUIRED_FIELDS = {
    'date',  # date
    'symbol',  # str
    'open',  # float
    'close',  # float
    'high',  # float
    'low',  # float
    'volume',  # int
    'turnover',  # float
    'amplitude',  # float
    'cp',  # float
    'ca',  # float
    'tr',  # float
    'outstanding_share',  # int
}

# Required fields for index data (simpler)
INDEX_REQUIRED_FIELDS = {'date', 'symbol', 'open', 'close', 'high', 'low'}


def update_trade_date(cfg: config.Config) -> DataFrame:
    """更新交易日日历

    从新浪财经获取历史交易日数据并保存到 Parquet 文件。

    Args:
        cfg: 配置对象，包含数据目录路径

    Returns:
        包含交易日数据的 DataFrame
    """
    df = ak.tool_trade_date_hist_sina()
    df = df.rename(columns={'trade_date': 'date'})
    df['date'] = pd.to_datetime(df['date']).dt.date
    df.to_parquet(cfg.data_dir / 'trade_date.parquet', index=False)
    return df


def check_trading_date_alignment(df: DataFrame, trade_dates: DataFrame) -> list[str]:
    """检查交易日对齐情况

    验证股票数据的日期范围是否与交易日历一致，检测是否有缺失的交易日。

    Args:
        df: 股票数据 DataFrame
        trade_dates: 交易日历 DataFrame

    Returns:
        错误信息列表，如果日期对齐则返回空列表
    """
    errors = []

    if df.empty or 'date' not in df.columns:
        errors.append('Missing date column')
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
            f'Missing {len(missing_dates)} trading dates in range {min_date} to {max_date}'
        )

    return errors


def check_missing_fields(df: DataFrame, required_fields: set) -> list[str]:
    """检查缺失字段

    验证数据是否包含所有必需字段，以及这些字段是否存在空值。

    Args:
        df: 待检查的 DataFrame
        required_fields: 必需字段集合

    Returns:
        错误信息列表，如果没有缺失则返回空列表
    """
    errors = []

    # Check for completely missing columns
    missing_columns = required_fields - set(df.columns)
    if missing_columns:
        errors.append(f'Missing columns: {missing_columns}')

    # Check for columns with null values
    for col in required_fields:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append(f"Column '{col}' has {null_count} null values")

    return errors


def check_invalid_values(df: DataFrame) -> list[str]:
    """检查非法值

    检测数据中的异常值：
    - 负的价格或成交量
    - 无穷大值 (inf/-inf)

    Args:
        df: 待检查的 DataFrame

    Returns:
        错误信息列表，如果没有非法值则返回空列表
    """
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
    """修复数据问题

    执行以下修复操作：
    1. 补全缺失的交易日（使用前一日数据填充）
    2. 修复缺失的开盘价：优先使用前一交易日收盘价，其次使用当日高低均价
    3. 修复缺失的收盘价：优先使用下一交易日开盘价，其次使用当日高低均价

    Args:
        df: 原始股票数据 DataFrame
        trade_dates: 交易日历 DataFrame

    Returns:
        修复后的 DataFrame
    """
    result_df = df.copy()

    # Ensure date column is datetime
    result_df['date'] = pd.to_datetime(result_df['date']).dt.date

    # Fill missing trading dates
    min_date = result_df['date'].min()
    max_date = result_df['date'].max()

    trade_dates_dt = pd.to_datetime(trade_dates['date']).dt.date
    expected_dates = trade_dates_dt[
        (trade_dates_dt >= min_date) & (trade_dates_dt <= max_date)
    ].tolist()

    # Create complete date range
    complete_df = pd.DataFrame({'date': expected_dates})
    result_df = complete_df.merge(result_df, on='date', how='left')

    # Fill missing open with previous close
    if all(col in result_df.columns for col in ['open', 'close', 'low', 'high']):
        # 1. 如果 open 缺失，先用前一行的 close 填充
        # shift(1) 将 close 列向下移动一位，使其对齐下一行的 open
        result_df['open'] = result_df['open'].fillna(result_df['close'].shift(1))

        # 2. 处理首行依然缺失的情况（因为 shift(1) 会导致第一行产生 NaN）
        # 使用 low 和 high 的均值填充
        avg_price = (result_df['low'] + result_df['high']) / 2
        result_df['open'] = result_df['open'].fillna(avg_price)

    # Fill missing close with next open
    if all(col in result_df.columns for col in ['open', 'close', 'low', 'high']):
        # 1. 缺失的今日收盘 = 明日开盘
        # shift(-1) 会将数据整体上移，把“明日开盘”挪到“今日”的位置
        result_df['close'] = result_df['close'].fillna(result_df['open'].shift(-1))

        # 2. 如果是最后一行依然缺失（因为 shift(-1) 会让最后一行产生 NaN）
        # 按照你的要求，取当日 low 和 high 的均值
        avg_price = (result_df['low'] + result_df['high']) / 2
        result_df['close'] = result_df['close'].fillna(avg_price)

    return result_df


def health_check(cfg: config.Config, fix: bool = False):
    """检查数据集的数据完整性和正确性。
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

        如果 turnover, amplitude, cp, ca, tr 缺失，尝试通过 outstanding_share 补全。
        如果尝试通过 outstanding_share 补全缺失，尝试通过 volume 和 tr 补全。
        无论 fix 是否为 True，均尝试补全。如果无法补全，标记为缺失。

    3. 检查数据中是否存在空值 / 非法值。

    当 fix==False 时，仅输出 [symbol]->[error] 报告。
    当 fix==True 时：
    1. 对缺失的交易日，用前一个交易日的信息作为填补
    2. 对缺失的 open 字段，用前一个交易日的 close 填补
       对缺失的 close 字段，用下一个交易日的 open 填补
       缺失的 high/low/volume 字段不处理
    """
    logger.info('开始健康检查...')

    # 更新交易日历
    trade_dates = update_trade_date(cfg)
    logger.info(f'已更新交易日历，共 {len(trade_dates)} 个交易日')

    # 获取所有股票文件
    stocks_dir = cfg.data_dir / 'stocks'
    index_dir = cfg.data_dir / 'index'

    all_files = []
    if stocks_dir.exists():
        all_files.extend(list(stocks_dir.glob('*.parquet')))
    if index_dir.exists():
        all_files.extend(list(index_dir.glob('*.parquet')))

    if not all_files:
        logger.warning('未找到需要检查的数据文件')
        return

    logger.info(f'正在检查 {len(all_files)} 个数据文件...')

    total_errors = 0
    fixed_files = 0

    for file_path in tqdm(all_files, desc='Health checking'):
        symbol = file_path.stem
        errors = []

        # 判断是指数文件还是股票文件
        is_index_file = 'index' in str(file_path.parent)
        required_fields = INDEX_REQUIRED_FIELDS if is_index_file else STOCK_REQUIRED_FIELDS

        try:
            # 读取数据
            if os.path.getsize(file_path) == 0:
                errors.append('文件为空')
                continue

            df = pd.read_parquet(file_path)
            if df.empty:
                errors.append('数据框为空')
                continue

            # 确保 symbol 列存在且无缺失值
            if 'symbol' not in df.columns:
                df['symbol'] = symbol
                logger.debug(f'[{symbol}] 已添加缺失的 symbol 列')
            else:
                # 用文件名中的股票代码填充缺失的 symbol 值
                missing_symbol_count = df['symbol'].isna().sum()
                if missing_symbol_count > 0:
                    df['symbol'] = df['symbol'].fillna(symbol)
                    logger.debug(f'[{symbol}] 已填充 {missing_symbol_count} 个缺失的 symbol 值')

            # 始终尝试推导缺失字段（仅针对股票数据）
            if not is_index_file:
                df = derive_missing_fields(df)

            # 执行所有检查
            date_errors = check_trading_date_alignment(df, trade_dates)
            field_errors = check_missing_fields(df, required_fields)
            invalid_errors = check_invalid_values(df)

            errors.extend(date_errors)
            errors.extend(field_errors)
            errors.extend(invalid_errors)

            if not errors or not fix:
                df.to_parquet(file_path, index=False)

            if errors:
                total_errors += len(errors)
                logger.warning(f'[{symbol}] -> {errors}')

                if fix:
                    # 应用修复
                    df_fixed = fix_data_issues(df, trade_dates)

                    # 保存修复后的数据
                    df_fixed.to_parquet(file_path, index=False)
                    fixed_files += 1
                    logger.info(f'已修复 {symbol} - 保存 {len(df_fixed)} 条记录')
            else:
                logger.debug(f'[{symbol}] -> 正常')

        except Exception as e:
            error_msg = f'处理 {symbol} 时出错: {e}'
            errors.append(error_msg)
            logger.error(error_msg)
            total_errors += 1

    # 汇总报告
    logger.info(f'健康检查完成。总错误数: {total_errors}')
    if fix:
        logger.info(f'已修复 {fixed_files} 个文件')

    if total_errors == 0:
        logger.success('所有数据文件均正常！')
    elif fix:
        logger.success(f'已对 {fixed_files} 个文件应用修复')


@app.command()
def cmd(ctx: typer.Context, fix: bool = typer.Option(False, '--fix', help='自动修复错误')):
    """检查数据集的数据完整性和正确性"""
    cfg: config.Config = ctx.obj
    health_check(cfg, fix)
