"""
Global project configuration file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from platformdirs import user_data_path, user_log_path

LogLevel = Literal['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
DataSource = Literal['sina', 'em']


@dataclass
class Config:
    data_dir: Path = user_data_path(appname='ashare_sync', appauthor='GOKORURI007')
    data_source: DataSource = 'sina'
    # --- Logger ---
    logger_name: str = 'ashare_sync'
    log_dir: Path = user_log_path(appname='ashare_sync', appauthor='GOKORURI007')  # Log directory
    log_file: str = 'ashare_sync.log'  # Log file name
    log_level_file: LogLevel = 'WARNING'  # File output log level
    log_level_stdout: LogLevel = 'INFO'  # Stdout log level

    def __post_init__(self):
        if isinstance(self.data_dir, str):
            if self.data_dir.startswith('~'):
                self.data_dir = Path(self.data_dir).expanduser()
            self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        if isinstance(self.log_dir, str):
            if self.log_dir.startswith('~'):
                self.log_dir = Path(self.log_dir).expanduser()
            self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(exist_ok=True)
