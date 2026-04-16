import json
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import Annotated

import rich
import typer
from click.core import ParameterSource
from platformdirs import user_config_path, user_data_path, user_log_path
from rich.console import Console
from rich.table import Table

from . import __version__
from .commands import sync_hist, sync_list
from .config import Config, DataSource, LogLevel

app = typer.Typer(help='ashare_sync', add_completion=True)
app.command(name="sync-list", help='Sync stock&index list.')(sync_list.cmd)
app.command(name="sync-hist", help='同步所有 A 股股票和指数的历史日线数据。')(sync_hist.cmd)


def version_callback(value: bool):
    if value:
        typer.echo(f'ashare_sync Version: {__version__}')
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[Path, typer.Option(help='Path to the configuration file')] = user_config_path(
        appname='ashare_sync', ensure_exists=True
    ) / 'config.json',
    data_dir: Annotated[Path | None, typer.Option(help='Log directory location')] = user_data_path(
        appname='ashare_sync', appauthor='GOKORURI007'
    ),
    data_source: Annotated[DataSource | None, typer.Option(help='数据源')] = 'sina',
    logger_name: Annotated[str | None, typer.Option(help='Logger name')] = 'ashare_sync',
    log_dir: Annotated[Path | None, typer.Option(help='Log directory location')] = user_log_path(
        appname='ashare_sync', appauthor='GOKORURI007'
    ),
    log_file: Annotated[str | None, typer.Option(help='Log file name')] = 'ashare_sync.log',
    log_level_file: Annotated[LogLevel | None, typer.Option(help='File log level')] = 'WARNING',
    log_level_stdout: Annotated[LogLevel | None, typer.Option(help='Console log level')] = 'INFO',
    show_config: Annotated[
        bool | None,
        typer.Option(
            '--show-config',
            help='Show current config.',
        ),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option(
            '--version',
            '-v',
            help='Show the version and exit.',
            callback=version_callback,
            is_eager=True,  # 确保在其他参数处理之前运行
        ),
    ] = None,
):
    """
    Synchronizing A-share data, which supports overriding JSON configurations via command-line arguments.
    The priority is CLI > config_file > default
    """

    # 1. Load the JSON configuration file
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('{}', encoding='utf-8')

    try:
        with open(config, 'r', encoding='utf-8') as f:
            json_dict = json.load(f)
    except json.JSONDecodeError:
        json_dict = {}

    # 2. Instantiate base configuration (filter invalid fields)
    valid_fields = {f.name for f in fields(Config)}
    filtered_json = {k: v for k, v in json_dict.items() if k in valid_fields}
    cfg = Config(**filtered_json)

    # 3. Collect the parameters passed in by the CLI (i.e. the non-non-none) part of locals())
    # Exclude parameters that are not Config fields, such as config_file
    cli_args = locals()
    overrides = {}
    for k in valid_fields:
        if k in cli_args:
            source = ctx.get_parameter_source(k)
            if source != ParameterSource.DEFAULT:
                overrides[k] = cli_args[k]

    # Override config
    cfg = replace(cfg, **overrides)

    if show_config:
        # 方法 A：快速调试（带颜色、类型和属性说明）
        console = Console()
        table = Table(box=rich.table.box.ROUNDED, border_style='medium_purple')
        table.add_column('Config', style='dim')
        table.add_column('Value')

        # 使用 asdict 确保只获取实例的数据
        for key, value in asdict(cfg).items():
            table.add_row(key, str(value))

        console.print(table)
        return

    ctx.obj = cfg
