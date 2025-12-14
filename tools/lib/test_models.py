#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Data Models Module - Data classes for test configuration and results
"""

from dataclasses import dataclass
from typing import TextIO


@dataclass
class TestStats:
    """Statistics for test execution results"""

    passed: int = 0
    failed: int = 0
    timeout: int = 0
    hang: int = 0
    crash: int = 0

    def total_completed(self) -> int:
        """Calculate total completed tests"""
        return self.passed + self.failed + self.timeout + self.hang + self.crash


@dataclass
class TestIndexInfo:
    """Information about test indexing"""

    idx: int
    total_to_test: int
    total_groups: int
    start_idx: int


@dataclass
class FileHandles:
    """File handles for logging and reporting"""

    log_file: TextIO
    csv_writer: "csv.writer"
    csv_file: TextIO


@dataclass
class TestCaseReport:
    """Data class for test case reporting"""

    files: FileHandles
    actual_idx: int
    group_path: str
    test_result: str
    case_start_time: float
    case_start_datetime: str


@dataclass
class TestEnvironment:
    """Test environment configuration"""

    log_dir: str
    ser: "serial.Serial"
    args: "argparse.Namespace"
    stats: TestStats
    files: FileHandles
    total_start_time: float


@dataclass
class TestConfig:
    """Configuration for running a single test group"""

    index_info: TestIndexInfo
    group_path: str
    environment: TestEnvironment


@dataclass
class FinalSummary:
    """Data class for final test summary"""

    files: FileHandles
    csv_filepath: str
    stats: TestStats
    total_groups: int
    skipped_groups: int
    total_to_test: int
    total_start_time: float


@dataclass
class ProgressStats:
    """Statistics for progress reporting"""

    passed: int
    failed: int
    timeout: int
    hang: int
    crash: int


@dataclass
class ProgressInfo:
    """Data class for progress reporting"""

    current: int
    total: int
    stats: ProgressStats
    case_duration: float = 0
    total_duration: float = 0
