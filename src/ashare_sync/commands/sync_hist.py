#!/usr/bin/env python
import datetime
import os

import akshare as ak
import numpy as np
import pandas as pd
import typer
from loguru import logger
from pandas.core.interchange.dataframe_protocol import DataFrame
from tqdm import tqdm

from .. import config

EAST_MONEY_DATA_DICT = {
    '日期': 'date',
    '股票代码': 'symbol',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'turnover',
    '振幅': 'amplitude',
    '涨跌幅': 'cp',
    '涨跌额': 'ca',
    '换手率': 'tr',
    # '流动股本': 成交量 / 换手率 *100(股) outstanding_share
}

SINA_DATA_DICT = {
    'date': 'date',
    'open': 'open',
    'close': 'close',
    'high': 'high',
    'low': 'low',
    'volume': 'volume',
    'turnover': 'turnover',
    'outstanding_share': 'outstanding_share',
    # '股票代码': symbol
    # '振幅':  $\frac{High_{today} - Low_{today}}{Close_{yesterday}} \times 100$ amplitude
    # '涨跌幅': $\frac{Close_{today} - Close_{yesterday}}{Close_{yesterday}} \times 100$ cp
    # '涨跌额': $Close_{today} - Close_{yesterday}$ ca
    # '换手率': $\frac{Volume_{today}}{Outstanding\_share_{today}} \times 100$ tr
}

app = typer.Typer(help='同步所有 A 股股票和指数的历史日线数据。')


def get_stock_daily_history(
    cfg: config.Config,
    symbol: str,
    start_date: str,
    end_date: str,
    period: str = 'daily',
    adjust: str = 'hfq',
    old_data: DataFrame | None = None,
):
    """
    获取股票每日历史行情数据。

    根据配置的数据源（东方财富或新浪）获取指定股票的日 K 线数据，并计算派生指标。
    支持增量更新和全量获取两种模式。

    Args:
        cfg: 配置对象，包含数据源类型等信息
        symbol: 股票代码，格式为交易所前缀 + 代码（如 'sh600000'）
        start_date: 开始日期，格式为 'YYYYMMDD'
        end_date: 结束日期，格式为 'YYYYMMDD'
        period: 数据周期，默认为 'daily'（日线）
        adjust: 复权类型，默认为 'hfq'（后复权），可选 'qfq'（前复权）、''（不复权）
        old_data: 历史数据 DataFrame，用于增量更新时合并数据

    Returns:
        包含以下字段的 DataFrame：
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

    Note:
        派生指标计算公式：
        - 涨跌额 (ca) = 今日收盘价 - 昨日收盘价
        - 涨跌幅 (cp) = (涨跌额 / 昨日收盘价) × 100
        - 振幅 = ((最高价 - 最低价) / 昨日收盘价 ) × 100
        - 换手率 (tr) = (成交量 / 流通股本) × 100
    """
    if cfg.data_source == 'em':
        new_df = ak.stock_zh_a_hist(
            symbol=symbol[2:],
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if new_df is not None:
            new_df = new_df.rename(columns=EAST_MONEY_DATA_DICT)
            new_df['symbol'] = symbol
        return new_df
    elif cfg.data_source == 'sina':
        new_df = ak.stock_zh_a_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        new_df = new_df.rename(columns=SINA_DATA_DICT)
        new_df['symbol'] = symbol

        # 2. 拼接与彻底去重
        if old_data is not None:
            # 即使 old_data 缺少某些列，concat 也会自动补齐 NaN
            df = pd.concat([old_data, new_df], axis=0, ignore_index=True)
            # 统一日期格式，防止因 str 和 datetime 混用导致去重失败
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
        else:
            df = new_df.sort_values('date').reset_index(drop=True)

        # 3. 【全量重算】派生指标
        # 无论 old_data 有没有这些列，直接通过向量化操作覆盖它们
        # 这样可以自动修补"断层"并统一旧数据格式

        last_close = df['close'].shift(1)

        df['ca'] = df['close'] - last_close
        df['cp'] = (df['ca'] / last_close) * 100
        df['amplitude'] = (df['high'] - df['low']) / last_close * 100

        # 4. 股本与换手率的特殊处理
        if cfg.data_source == 'em':
            # 优先通过东财的成交量和换手率反推股本
            # 即使 old_data 没这列，这里也会全量创建
            df['outstanding_share'] = (df['volume'] * 100) / (df['tr'] / 100)
        else:
            # 如果是新浪源且 old_data 有股本，new_df 没股本，先填充股本再算 tr
            # 这里假设 outstanding_share 这种属性数据在增量时是稳定的
            df['tr'] = (df['volume'] / df['outstanding_share']) * 100

        # 5. 最终清洗
        # 派生指标的首行 NaN 填 0（代表没有变化）
        df[['ca', 'cp', 'amplitude', 'tr']] = df[['ca', 'cp', 'amplitude', 'tr']].fillna(0)

        # 流动股本必须前向 + 后向填充（解决停牌导致的 inf 和首行 NaN）
        df['outstanding_share'] = (
            df['outstanding_share'].replace([np.inf, -np.inf], np.nan).ffill().bfill()
        )
    else:
        raise NotImplementedError(f'不支持数据源 {cfg.data_source}')

    return df


def sync_daily_history(cfg: config.Config):
    """
    同步所有 A 股股票和指数的历史日线数据。

    通过获取上次记录日期之后的新数据进行增量更新。
    对于没有现有数据的股票，从 1970 年开始获取完整历史数据。

    Args:
        cfg: 配置对象，包含 data_dir 路径

    读取文件:
        - {data_dir}/a_code_name.csv: 股票列表
        - {data_dir}/a_index_code_name.csv: 指数列表

    保存文件:
        - {data_dir}/stocks/{code}.csv: 个股日线历史数据
        - {data_dir}/index/{symbol}.csv: 个指数日线历史数据
    """
    data_dir = cfg.data_dir
    today = datetime.date.today().strftime('%Y%m%d')
    logger.info(f'Starting daily history sync for date: {today}')

    a_code_name = pd.read_csv(os.path.join(data_dir, 'a_code_name.csv'), dtype=str)
    a_index_code_name = pd.read_csv(os.path.join(data_dir, 'a_index_code_name.csv'), dtype=str)

    os.makedirs(os.path.join(data_dir, 'stocks'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'index'), exist_ok=True)

    logger.info(f'Syncing daily history for {len(a_code_name)} stocks...')
    stock_success = 0
    stock_error = 0

    for index, row in tqdm(a_code_name.iterrows(), total=len(a_code_name), desc='Stocks'):
        stock_datapath = os.path.join(data_dir, f'stocks/{row["symbol"]}.csv')
        try:
            old_data = pd.read_csv(stock_datapath) if os.path.exists(stock_datapath) else None
        except pd.errors.EmptyDataError:
            logger.warning(f'Empty data file for {row["symbol"]}, will re-fetch full history')
            old_data = None

        last_day = None
        if old_data is not None:
            last_day = old_data.sort_values('date')['date'].tolist()[-1].replace('-', '')

        if old_data is not None and int(last_day) < int(today):
            try:
                stock_daily_history = get_stock_daily_history(
                    cfg,
                    symbol=row['symbol'],
                    start_date=str(int(last_day) + 1),
                    end_date=today,
                )
            except Exception as e:
                logger.error(f'Failed to fetch data for {row["symbol"]} ({row["name"]}): {e}')
                stock_error += 1
                continue
            if stock_daily_history.empty:
                logger.debug(f'No new data for {row["symbol"]} since {last_day}')
                continue
            logger.debug(
                f'Updated {row["symbol"]} ({len(stock_daily_history) - len(old_data)} new records)'
            )
        else:
            try:
                stock_daily_history = get_stock_daily_history(
                    cfg,
                    symbol=row['symbol'],
                    start_date='19700101',
                    end_date=today,
                )
            except Exception as e:
                logger.error(
                    f'Failed to fetch full history for {row["symbol"]} ({row["name"]}): {e}'
                )
                stock_error += 1
                continue
            logger.debug(
                f'Fetched full history for {row["symbol"]} ({len(stock_daily_history)} records)'
            )

        stock_daily_history.to_csv(stock_datapath, index=False)
        stock_success += 1

    logger.info(f'Stock sync completed: {stock_success} success, {stock_error} errors')

    logger.info(f'Syncing daily history for {len(a_index_code_name)} indices...')
    index_success = 0
    index_error = 0

    for index, row in tqdm(
        a_index_code_name.iterrows(), total=len(a_index_code_name), desc='Indices'
    ):
        index_datapath = os.path.join(data_dir, f'index/{row["symbol"]}.csv')
        old_data = pd.read_csv(index_datapath) if os.path.exists(index_datapath) else None

        last_day = None
        if old_data is not None:
            last_day = old_data.sort_values('date')['date'].tolist()[-1].replace('-', '')

        if old_data is not None and int(last_day) < int(today):
            try:
                index_daily_history = ak.stock_zh_index_daily(symbol=row['symbol'])
            except Exception as e:
                logger.error(f'Failed to fetch index data for {row["symbol"]}: {e}')
                index_error += 1
                continue
            if index_daily_history.empty:
                logger.debug(f'No new data for index {row["symbol"]} since {last_day}')
                continue
            index_daily_history = pd.concat(
                [old_data, index_daily_history], axis=0
            ).drop_duplicates(subset=['date'])
            logger.debug(
                f'Updated index {row["symbol"]} ({len(index_daily_history) - len(old_data)} new records)'
            )
        else:
            try:
                index_daily_history = ak.stock_zh_index_daily(symbol=row['symbol'])
            except Exception as e:
                logger.error(f'Failed to fetch full index history for {row["symbol"]}: {e}')
                index_error += 1
                continue
            logger.debug(
                f'Fetched full history for index {row["symbol"]} ({len(index_daily_history)} records)'
            )

        index_daily_history.to_csv(index_datapath, index=False)
        index_success += 1

    logger.info(f'Index sync completed: {index_success} success, {index_error} errors')
    logger.success(f'Daily history sync completed for {today}')


@app.command()
def cmd(ctx: typer.Context):
    cfg: config.Config = ctx.obj
    sync_daily_history(cfg)
