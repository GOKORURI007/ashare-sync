#!/usr/bin/env python
import os
from typing import Annotated

import akshare as ak
import pandas as pd
import typer
from loguru import logger

from .. import config

app = typer.Typer(help='Sync stock&index list.')


def sync_stock_list(cfg: config.Config):
    """
    同步所有 A 股股票代码和名称。

    通过 akshare 从上海、深圳、北京三个交易所获取股票列表，
    合并为统一列表并保存为 CSV 文件。

    Args:
        cfg: 配置对象，包含 data_dir 路径

    保存文件:
        - {data_dir}/a_code_name.csv: 统一股票列表，包含 symbol、code、name
        - {data_dir}/sz_code_name.csv: 深交所股票列表
        - {data_dir}/sh_code_name.csv: 上交所股票列表
        - {data_dir}/bj_code_name.csv: 北交所股票列表
    """
    data_dir = cfg.data_dir
    logger.info('Starting A-share stock list sync...')

    logger.debug('Fetching Shenzhen stock list...')
    sz_code_name = ak.stock_info_sz_name_code()
    logger.debug(f'Shenzhen stocks: {len(sz_code_name)} records')

    logger.debug('Fetching Shanghai stock list...')
    sh_code_name = ak.stock_info_sh_name_code()
    logger.debug(f'Shanghai stocks: {len(sh_code_name)} records')

    logger.debug('Fetching Beijing stock list...')
    bj_code_name = ak.stock_info_bj_name_code()
    logger.debug(f'Beijing stocks: {len(bj_code_name)} records')

    a_code_name = pd.DataFrame({
        'symbol': pd.concat(
            [
                sz_code_name['A股代码'].apply(lambda x: 'sz' + x),
                sh_code_name['证券代码'].apply(lambda x: 'sh' + x),
                bj_code_name['证券代码'].apply(lambda x: 'bj' + x),
            ],
            axis=0,
        ),
        'code': pd.concat(
            [sz_code_name['A股代码'], sh_code_name['证券代码'], bj_code_name['证券代码']], axis=0
        ),
        'name': pd.concat(
            [sz_code_name['A股简称'], sh_code_name['证券简称'], bj_code_name['证券简称']], axis=0
        ),
    })

    sz_code_name.to_csv(os.path.join(data_dir, 'sz_code_name.csv'), index=False)
    sh_code_name.to_csv(os.path.join(data_dir, 'sh_code_name.csv'), index=False)
    bj_code_name.to_csv(os.path.join(data_dir, 'bj_code_name.csv'), index=False)
    a_code_name.to_csv(os.path.join(data_dir, 'a_code_name.csv'), index=False)

    logger.success(f'Stock list sync completed. Total: {len(a_code_name)} stocks saved.')


def sync_index_list(cfg: config.Config):
    """
    同步所有 A 股指数代码和名称。

    通过 akshare 从新浪财经获取指数列表并保存为 CSV 文件。

    Args:
        cfg: 配置对象，包含 data_dir 路径

    保存文件:
        - {data_dir}/a_index_code_name.csv: 指数列表，包含 symbol、code、name
    """
    data_dir = cfg.data_dir
    logger.info('Starting A-share index list sync...')

    index_info = ak.stock_zh_index_spot_sina()
    logger.debug(f'Fetched {len(index_info)} index records')

    index_a_code_name = pd.DataFrame({
        'symbol': index_info['代码'],
        'code': index_info['代码'].apply(lambda x: x[2:]),
        'name': index_info['名称'],
    })
    index_a_code_name.to_csv(os.path.join(data_dir, 'a_index_code_name.csv'), index=False)

    logger.success(f'Index list sync completed. Total: {len(index_a_code_name)} indices saved.')


@app.command()
def cmd(
    ctx: typer.Context,
    skip_stock: Annotated[
        bool | None,
        typer.Option(
            '--skip-stock',
            help='Skip stock list sync',
        ),
    ] = False,
    skip_index: Annotated[
        bool | None,
        typer.Option(
            '--skip-index',
            help='Skip index list sync',
        ),
    ] = False,
):
    cfg: config.Config = ctx.obj
    if not skip_stock:
        sync_stock_list(cfg)
    if not skip_index:
        sync_index_list(cfg)
