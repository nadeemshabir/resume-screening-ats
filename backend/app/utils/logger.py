"""
Logging System
Provides structured logging across the application
"""
import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logger():
    """
    Configure loguru logger with proper formatting and handlers
    """
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
    )
    
    # File handler for all logs
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.LOG_FILE,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress rotated logs
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
    )
    
    # Error-only file handler
    logger.add(
        log_path.parent / "errors.log",
        rotation="5 MB",
        retention="90 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
    )
    
    logger.info("Logger initialized successfully")
    return logger


# Initialize logger
app_logger = setup_logger()


# Convenience functions
def log_info(message: str, **kwargs):
    """Log info message with optional context"""
    app_logger.info(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log error message with optional context"""
    app_logger.error(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message with optional context"""
    app_logger.warning(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message with optional context"""
    app_logger.debug(message, **kwargs)


def log_exception(exception: Exception, message: str = "Exception occurred"):
    """Log exception with full traceback"""
    app_logger.exception(f"{message}: {str(exception)}")