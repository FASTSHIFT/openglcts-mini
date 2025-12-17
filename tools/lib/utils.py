#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility Functions Module
"""

import logging

from .test_models import ProgressInfo

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
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
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
    logger.info("=" * len(title))
    logger.info(title)
    logger.info("=" * len(title))


def print_progress(progress: ProgressInfo) -> None:
    """
    Print test progress summary with progress bar

    Args:
        progress: ProgressInfo object containing all progress data
    """
    progress_pct = (
        (progress.current / progress.total * 100) if progress.total > 0 else 0
    )
    bar_width = 40
    filled = (
        int(bar_width * progress.current / progress.total) if progress.total > 0 else 0
    )
    progress_bar = "█" * filled + "░" * (bar_width - filled)

    logger.info("")
    logger.info(
        "Progress: [%s] %s/%s (%.1f%%)",
        progress_bar,
        progress.current,
        progress.total,
        progress_pct,
    )
    logger.info(
        "Results:"
        "  ✅ Passed: %s  ❌ Failed: %s  ⏱ Timeout: %s"
        "  💀 Hang: %s  💥 Crash: %s  ⚠️ Exception: %s",
        progress.stats.passed,
        progress.stats.failed,
        progress.stats.timeout,
        progress.stats.hang,
        progress.stats.crash,
        progress.stats.exception,
    )
    logger.info(
        "Time:     ⏱ Case: %s  📊 Total: %s",
        format_duration(progress.case_duration),
        format_duration(progress.total_duration),
    )
    logger.info("")
