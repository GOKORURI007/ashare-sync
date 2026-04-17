#!/usr/bin/env python
import os

import akshare as ak
import pandas as pd
import typer
from loguru import logger
from pandas import DataFrame
from tqdm import tqdm

from .. import config

INDEX_CONS_DATA_DICT = {
    '日期': 'date',
    '指数代码': 'symbol',
    '指数名称': 'name',
    '指数英文名称': 'name_en',
    '成分券代码': 'stock_symbol',
    '成分券名称': 'stock_name',
    '成分券英文名称': 'stock_name_en',
    '交易所': 'exchange',
    '交易所英文名称': 'exchange_en',
}

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

    sz_code_name.to_parquet(os.path.join(data_dir, 'sz_code_name.parquet'), index=False)
    sh_code_name.to_parquet(os.path.join(data_dir, 'sh_code_name.parquet'), index=False)
    bj_code_name.to_parquet(os.path.join(data_dir, 'bj_code_name.parquet'), index=False)
    a_code_name.to_parquet(os.path.join(data_dir, 'a_code_name.parquet'), index=False)

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
    index_a_code_name.to_parquet(os.path.join(data_dir, 'a_index_code_name.parquet'), index=False)

    logger.success(f'指数列表同步完成。总计：{len(index_a_code_name)} 个指数已保存。')


def sync_index_composition(
    cfg: config.Config, index_code_name: DataFrame, stock_code_name: DataFrame
):
    # 1. 预创建保存目录
    save_dir = cfg.data_dir / 'index composition'
    save_dir.mkdir(parents=True, exist_ok=True)

    # 2. 优化：建立 code -> symbol 的映射字典，避免在 apply 里循环查询
    # 这样查找速度从 O(N) 变为 O(1)
    symbol_map = dict(zip(stock_code_name['code'], stock_code_name['symbol']))

    for _, row in tqdm(
        index_code_name.iterrows(), total=len(index_code_name), desc='Syncing Index Cons'
    ):
        # 获取成分股列表 (中证指数官网源)
        df = ak.index_stock_cons_csindex(symbol=row['code'])
        df = df.rename(columns=INDEX_CONS_DATA_DICT)

        # 3. 映射成分股 symbol
        # 使用 map 替代 apply 配合 loc，效率提升巨大
        df['stock_symbol'] = df['stock_symbol'].map(symbol_map)

        # 4. 保存结果
        file_path = save_dir / f'{row["symbol"]}.parquet'
        df.to_parquet(file_path, index=False)


@app.command()
def cmd(
    ctx: typer.Context,
    skip_stock: bool = typer.Option(False, '--skip-stock', help='跳过股票列表同步'),
    skip_index: bool = typer.Option(False, '--skip-index', help='跳过指数列表同步'),
    cons_list: list[str] = typer.Option(
        ['sh000300'],
        '--cons-list',
        help='需要同步的指数成分列表，如sh000300。\n可输入full同步所有指数的成分',
    ),
):
    cfg: config.Config = ctx.obj

    # 同步基础列表
    if not skip_stock:
        sync_stock_list(cfg)
    if not skip_index:
        sync_index_list(cfg)

    # 加载基础对照表
    # a_index_code_name 包含指数代码，a_stock_code_name 包含个股代码
    index_code_name = pd.read_parquet(os.path.join(cfg.data_dir, 'a_index_code_name.parquet'))
    stock_code_name = pd.read_parquet(os.path.join(cfg.data_dir, 'a_code_name.parquet'))

    # 根据 cons_list 过滤需要同步的指数
    if 'full' not in cons_list:
        index_code_name = index_code_name[index_code_name['symbol'].isin(cons_list)]

    # 执行同步
    if not index_code_name.empty:
        sync_index_composition(cfg, index_code_name, stock_code_name)
    else:
        typer.echo('没有找到匹配的指数代码，请检查 --cons-list 输入')
