import sys
from pathlib import Path

from loguru import logger

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
