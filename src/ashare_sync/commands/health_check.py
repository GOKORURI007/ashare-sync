import akshare as ak
import typer
from pandas import DataFrame

from .. import config

app = typer.Typer(help='检查数据集的数据完整性和正确性。')


def update_trade_date(cfg: config.Config) -> DataFrame:
    """更新交易日日历"""
    df = ak.tool_trade_date_hist_sina()
    df.to_csv(cfg.data_dir / 'trade_date.csv')
    return df


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
    update_trade_date(cfg)
    ...


@app.command()
def cmd(
    ctx: typer.Context,
    fix: bool = typer.Option(False, '--fix', help='自动修复错误')
):
    ...
