import sys
from pathlib import Path

import numpy as np
from loguru import logger
from pandas import DataFrame

from . import config


def init_logger(cfg: config.Config):
    """
    Initialize logger.

    This function removes default handlers and adds two new handlers:
    1. Stdout handler: Displays logs in real-time with colors and concise format.
    2. File handler: Records logs to specified file with size-based rotation and compression.

    Args:
        cfg: config dict
    """
    logger.remove()
    log_path = Path(cfg.log_dir) / cfg.log_file
    logger.add(
        sys.stdout,
        level=cfg.log_level_stdout,
        format='<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        colorize=True,
        diagnose=False,
    )

    logger.add(
        log_path,
        level=cfg.log_level_file,
        rotation='10 MB',
        compression='zip',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        diagnose=False,
    )

    logger.bind(name=cfg.logger_name)


def derive_missing_fields(df: DataFrame) -> DataFrame:
    """尝试推导缺失的字段

    根据已有的价格、成交量等数据计算衍生指标：
    - ca (涨跌额): 当日收盘价 - 前一日收盘价
    - cp (涨跌幅): (涨跌额 / 前一日收盘价) * 100%
    - amplitude (振幅): (最高价 - 最低价) / 前一日收盘价 * 100%
    - tr (换手率): (成交量 / 流通股本) * 100%
    - outstanding_share (流通股本): 如果缺失但已知成交量和换手率，可反推

    Args:
        df: 原始股票数据 DataFrame

    Returns:
        补充了缺失字段的 DataFrame
    """
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

    # Calculate outstanding_share if missing but we have volume and tr
    if 'outstanding_share' not in result_df.columns or result_df['outstanding_share'].isna().any():
        if 'volume' in result_df.columns and 'tr' in result_df.columns:
            # outstanding_share = volume * 100 / tr (since tr = volume/outstanding_share * 100)
            result_df['outstanding_share'] = (result_df['volume'] * 100) / result_df['tr']
            result_df['outstanding_share'] = result_df['outstanding_share'].replace(
                [np.inf, -np.inf], np.nan
            )
            result_df['outstanding_share'] = result_df['outstanding_share'].ffill().bfill()

    return result_df
