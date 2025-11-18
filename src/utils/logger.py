"""
Logging system for the literature review system.

Provides structured logging with different levels, file rotation,
and console output with formatting.
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import json

try:
    from rich.logging import RichHandler
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichHandler = None
    Console = None

from ..core.config import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'provider'):
            log_entry['provider'] = record.provider
        if hasattr(record, 'model'):
            log_entry['model'] = record.model
        if hasattr(record, 'tokens_used'):
            log_entry['tokens_used'] = record.tokens_used
        if hasattr(record, 'cost'):
            log_entry['cost'] = record.cost
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class LiteratureReviewLogger:
    """
    Enhanced logging system for the literature review pipeline.
    
    Features:
    - Structured JSON logging for file output
    - Rich console output for development
    - Task-specific logging contexts
    - Performance and cost tracking
    - Automatic log rotation
    """
    
    def __init__(self, name: str = "literature_review"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Get configuration
        config = get_config()
        log_level = config.get('logging.level', 'INFO')
        log_file = config.get('logging.file', './data/system.log')
        
        # Create log directory
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # File handler with JSON formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
        
        # Console handler
        if RICH_AVAILABLE:
            console = Console(stderr=True)
            console_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True
            )
        else:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        console_handler.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional extra fields."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional extra fields."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional extra fields."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional extra fields."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with optional extra fields."""
        self.logger.critical(message, extra=kwargs)
    
    def log_llm_call(self, provider: str, model: str, tokens_used: int, cost: float, task: str):
        """
        Log an LLM API call with usage metrics.
        
        Args:
            provider: LLM provider name
            model: Model name
            tokens_used: Number of tokens used
            cost: Cost in USD
            task: Task description
        """
        self.info(
            f"LLM Call: {task}",
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            cost=cost
        )
    
    def log_search_query(self, source: str, query: str, results_count: int):
        """Log a search query execution."""
        self.info(
            f"Search executed: {source}",
            source=source,
            query=query,
            results_count=results_count
        )
    
    def log_paper_processed(self, paper_id: str, title: str, status: str):
        """Log paper processing status."""
        self.info(
            f"Paper processed: {status}",
            paper_id=paper_id,
            title=title[:100] + "..." if len(title) > 100 else title,
            status=status
        )
    
    def log_stage_progress(self, stage: str, current: int, total: int, message: str = ""):
        """Log progress through a processing stage."""
        progress_pct = (current / total * 100) if total > 0 else 0
        self.info(
            f"Stage {stage}: {current}/{total} ({progress_pct:.1f}%) {message}",
            stage=stage,
            current=current,
            total=total,
            progress_pct=progress_pct
        )
    
    def log_error_with_context(self, error: Exception, context: dict):
        """Log error with additional context information."""
        self.error(
            f"Error in {context.get('operation', 'unknown operation')}: {str(error)}",
            operation=context.get('operation'),
            paper_id=context.get('paper_id'),
            provider=context.get('provider'),
            **context
        )
    
    def create_task_logger(self, task_id: str, task_name: str):
        """
        Create a logger for a specific task.
        
        Args:
            task_id: Unique task identifier
            task_name: Human-readable task name
            
        Returns:
            TaskLogger instance
        """
        return TaskLogger(self.logger, task_id, task_name)


class TaskLogger:
    """
    Logger for a specific task with automatic context.
    """
    
    def __init__(self, logger: logging.Logger, task_id: str, task_name: str):
        self.logger = logger
        self.task_id = task_id
        self.task_name = task_name
        self.parent_logger = None  # Reference to parent for progress logging
    
    def _log_with_task_context(self, level: str, message: str, **kwargs):
        """Log message with task context."""
        # Remove custom kwargs that aren't supported by logging
        log_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
        
        # Add task context to extra field
        if 'extra' not in log_kwargs:
            log_kwargs['extra'] = {}
        log_kwargs['extra']['task_id'] = self.task_id
        log_kwargs['extra']['task_name'] = self.task_name
        
        getattr(self.logger, level)(f"[{self.task_name}] {message}", **log_kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_task_context('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_task_context('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_task_context('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_task_context('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_task_context('critical', message, **kwargs)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Update progress for this task.
        
        Args:
            current: Current progress count
            total: Total items to process
            message: Optional progress message
        """
        progress_pct = (current / total * 100) if total > 0 else 0
        self.info(f"Progress: {current}/{total} ({progress_pct:.1f}%) {message}")


# Global logger instance
main_logger = LiteratureReviewLogger()


def get_logger(name: Optional[str] = None) -> LiteratureReviewLogger:
    """Get logger instance."""
    if name:
        return LiteratureReviewLogger(name)
    return main_logger


def setup_logging(config_path: Optional[str] = None):
    """Setup logging system with optional custom config."""
    if config_path:
        # Custom configuration would be loaded here
        pass
    
    return main_logger