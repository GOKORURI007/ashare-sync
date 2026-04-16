#!/usr/bin/env python
import os
from typing import Annotated

import akshare as ak
import pandas as pd
import typer
from loguru import logger

from .. import config

app = typer.Typer(help='同步股票和指数列表。')


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
    logger.info('开始同步 A 股股票列表...')

    logger.debug('获取深交所股票列表...')
    sz_code_name = ak.stock_info_sz_name_code()
    logger.debug(f'深交所股票：{len(sz_code_name)} 条记录')

    logger.debug('获取上交所股票列表...')
    sh_code_name = ak.stock_info_sh_name_code()
    logger.debug(f'上交所股票：{len(sh_code_name)} 条记录')

    logger.debug('获取北交所股票列表...')
    bj_code_name = ak.stock_info_bj_name_code()
    logger.debug(f'北交所股票：{len(bj_code_name)} 条记录')

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

    logger.success(f'股票列表同步完成。总计：{len(a_code_name)} 只股票已保存。')


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
    logger.info('开始同步 A 股指数列表...')

    index_info = ak.stock_zh_index_spot_sina()
    logger.debug(f'获取到 {len(index_info)} 条指数记录')

    index_a_code_name = pd.DataFrame({
        'symbol': index_info['代码'],
        'code': index_info['代码'].apply(lambda x: x[2:]),
        'name': index_info['名称'],
    })
    index_a_code_name.to_csv(os.path.join(data_dir, 'a_index_code_name.csv'), index=False)

    logger.success(f'指数列表同步完成。总计：{len(index_a_code_name)} 个指数已保存。')


@app.command()
def cmd(
    ctx: typer.Context,
    skip_stock: Annotated[
        bool | None,
        typer.Option(
            '--skip-stock',
            help='跳过股票列表同步',
        ),
    ] = False,
    skip_index: Annotated[
        bool | None,
        typer.Option(
            '--skip-index',
            help='跳过指数列表同步',
        ),
    ] = False,
):
    cfg: config.Config = ctx.obj
    if not skip_stock:
        sync_stock_list(cfg)
    if not skip_index:
        sync_index_list(cfg)
