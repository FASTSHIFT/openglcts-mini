#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility Functions Module
"""

import logging

logger = logging.getLogger(__name__)


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure logging
    
    Args:
        level: Logging level, default INFO
        
    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "30.5s", "2m 15.3s", or "1h 30m 45.2s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


def print_title_info(title: str) -> None:
    """
    Print a title with decorative borders
    
    Args:
        title: Title string to print
    """
    logger.info(f"{'=' * len(title)}")
    logger.info(title)
    logger.info(f"{'=' * len(title)}")


def print_progress(
    current: int,
    total: int,
    passed: int,
    failed: int,
    timeout: int,
    hung: int,
    crash: int,
    case_duration: float = 0,
    total_duration: float = 0,
) -> None:
    """
    Print test progress summary with progress bar
    
    Args:
        current: Current test index
        total: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        timeout: Number of timed out tests
        hung: Number of hung tests
        crash: Number of crashed tests
        case_duration: Duration of current case in seconds
        total_duration: Total elapsed time in seconds
    """
    progress_pct = (current / total * 100) if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    logger.info("")
    logger.info(f"Progress: [{bar}] {current}/{total} ({progress_pct:.1f}%)")
    logger.info(
        f"Results:  ✅ Passed: {passed}  ❌ Failed: {failed}  ⏱ Timeout: {timeout}  💀 Hung: {hung}  💥 Crash: {crash}"
    )
    logger.info(
        f"Time:     ⏱ Case: {format_duration(case_duration)}  📊 Total: {format_duration(total_duration)}"
    )
    logger.info("")
