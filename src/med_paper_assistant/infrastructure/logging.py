"""
Logging Configuration.

日誌存放位置（跨平台）:
- 專案目錄: {project_root}/logs/
- 每日一個檔案: YYYYMMDD.log
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_project_log_dir() -> Path:
    """
    取得專案內的 logs 目錄（跨平台支援）。

    Returns:
        Path to {project_root}/logs/
    """
    # 找到專案根目錄（包含 pyproject.toml 的目錄）
    current = Path(__file__).resolve()

    # 向上查找直到找到 pyproject.toml
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            log_dir = parent / "logs"
            log_dir.mkdir(exist_ok=True)
            return log_dir

    # Fallback: 使用當前工作目錄
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


def setup_logger(
    name: str = "med_paper_assistant", log_dir: Optional[str] = None, level: int = logging.DEBUG
) -> logging.Logger:
    """
    Setup a logger with file and console handlers.

    日誌存放在專案目錄的 logs/ 資料夾中（支援 Windows/Linux/macOS）。

    Args:
        name: Logger name.
        log_dir: Directory to store log files. If None, uses {project}/logs/.
        level: Logging level.

    Returns:
        Configured logger instance.
    """
    # 使用專案內的 logs 目錄
    if log_dir is None:
        log_dir = str(_get_project_log_dir())

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        return logger

    # File Handler - DEBUG level (記錄所有詳細資訊)
    filename = f"{datetime.now().strftime('%Y%m%d')}.log"
    filepath = os.path.join(log_dir, filename)
    fh = logging.FileHandler(filepath, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console Handler - INFO level (只顯示重要訊息)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter with more context
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    fh.setFormatter(file_formatter)
    ch.setFormatter(console_formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    # Log the log file location on first setup
    logger.info(f"Log file: {filepath}")

    return logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
