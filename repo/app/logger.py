"""
Structured logging with PII redaction
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

# Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "./logs/app.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# PII patterns to redact
PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]'),  # SSN
    (r'\b\d{16}\b', '[CC-REDACTED]'),  # Credit card
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-REDACTED]'),  # Email
]


class PIIRedactingFormatter(logging.Formatter):
    """Custom formatter that redacts PII"""
    
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        
        # Redact PII patterns
        redacted = original
        for pattern, replacement in PII_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted)
        
        return redacted


def setup_logger(name: str = __name__) -> logging.Logger:
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = PIIRedactingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (with rotation)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Create default logger
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    return setup_logger(name)