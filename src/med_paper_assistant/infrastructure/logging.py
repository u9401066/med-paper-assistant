"""
Logging Configuration — structlog + stdlib hybrid.

structlog 包裝 stdlib logging，讓每個模組的 logger 都是 structured logger，
同時保留現有的 file handler（每日一個 log 檔）與 console handler。

日誌存放位置（跨平台）:
- 專案目錄: {project_root}/logs/
- 每日一個檔案: YYYYMMDD.log
- 檔案格式: JSON Lines（方便 grep/jq 分析）
- Console 格式: 彩色 key=value（開發友善）
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog


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


_configured = False


def configure_structlog() -> None:
    """
    Configure structlog to wrap stdlib logging.

    Call once at application startup (idempotent).
    After this, ``structlog.get_logger()`` returns a bound logger that
    ultimately delegates to the stdlib root logger named *med_paper_assistant*.
    """
    global _configured
    if _configured:
        return

    # Shared processors for both structlog-originated and stdlib-originated events
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configure structlog to route through stdlib
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    _configured = True


def setup_logger(
    name: str = "med_paper_assistant", log_dir: Optional[str] = None, level: int = logging.DEBUG
) -> logging.Logger:
    """
    Setup stdlib root logger with file and console handlers,
    then configure structlog on top.

    Args:
        name: Logger name.
        log_dir: Directory to store log files. If None, uses {project}/logs/.
        level: Logging level.

    Returns:
        Configured stdlib logger instance (for backward compatibility).
    """
    # 使用專案內的 logs 目錄
    if log_dir is None:
        log_dir = str(_get_project_log_dir())

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    stdlib_logger = logging.getLogger(name)
    stdlib_logger.setLevel(level)

    # Prevent adding handlers multiple times
    if not stdlib_logger.hasHandlers():
        # File Handler - JSON Lines for machine parsing
        filename = f"{datetime.now().strftime('%Y%m%d')}.log"
        filepath = os.path.join(log_dir, filename)
        fh = logging.FileHandler(filepath, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso"),
                ],
            )
        )

        # Console Handler - coloured key=value for humans
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(),
                foreign_pre_chain=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso"),
                ],
            )
        )

        stdlib_logger.addHandler(fh)
        stdlib_logger.addHandler(ch)

        stdlib_logger.info("Log file: %s", filepath)

    # Ensure structlog is wired up
    configure_structlog()

    return stdlib_logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog bound logger.

    Args:
        name: Logger name. If None, uses caller's module name via structlog default.

    Returns:
        A structlog BoundLogger that routes through stdlib handlers.
    """
    # Ensure handlers are set up at least once
    global _logger
    if _logger is None:
        _logger = setup_logger()

    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()
