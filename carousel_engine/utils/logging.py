"""
Logging configuration and utilities
"""

import logging
import sys
from typing import Optional
import structlog
from structlog.typing import FilteringBoundLogger

from ..core.config import config


def configure_logging(
    level: Optional[str] = None,
    format_json: bool = True
) -> None:
    """Configure application logging
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_json: Whether to use JSON formatting
    """
    log_level = level or config.log_level
    
    # Configure stdlib logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        stream=sys.stdout,
        format="%(message)s" if format_json else "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if format_json:
        processors.extend([
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer()
        ])
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        # Add correlation ID if available in context
        # This could be enhanced with request tracing
        record.correlation_id = getattr(record, 'correlation_id', None)
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from log records"""
    
    SENSITIVE_KEYS = [
        'api_key', 'token', 'password', 'secret', 'credentials',
        'auth', 'authorization', 'bearer'
    ]
    
    def filter(self, record):
        # Filter sensitive data from log message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    record.msg = record.msg.replace(
                        record.msg, 
                        "[FILTERED - SENSITIVE DATA]"
                    )
        
        # Filter sensitive data from record attributes
        for key in list(vars(record).keys()):
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                setattr(record, key, "[FILTERED]")
        
        return True