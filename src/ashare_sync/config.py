"""
全局项目配置文件。

本模块定义了 ashare-sync 的核心配置类，包括：
- 数据存储路径配置
- 数据源选择（新浪财经或东方财富）
- 日志系统配置（日志级别、输出路径等）

配置采用分层优先级：
1. 默认值：在 Config 数据类中硬编码
2. 配置文件：JSON 格式的持久化配置
3. CLI 参数：命令行参数可覆盖上述配置
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from platformdirs import user_data_path, user_log_path

# 日志级别类型定义
LogLevel = Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
# 数据源类型定义：sina=新浪财经, em=东方财富
DataSource = Literal['sina', 'em']


@dataclass
class Config:
    """A股数据同步工具的配置类。

    使用 dataclass 实现，支持默认值、序列化和反序列化。
    所有路径会在初始化时自动创建对应的目录。

    Attributes:
        data_dir: 数据存储根目录，用于保存股票列表、指数列表和历史行情数据
        data_source: 数据源选择，'sina' 表示新浪财经，'em' 表示东方财富
        logger_name: 日志记录器名称，用于标识日志来源
        log_dir: 日志文件存储目录
        log_file: 日志文件名
        log_level_file: 文件日志的输出级别，默认为 WARNING，减少磁盘写入
        log_level_stdout: 控制台日志的输出级别，默认为 INFO，提供实时反馈
    """

    # 数据存储目录（使用平台特定的用户数据目录）
    data_dir: Path = user_data_path(appname='ashare_sync', appauthor='GOKORURI007')
    # 数据源选择
    data_source: DataSource = 'sina'

    # --- 日志配置 ---
    logger_name: str = 'ashare_sync'  # 日志记录器名称
    log_dir: Path = user_log_path(appname='ashare_sync', appauthor='GOKORURI007')  # 日志目录
    log_file: str = 'ashare_sync.log'  # 日志文件名
    log_level_file: LogLevel = 'WARNING'  # 文件日志级别（仅记录警告及以上）
    log_level_stdout: LogLevel = 'INFO'  # 控制台日志级别（显示信息及以上）

    def __post_init__(self):
        """初始化后处理：确保路径对象正确并创建目录。

        处理以下情况：
        1. 将字符串路径转换为 Path 对象
        2. 展开以 ~ 开头的用户主目录路径
        3. 自动创建数据目录和日志目录（如果不存在）
        """
        # 处理数据目录路径
        if isinstance(self.data_dir, str):
            if self.data_dir.startswith('~'):
                self.data_dir = Path(self.data_dir).expanduser()
            self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(exist_ok=True)  # 创建数据目录

        # 处理日志目录路径
        if isinstance(self.log_dir, str):
            if self.log_dir.startswith('~'):
                self.log_dir = Path(self.log_dir).expanduser()
            self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(exist_ok=True)  # 创建日志目录
