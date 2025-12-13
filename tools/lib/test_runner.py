#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Runner Module - Main test execution logic
"""

import os
import csv
import time
import logging
from datetime import datetime
from typing import Dict, List

from .test_parser import TestCaseParser
from .serial_utils import (
    serial_open,
    serial_write,
    serial_wait_for_response,
    collect_crash_log,
)
from .device_control import check_system_alive, reset_device
from .utils import format_duration, print_title_info, print_progress

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


def _handle_crash(ser, log_file, print_output: bool) -> None:
    """
    Collect crash log after PANIC detected.

    Args:
        ser: Serial port object
        log_file: Log file object
        print_output: Whether to print output to console
    """
    log_file.write("\n# --- Begin Crash Log ---\n")
    collect_crash_log(ser, log_file, print_output, idle_timeout=2.0, max_total=10.0)
    log_file.write("\n# --- End Crash Log ---\n")


def _wait_for_test_result(
    ser,
    args,
    log_file,
    group_path: str,
    stats: Dict[str, int],
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
        Test result string: "PASSED", "CRASH", "HUNG", or "TIMEOUT"
    """
    print_output = getattr(args, "print_output", False)
    wait_count = 0
    test_completed = False
    test_crashed = False
    test_result = "UNKNOWN"

    # Accumulated buffer for checking fail patterns
    accumulated_buffer = ""

    while wait_count < args.max_wait_count:
        logger.info(
            f"Waiting for test completion (free check count: {wait_count}/{args.max_wait_count})..."
        )

        found, has_any_data, matched_keyword, buffer = serial_wait_for_response(
            ser, ["DONE!", "PANIC"], args.test_timeout, log_file, print_output
        )

        # Accumulate buffer data for fail pattern checking
        accumulated_buffer += buffer

        if found:
            if matched_keyword and "panic" in matched_keyword.lower():
                logger.error(f"Group {group_path} CRASHED (PANIC detected)!")
                log_file.write(f"\n\n# Result: CRASH (PANIC)\n")
                _handle_crash(ser, log_file, print_output)
                stats["crash"] += 1
                test_crashed = True
                test_result = "CRASH"
            else:
                # Check if there are any "Fail (" patterns in the accumulated buffer
                if "Fail (" in accumulated_buffer:
                    logger.warning(
                        f"Group {group_path} completed with FAILURES detected."
                    )
                    log_file.write(f"\n\n# Result: FAILED (Fail pattern detected)\n")
                    stats["failed"] += 1
                    test_completed = True
                    test_result = "FAILED"
                else:
                    logger.info(f"Group {group_path} completed successfully.")
                    log_file.write(f"\n\n# Result: PASSED\n")
                    stats["passed"] += 1
                    test_completed = True
                    test_result = "PASSED"
            break

        if has_any_data:
            logger.info(
                "Received data during wait, system is alive. Continuing to wait..."
            )
            continue
        else:
            wait_count += 1
            logger.warning(
                f"No data received within {args.test_timeout}s, checking system status (attempt {wait_count}/{args.max_wait_count})..."
            )
            system_alive = check_system_alive(
                ser, args.test_timeout, log_file, print_output
            )
            if system_alive:
                logger.info(
                    "System is still alive (free responded). Continuing to wait..."
                )
                continue
            else:
                logger.error("System is not responding! Breaking wait loop.")
                log_file.write(f"\n\n# Result: SYSTEM HUNG\n")
                stats["hung"] += 1
                test_result = "HUNG"
                break

    if not test_completed and not test_crashed:
        if wait_count >= args.max_wait_count:
            logger.error(
                f"Group {group_path} exceeded max wait count ({args.max_wait_count}). Moving to next test."
            )
            log_file.write(f"\n\n# Result: TIMEOUT (exceeded max wait count)\n")
            stats["timeout"] += 1
            test_result = "TIMEOUT"

    return test_result


def _write_test_case_report(
    log_file,
    csv_writer,
    csv_file,
    actual_idx: int,
    group_path: str,
    test_result: str,
    case_start_time: float,
    case_start_datetime: str,
) -> float:
    """
    Write test case report to log and CSV.

    Args:
        log_file: Log file object
        csv_writer: CSV writer object
        csv_file: CSV file object
        actual_idx: Actual index in full list
        group_path: Test group path
        test_result: Test result string
        case_start_time: Case start timestamp
        case_start_datetime: Case start datetime string

    Returns:
        Case duration in seconds
    """
    case_end_time = time.time()
    case_end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    case_duration = case_end_time - case_start_time

    csv_writer.writerow(
        [
            actual_idx,
            group_path,
            test_result,
            f"{case_duration:.2f}",
            case_start_datetime,
            case_end_datetime,
        ]
    )
    csv_file.flush()

    log_file.write(f"\n# End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"# Duration: {format_duration(case_duration)}\n")
    log_file.close()

    logger.info(f"Case duration: {format_duration(case_duration)}")
    return case_duration


def run_group_tests(args) -> None:
    """
    Run tests by group

    Args:
        args: Parsed command line arguments
    """
    # Parse XML file
    test_parser = TestCaseParser(args.file)
    test_parser.parse()

    # Get leaf test groups
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
                    f"Starting from group: {path} (index {i + 1}/{total_groups})"
                )
                break
        if not found:
            logger.error(f"Start group '{args.start_group}' not found in test groups!")
            logger.info("Available groups containing the keyword:")
            matches = [p for p in group_paths if args.start_group.lower() in p.lower()]
            for m in matches[:10]:
                logger.info(f"  - {m}")
            if len(matches) > 10:
                logger.info(f"  ... and {len(matches) - 10} more")
            return

    # Slice groups to start from specified index
    groups_to_test = group_paths[start_idx:]
    skipped_groups = start_idx

    print_title_info(
        f"Total leaf groups to test: {len(groups_to_test)} (skipped: {skipped_groups})"
    )

    # Create log directory
    if args.log_dir:
        log_dir = args.log_dir
    else:
        log_dir = datetime.now().strftime("logs_%Y%m%d_%H%M%S")

    os.makedirs(log_dir, exist_ok=True)
    logger.info(f"Log directory: {log_dir}")

    # Open serial port
    ser = serial_open(args.test_port, args.test_baudrate, args.test_timeout)

    # Clear serial buffer
    ser.reset_input_buffer()

    reset_device(args.reset_port, args.reset_baudrate, args.reset_wait)

    # Statistics
    stats: Dict[str, int] = {
        "passed": 0,
        "failed": 0,
        "timeout": 0,
        "hung": 0,
        "crash": 0,
    }

    # Total time tracking
    total_start_time = time.time()
    total_to_test = len(groups_to_test)

    # Create CSV report file
    csv_filepath = os.path.join(log_dir, "test_report.csv")
    csv_file = open(csv_filepath, "w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(
        ["Index", "Group Path", "Result", "Duration (s)", "Start Time", "End Time"]
    )
    logger.info(f"Writing test report to: {csv_filepath}")

    try:
        for idx, group_path in enumerate(groups_to_test, 1):
            _run_single_group_test(
                idx=idx,
                group_path=group_path,
                total_to_test=total_to_test,
                total_groups=total_groups,
                start_idx=start_idx,
                log_dir=log_dir,
                ser=ser,
                args=args,
                stats=stats,
                csv_writer=csv_writer,
                csv_file=csv_file,
                total_start_time=total_start_time,
            )

    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    finally:
        ser.close()
        logger.info("Serial port closed.")

        _write_final_summary(
            csv_writer=csv_writer,
            csv_file=csv_file,
            csv_filepath=csv_filepath,
            stats=stats,
            total_groups=total_groups,
            skipped_groups=skipped_groups,
            total_to_test=total_to_test,
            total_start_time=total_start_time,
        )


def _run_single_group_test(
    idx: int,
    group_path: str,
    total_to_test: int,
    total_groups: int,
    start_idx: int,
    log_dir: str,
    ser,
    args,
    stats: Dict[str, int],
    csv_writer,
    csv_file,
    total_start_time: float,
) -> None:
    """
    Run a single group test
    """
    # Record case start time
    case_start_time = time.time()
    case_start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate actual index in full list
    actual_idx = start_idx + idx

    print_title_info(
        f"[{idx}/{total_to_test}] (#{actual_idx}/{total_groups}) Testing group: {group_path}"
    )

    # Create log file for this test group
    log_filename = group_path.replace(".", "_").replace("*", "all") + ".log"
    log_filepath = os.path.join(log_dir, log_filename)
    log_file = open(log_filepath, "w", encoding="utf-8")
    logger.info(f"Writing log to: {log_filepath}")

    # Write header to log file
    log_file.write(f"# Test Group: {group_path}\n")
    log_file.write(f"# Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"{'=' * 60}\n\n")

    # Build and send test command
    cmd = build_test_command(group_path)
    ser.reset_input_buffer()
    serial_write(ser, cmd)
    log_file.write(f"Command: {cmd}\n")

    # Wait for test result
    test_result = _wait_for_test_result(ser, args, log_file, group_path, stats)

    # Write test case report and get duration
    case_duration = _write_test_case_report(
        log_file,
        csv_writer,
        csv_file,
        actual_idx,
        group_path,
        test_result,
        case_start_time,
        case_start_datetime,
    )

    # Calculate total duration
    total_duration = time.time() - total_start_time

    # Print progress
    print_progress(
        idx,
        total_to_test,
        stats["passed"],
        stats["failed"],
        stats["timeout"],
        stats["hung"],
        stats["crash"],
        case_duration,
        total_duration,
    )

    # Restart system regardless of success or failure
    reset_device(args.reset_port, args.reset_baudrate, args.reset_wait)


def _write_final_summary(
    csv_writer,
    csv_file,
    csv_filepath: str,
    stats: Dict[str, int],
    total_groups: int,
    skipped_groups: int,
    total_to_test: int,
    total_start_time: float,
) -> None:
    """
    Write final test summary to CSV and console
    """
    # Calculate final total duration
    final_total_duration = time.time() - total_start_time

    # Write summary to CSV
    csv_writer.writerow([])
    csv_writer.writerow(["# Summary"])
    csv_writer.writerow(["Total Groups", total_groups])
    csv_writer.writerow(["Skipped", skipped_groups])
    csv_writer.writerow(["To Test", total_to_test])

    completed = (
        stats["passed"]
        + stats["failed"]
        + stats["timeout"]
        + stats["hung"]
        + stats["crash"]
    )

    csv_writer.writerow(["Completed", completed])
    csv_writer.writerow(["Passed", stats["passed"]])
    csv_writer.writerow(["Failed", stats["failed"]])
    csv_writer.writerow(["Timeout", stats["timeout"]])
    csv_writer.writerow(["Hung", stats["hung"]])
    csv_writer.writerow(["Crash", stats["crash"]])

    pass_rate = 0.0
    if total_to_test > 0:
        pass_rate = stats["passed"] / total_to_test * 100
        csv_writer.writerow(["Pass Rate (%)", f"{pass_rate:.1f}"])

    csv_writer.writerow(["Total Time (s)", f"{final_total_duration:.2f}"])

    avg_time = 0.0
    if completed > 0:
        avg_time = final_total_duration / completed
        csv_writer.writerow(["Avg Time per Group (s)", f"{avg_time:.2f}"])

    csv_file.close()
    logger.info(f"Test report saved to: {csv_filepath}")

    # Print final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("FINAL TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(
        f"Total Groups:  {total_groups} (skipped: {skipped_groups}, to test: {total_to_test})"
    )
    logger.info(f"Completed:     {completed}")
    logger.info(f"✅ Passed:     {stats['passed']}")
    logger.info(f"❌ Failed:     {stats['failed']}")
    logger.info(f"⏱ Timeout:    {stats['timeout']}")
    logger.info(f"💀 Hung:       {stats['hung']}")
    logger.info(f"💥 Crash:      {stats['crash']}")
    if total_to_test > 0:
        logger.info(f"Pass Rate:     {pass_rate:.1f}%")
    logger.info("")
    logger.info(f"⏱ Total Time: {format_duration(final_total_duration)}")
    if completed > 0:
        logger.info(f"📊 Avg Time:   {format_duration(avg_time)} per group")
    logger.info("=" * 60)
    logger.info(f"📄 Report:     {csv_filepath}")
