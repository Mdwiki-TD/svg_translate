"""Unit tests for log module logger name change."""
from __future__ import annotations

import logging


def test_log_module_uses_svg_translate_logger():
    """Test that log.py creates logger with 'svg_translate' name."""
    from src import log
    
    assert log.logger.name == "svg_translate"


def test_log_module_logger_has_correct_handlers():
    """Test that the logger has file and error handlers attached."""
    from src import log
    
    assert len(log.logger.handlers) >= 2
    handler_types = [type(h).__name__ for h in log.logger.handlers]
    assert "WatchedFileHandler" in handler_types


def test_log_module_logger_level_is_debug():
    """Test that the logger level is set to DEBUG."""
    from src import log
    
    assert log.logger.level == logging.DEBUG


def test_config_console_logger_adds_stream_handler():
    """Test that config_console_logger adds a StreamHandler."""
    from src import log
    
    initial_handler_count = len(log.logger.handlers)
    
    log.config_console_logger(logging.INFO)
    
    # Should have added one more handler
    assert len(log.logger.handlers) >= initial_handler_count + 1
    
    # Check for StreamHandler
    stream_handlers = [h for h in log.logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) > 0