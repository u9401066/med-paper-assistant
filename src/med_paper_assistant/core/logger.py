import os
import logging
from datetime import datetime

def setup_logger(name: str = "med_paper_assistant", log_dir: str = "logs"):
    """
    Setup a logger with file and console handlers.
    
    Args:
        name: Logger name.
        log_dir: Directory to store log files.
        
    Returns:
        Configured logger instance.
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Prevent adding handlers multiple times if function is called repeatedly
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
