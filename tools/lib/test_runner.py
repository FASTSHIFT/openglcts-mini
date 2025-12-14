#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Runner Module - Main test execution logic
"""

import os
import csv
import time
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

try:
    from tabulate import tabulate
except ImportError:
    print("Please install 'tabulate' package: pip install tabulate")
    sys.exit(1)

from .test_parser import TestCaseParser
from .serial_utils import (
    serial_open,
    serial_write,
    serial_wait_for_response,
)
from .device_control import check_system_alive, reset_device
from .utils import format_duration, print_title_info, print_progress
from .test_models import (
    TestCaseReport,
    TestConfig,
    FinalSummary,
    TestIndexInfo,
    FileHandles,
    ProgressInfo,
    ProgressStats,
    TestEnvironment,
)


@dataclass
class FoundResultData:
    """Data class for found result handling parameters"""

    found_data: Any
    accumulated_buffer: str
    log_file: Any
    print_output: bool
    group_path: str
    stats: Dict[str, int]


@dataclass
class TestGroupInfo:
    """Information about test groups to execute"""

    groups_to_test: list
    total_groups: int
    start_idx: int
    total_to_test: int


@dataclass
class FileHandlingInfo:
    """Information about file handling for test execution"""

    csv_filepath: str
    csv_file: Any
    csv_writer: Any


@dataclass
class TestGroupSetupInfo:
    """Information about test groups setup"""

    groups_to_test: list
    total_groups: int
    start_idx: int
    total_to_test: int


@dataclass
class TestEnvironmentSetupInfo:
    """Information about test environment setup"""

    log_dir: str
    ser: Any


@dataclass
class TestSetupData:
    """Data class for test setup parameters"""

    args: Any
    group_info: TestGroupSetupInfo
    environment_info: TestEnvironmentSetupInfo
    stats: Dict[str, int]
    total_start_time: float


@dataclass
class TestExecutionData:
    """Data class for test execution parameters"""

    group_info: TestGroupInfo
    log_dir: str
    ser: Any
    args: Any
    stats: Dict[str, int]
    total_start_time: float
    file_info: FileHandlingInfo


logger = logging.getLogger(__name__)


def build_test_command(group_path: str) -> str:
    """
    Build test command for a group

    Args:
        group_path: Full path of the test group

    Returns:
        Command string to execute
    """
    cmd = (
        f"openglcts "
        f'--deqp-archive-dir="/tmp/data" '
        f"--deqp-surface-type=fbo "
        f"--deqp-surface-width=256 "
        f"--deqp-surface-height=256 "
        f"--deqp-case='{group_path}.*' "
        f"--deqp-log-filename=/dev/null &\n"
    )
    return cmd


def _handle_found_result(result_data: FoundResultData):
    """
    Handle the case when test result is found.

    Args:
        result_data: FoundResultData object containing all result handling data

    Returns:
        Tuple of (test_completed, test_crashed, test_result)
    """
    matched_keyword = result_data.found_data[2]  # Only need matched_keyword
    test_completed = False
    test_crashed = False
    test_result = "UNKNOWN"

    if matched_keyword and "panic" in matched_keyword.lower():
        logger.error("Group %s CRASHED (PANIC detected)!", result_data.group_path)

        # Now write result marker after crash log is fully collected
        result_data.log_file.write("\n# Result: CRASH (PANIC)\n")
        result_data.stats["crash"] += 1
        test_crashed = True
        test_result = "CRASH"
    else:
        # Check if there are any "Fail (" patterns in the accumulated buffer
        if "Fail (" in result_data.accumulated_buffer:
            logger.warning(
                "Group %s completed with FAILURES detected.", result_data.group_path
            )
            result_data.log_file.write("\n\n# Result: FAILED (Fail pattern detected)\n")
            result_data.stats["failed"] += 1
            test_completed = True
            test_result = "FAILED"
        else:
            logger.info("Group %s completed successfully.", result_data.group_path)
            result_data.log_file.write("\n\n# Result: PASSED\n")
            result_data.stats["passed"] += 1
            test_completed = True
            test_result = "PASSED"

    return test_completed, test_crashed, test_result


def _check_system_status(ser, args, log_file, print_output, wait_count):
    """
    Check if system is alive and handle the response.

    Args:
        ser: Serial port object
        args: Parsed command line arguments
        log_file: Log file object
        print_output: Whether to print output to console
        wait_count: Current wait count

    Returns:
        Tuple of (system_alive, should_continue)
    """
    logger.warning(
        "No data received within %ss, checking system status (attempt %s/%s)...",
        args.test_timeout,
        wait_count,
        args.max_wait_count,
    )
    system_alive = check_system_alive(ser, args.test_timeout, log_file, print_output)
    if system_alive:
        logger.info("System is still alive (free responded). Continuing to wait...")
        return True, True
    return False, False


def _wait_for_test_result(
    ser, args, log_file, group_path: str, stats: Dict[str, int]
) -> str:
    """
    Wait for test completion and handle result.

    Args:
        ser: Serial port object
        args: Parsed command line arguments
        log_file: Log file object
        group_path: Current test group path
        stats: Statistics dictionary

    Returns:
        Test result string: "PASSED", "CRASH", "HANG", or "TIMEOUT"
    """
    print_output = getattr(args, "print_output", False)
    wait_count = 0
    test_completed = False
    test_crashed = False
    test_result = "UNKNOWN"
    accumulated_buffer = ""

    while wait_count < args.max_wait_count:
        logger.info(
            "Waiting for test completion (free check count: %s/%s)...",
            wait_count,
            args.max_wait_count,
        )

        found_data = serial_wait_for_response(
            ser, ["DONE!", "PANIC"], args.test_timeout, log_file, print_output
        )
        accumulated_buffer += found_data[3]  # buffer

        if found_data[0]:  # found
            result_data = FoundResultData(
                found_data=found_data,
                accumulated_buffer=accumulated_buffer,
                log_file=log_file,
                print_output=print_output,
                group_path=group_path,
                stats=stats,
            )
            test_completed, test_crashed, test_result = _handle_found_result(
                result_data
            )
            break

        if found_data[1]:  # has_any_data
            logger.info(
                "Received data during wait, system is alive. Continuing to wait..."
            )
            continue

        wait_count += 1
        _, should_continue = _check_system_status(
            ser, args, log_file, print_output, wait_count
        )
        if should_continue:
            continue

        logger.error("System is not responding! Breaking wait loop.")
        log_file.write("\n\n# Result: SYSTEM HANG\n")
        stats["hang"] += 1
        test_result = "HANG"
        break

    if not test_completed and not test_crashed:
        if wait_count >= args.max_wait_count:
            logger.error(
                "Group %s exceeded max wait count (%s). Moving to next test.",
                group_path,
                args.max_wait_count,
            )
            log_file.write("\n\n# Result: TIMEOUT (exceeded max wait count)\n")
            stats["timeout"] += 1
            test_result = "TIMEOUT"

    return test_result


def _write_test_case_report(report: TestCaseReport) -> float:
    """
    Write test case report to log and CSV.

    Args:
        report: TestCaseReport object containing all report data

    Returns:
        Case duration in seconds
    """
    case_end_time = time.time()
    case_end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    case_duration = case_end_time - report.case_start_time

    report.files.csv_writer.writerow(
        [
            report.actual_idx,
            report.group_path,
            report.test_result,
            f"{case_duration:.2f}",
            report.case_start_datetime,
            case_end_datetime,
        ]
    )
    report.files.csv_file.flush()

    report.files.log_file.write(
        f"\n# End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    report.files.log_file.write(f"# Duration: {format_duration(case_duration)}\n")

    logger.info("Case duration: %s", format_duration(case_duration))
    return case_duration


def _parse_test_groups(args):
    """
    Parse XML file and get test groups to run.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (group_paths, total_groups, start_idx, groups_to_test, skipped_groups)
    """
    test_parser = TestCaseParser(args.file)
    test_parser.parse()
    group_paths = test_parser.get_leaf_group_paths()
    total_groups = len(group_paths)

    # Handle --start-group option
    start_idx = 0
    if args.start_group:
        found = False
        for i, path in enumerate(group_paths):
            if args.start_group in path or path == args.start_group:
                start_idx = i
                found = True
                logger.info(
                    "Starting from group: %s (index %s/%s)", path, i + 1, total_groups
                )
                break
        if not found:
            logger.error("Start group '%s' not found in test groups!", args.start_group)
            logger.info("Available groups containing the keyword:")
            matches = [p for p in group_paths if args.start_group.lower() in p.lower()]
            for m in matches[:10]:
                logger.info("  - %s", m)
            if len(matches) > 10:
                logger.info("  ... and %s more", len(matches) - 10)
            return None, None, None, None, None

    # Slice groups to start from specified index
    groups_to_test = group_paths[start_idx:]
    skipped_groups = start_idx

    print_title_info(
        f"Total leaf groups to test: {len(groups_to_test)} (skipped: {skipped_groups})"
    )

    return group_paths, total_groups, start_idx, groups_to_test, skipped_groups


def _setup_test_environment(args):
    """
    Setup test environment including log directory and serial port.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (log_dir, ser)
    """
    # Create log directory
    if args.log_dir:
        log_dir = args.log_dir
    else:
        log_dir = datetime.now().strftime("logs_%Y%m%d_%H%M%S")

    os.makedirs(log_dir, exist_ok=True)
    logger.info("Log directory: %s", log_dir)

    # Open serial port
    ser = serial_open(args.test_port, args.test_baudrate, args.test_timeout)

    # Clear serial buffer
    ser.reset_input_buffer()

    return log_dir, ser


def _initialize_test_stats(groups_to_test):
    """
    Initialize test statistics and tracking.

    Args:
        groups_to_test: List of groups to test

    Returns:
        Tuple of (stats, total_start_time, total_to_test)
    """
    # Statistics
    stats: Dict[str, int] = {
        "passed": 0,
        "failed": 0,
        "timeout": 0,
        "hang": 0,
        "crash": 0,
    }

    # Total time tracking
    total_start_time = time.time()
    total_to_test = len(groups_to_test)

    return stats, total_start_time, total_to_test


def _execute_test_groups(exec_data: TestExecutionData):
    """Execute test groups and handle final summary"""
    try:
        for idx, group_path in enumerate(exec_data.group_info.groups_to_test, 1):
            index_info = TestIndexInfo(
                idx=idx,
                total_to_test=exec_data.group_info.total_to_test,
                total_groups=exec_data.group_info.total_groups,
                start_idx=exec_data.group_info.start_idx,
            )
            files = FileHandles(
                log_file=None,  # Will be created in _run_single_group_test
                csv_writer=exec_data.file_info.csv_writer,
                csv_file=exec_data.file_info.csv_file,
            )
            environment = TestEnvironment(
                log_dir=exec_data.log_dir,
                ser=exec_data.ser,
                args=exec_data.args,
                stats=exec_data.stats,
                files=files,
                total_start_time=exec_data.total_start_time,
            )
            config = TestConfig(
                index_info=index_info,
                group_path=group_path,
                environment=environment,
            )
            _run_single_group_test(config)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    finally:
        exec_data.ser.close()
        logger.info("Serial port closed.")

        files = FileHandles(
            log_file=None,
            csv_writer=exec_data.file_info.csv_writer,
            csv_file=exec_data.file_info.csv_file,
        )
        summary = FinalSummary(
            files=files,
            csv_filepath=exec_data.file_info.csv_filepath,
            stats=exec_data.stats,
            total_groups=exec_data.group_info.total_groups,
            skipped_groups=exec_data.group_info.start_idx,  # skipped_groups is same as start_idx
            total_to_test=exec_data.group_info.total_to_test,
            total_start_time=exec_data.total_start_time,
        )
        _write_final_summary(summary)


def _setup_test_execution_data(setup_data: TestSetupData):
    """Setup test execution data including CSV file and execution parameters"""
    csv_filepath = os.path.join(setup_data.environment_info.log_dir, "test_report.csv")
    with open(csv_filepath, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(
            ["Index", "Group Path", "Result", "Duration (s)", "Start Time", "End Time"]
        )
        logger.info("Writing test report to: %s", csv_filepath)

        group_info = TestGroupInfo(
            groups_to_test=setup_data.group_info.groups_to_test,
            total_groups=setup_data.group_info.total_groups,
            start_idx=setup_data.group_info.start_idx,
            total_to_test=setup_data.group_info.total_to_test,
        )
        file_info = FileHandlingInfo(
            csv_filepath=csv_filepath,
            csv_file=csv_file,
            csv_writer=csv_writer,
        )
        exec_data = TestExecutionData(
            group_info=group_info,
            log_dir=setup_data.environment_info.log_dir,
            ser=setup_data.environment_info.ser,
            args=setup_data.args,
            stats=setup_data.stats,
            total_start_time=setup_data.total_start_time,
            file_info=file_info,
        )
        _execute_test_groups(exec_data)


def run_group_tests(args) -> None:
    """
    Run tests by group

    Args:
        args: Parsed command line arguments
    """
    # Parse test groups
    result = _parse_test_groups(args)
    if result[0] is None:  # Start group not found
        return
    _, total_groups, start_idx, groups_to_test, _ = result

    # Setup test environment
    log_dir, ser = _setup_test_environment(args)

    # Initialize test statistics
    stats, total_start_time, total_to_test = _initialize_test_stats(groups_to_test)

    # Setup and execute tests
    group_info = TestGroupSetupInfo(
        groups_to_test=groups_to_test,
        total_groups=total_groups,
        start_idx=start_idx,
        total_to_test=total_to_test,
    )
    environment_info = TestEnvironmentSetupInfo(
        log_dir=log_dir,
        ser=ser,
    )
    setup_data = TestSetupData(
        args=args,
        group_info=group_info,
        environment_info=environment_info,
        stats=stats,
        total_start_time=total_start_time,
    )
    _setup_test_execution_data(setup_data)


def _run_single_group_test(config: TestConfig) -> None:
    """
    Run a single group test

    Args:
        config: TestConfig object containing all test configuration data
    """
    # Restart system make sure it is ready for test execution
    reset_device(
        config.environment.args.reset_port,
        config.environment.args.reset_baudrate,
        config.environment.args.reset_wait,
    )

    # Record case start time
    case_start_time = time.time()
    case_start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate actual index in full list
    actual_idx = config.index_info.start_idx + config.index_info.idx

    print_title_info(
        f"[{config.index_info.idx}/{config.index_info.total_to_test}] "
        f"(#{actual_idx}/{config.index_info.total_groups}) "
        f"Testing group: {config.group_path}"
    )

    # Create log file for this test group
    log_filename = config.group_path.replace(".", "_").replace("*", "all") + ".log"
    log_filepath = os.path.join(config.environment.log_dir, log_filename)
    with open(log_filepath, "w", encoding="utf-8") as log_file:
        logger.info("Writing log to: %s", log_filepath)

        # Write header to log file
        log_file.write(f"# Test Group: {config.group_path}\n")
        log_file.write(
            f"# Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        log_file.write(f"{'=' * 60}\n\n")

        # Build and send test command
        cmd = build_test_command(config.group_path)
        config.environment.ser.reset_input_buffer()
        serial_write(config.environment.ser, cmd)
        log_file.write(f"Command: {cmd}\n")

        # Wait for test result
        test_result = _wait_for_test_result(
            config.environment.ser,
            config.environment.args,
            log_file,
            config.group_path,
            config.environment.stats,
        )

        # Write test case report and get duration
        files = FileHandles(
            log_file=log_file,
            csv_writer=config.environment.files.csv_writer,
            csv_file=config.environment.files.csv_file,
        )
        report = TestCaseReport(
            files=files,
            actual_idx=actual_idx,
            group_path=config.group_path,
            test_result=test_result,
            case_start_time=case_start_time,
            case_start_datetime=case_start_datetime,
        )
        case_duration = _write_test_case_report(report)

    # Calculate total duration
    total_duration = time.time() - config.environment.total_start_time

    # Print progress
    stats = ProgressStats(
        passed=config.environment.stats["passed"],
        failed=config.environment.stats["failed"],
        timeout=config.environment.stats["timeout"],
        hang=config.environment.stats["hang"],
        crash=config.environment.stats["crash"],
    )
    progress = ProgressInfo(
        current=config.index_info.idx,
        total=config.index_info.total_to_test,
        stats=stats,
        case_duration=case_duration,
        total_duration=total_duration,
    )
    print_progress(progress)


def _write_final_summary(summary: FinalSummary) -> None:
    """
    Write final test summary to CSV and console

    Args:
        summary: FinalSummary object containing all summary data
    """
    # Calculate final total duration
    final_total_duration = time.time() - summary.total_start_time

    # Write summary to CSV
    summary.files.csv_writer.writerow([])
    summary.files.csv_writer.writerow(["# Summary"])
    summary.files.csv_writer.writerow(["Total Groups", summary.total_groups])
    summary.files.csv_writer.writerow(["Skipped", summary.skipped_groups])
    summary.files.csv_writer.writerow(["To Test", summary.total_to_test])

    completed = (
        summary.stats["passed"]
        + summary.stats["failed"]
        + summary.stats["timeout"]
        + summary.stats["hang"]
        + summary.stats["crash"]
    )

    summary.files.csv_writer.writerow(["Completed", completed])
    summary.files.csv_writer.writerow(["Passed", summary.stats["passed"]])
    summary.files.csv_writer.writerow(["Failed", summary.stats["failed"]])
    summary.files.csv_writer.writerow(["Timeout", summary.stats["timeout"]])
    summary.files.csv_writer.writerow(["Hang", summary.stats["hang"]])
    summary.files.csv_writer.writerow(["Crash", summary.stats["crash"]])

    pass_rate = 0.0
    if summary.total_to_test > 0:
        pass_rate = summary.stats["passed"] / summary.total_to_test * 100
        summary.files.csv_writer.writerow(["Pass Rate (%)", f"{pass_rate:.1f}"])

    summary.files.csv_writer.writerow(
        ["Total Time", format_duration(final_total_duration)]
    )

    avg_time = 0.0
    if completed > 0:
        avg_time = final_total_duration / completed
        summary.files.csv_writer.writerow(
            ["Avg Time per Group", format_duration(avg_time)]
        )

    summary.files.csv_file.flush()
    logger.info("Test report saved to: %s", summary.csv_filepath)

    # Print final summary
    print_title_info("|| FINAL TEST SUMMARY ||")

    # Content table data
    table_data = [
        ["📊 Total Groups", f"{summary.total_groups:,}", "", ""],
        ["  └─ Skipped", f"{summary.skipped_groups:,}", "", ""],
        ["  └─ To Test", f"{summary.total_to_test:,}", "", ""],
        ["✅ Completed", f"{completed:,}", "", ""],
        ["", "", "", ""],
        ["📈 Test Results", "Count", "Percentage", "Status"],
        [
            "✅ Passed",
            f"{summary.stats['passed']:,}",
            (
                f"{summary.stats['passed']/completed*100:.1f}%"
                if completed > 0
                else "0.0%"
            ),
            "🟢" if summary.stats["passed"] > 0 else "⚪",
        ],
        [
            "❌ Failed",
            f"{summary.stats['failed']:,}",
            (
                f"{summary.stats['failed']/completed*100:.1f}%"
                if completed > 0
                else "0.0%"
            ),
            "🔴" if summary.stats["failed"] > 0 else "⚪",
        ],
        [
            "⏱ Timeout",
            f"{summary.stats['timeout']:,}",
            (
                f"{summary.stats['timeout']/completed*100:.1f}%"
                if completed > 0
                else "0.0%"
            ),
            "🟡" if summary.stats["timeout"] > 0 else "⚪",
        ],
        [
            "💀 Hang",
            f"{summary.stats['hang']:,}",
            (
                f"{summary.stats['hang']/completed*100:.1f}%"
                if completed > 0
                else "0.0%"
            ),
            "🔴" if summary.stats["hang"] > 0 else "⚪",
        ],
        [
            "💥 Crash",
            f"{summary.stats['crash']:,}",
            (
                f"{summary.stats['crash']/completed*100:.1f}%"
                if completed > 0
                else "0.0%"
            ),
            "🔴" if summary.stats["crash"] > 0 else "⚪",
        ],
        ["", "", "", ""],
        ["⏱ Total Time", format_duration(final_total_duration), "", ""],
        [
            "📊 Avg Time",
            f"{format_duration(avg_time)}/group" if completed > 0 else "N/A",
            "",
            "",
        ],
        ["", "", "", ""],
        ["📄 Report File", summary.csv_filepath, "", ""],
    ]

    # Create the content table with grid format
    table = tabulate(table_data, tablefmt="grid", stralign="left")

    # Print the complete table (title and content are now integrated)
    for line in table.split("\n"):
        logger.info(line)
