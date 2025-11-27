"""
Logging Configuration.
"""

import os
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "med_paper_assistant",
    log_dir: Optional[str] = None,
    level: int = logging.DEBUG
) -> logging.Logger:
    """
    Setup a logger with file and console handlers.
    
    Args:
        name: Logger name.
        log_dir: Directory to store log files. If None, uses system temp directory.
        level: Logging level.
        
    Returns:
        Configured logger instance.
    """
    # Use temp directory to avoid polluting project root
    if log_dir is None:
        log_dir = os.path.join(tempfile.gettempdir(), "med_paper_assistant_logs")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        return logger
    
    # File Handler
    filename = f"{datetime.now().strftime('%Y%m%d')}.log"
    filepath = os.path.join(log_dir, filename)
    fh = logging.FileHandler(filepath, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
