#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional
import serial
import time
import logging
import os
import csv
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Test case node"""

    name: str
    case_type: str
    full_path: str = ""
    children: List["TestCase"] = field(default_factory=list)

    def is_group(self) -> bool:
        """Check if it's a test group"""
        return self.case_type == "TestGroup"

    def is_executable(self) -> bool:
        """Check if it's an executable test case"""
        return self.case_type != "TestGroup"


class TestCaseParser:
    """dEQP test case XML parser"""

    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.package_name: str = ""
        self.root_cases: List[TestCase] = []
        self.total_groups: int = 0
        self.total_tests: int = 0

    def parse(self) -> None:
        """Parse XML file"""
        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        # Get package name
        self.package_name = root.get("PackageName", "")

        # Recursively parse all test cases
        for child in root:
            if child.tag == "TestCase":
                test_case = self._parse_test_case(child, self.package_name)
                self.root_cases.append(test_case)

    def _parse_test_case(self, element: ET.Element, parent_path: str) -> TestCase:
        """Recursively parse test case node"""
        name = element.get("Name", "")
        case_type = element.get("CaseType", "")
        full_path = f"{parent_path}.{name}" if parent_path else name

        test_case = TestCase(name=name, case_type=case_type, full_path=full_path)

        # Statistics
        if test_case.is_group():
            self.total_groups += 1
        else:
            self.total_tests += 1

        # Recursively parse child nodes
        for child in element:
            if child.tag == "TestCase":
                child_case = self._parse_test_case(child, full_path)
                test_case.children.append(child_case)

        return test_case

    def print_structure(self, max_depth: Optional[int] = None) -> None:
        """Print test case structure"""
        logger.info(f"Package: {self.package_name}")
        logger.info(f"Total Groups: {self.total_groups}")
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info("-" * 60)

        for case in self.root_cases:
            self._print_case(case, depth=0, max_depth=max_depth)

    def _print_case(self, case: TestCase, depth: int, max_depth: Optional[int]) -> None:
        """Recursively print test case"""
        if max_depth is not None and depth > max_depth:
            return

        indent = "  " * depth
        type_indicator = "[G]" if case.is_group() else "[T]"
        logger.info(f"{indent}{type_indicator} {case.name} ({case.case_type})")

        for child in case.children:
            self._print_case(child, depth + 1, max_depth)

    def get_all_test_paths(self) -> List[str]:
        """Get all executable test case full paths"""
        paths = []
        for case in self.root_cases:
            self._collect_test_paths(case, paths)
        return paths

    def _collect_test_paths(self, case: TestCase, paths: List[str]) -> None:
        """Recursively collect test paths"""
        if case.is_executable():
            paths.append(case.full_path)
        for child in case.children:
            self._collect_test_paths(child, paths)

    def get_group_paths(self) -> List[str]:
        """Get all test group full paths"""
        paths = []
        for case in self.root_cases:
            self._collect_group_paths(case, paths)
        return paths

    def _collect_group_paths(self, case: TestCase, paths: List[str]) -> None:
        """Recursively collect test group paths"""
        if case.is_group():
            paths.append(case.full_path)
        for child in case.children:
            self._collect_group_paths(child, paths)

    def get_leaf_group_paths(self) -> List[str]:
        """Get all leaf test group full paths (minimum test groups containing executable test cases)"""
        paths = []
        for case in self.root_cases:
            self._collect_leaf_group_paths(case, paths)
        return paths

    def _collect_leaf_group_paths(self, case: TestCase, paths: List[str]) -> None:
        """Recursively collect leaf test group paths"""
        if case.is_group():
            # Check if there are executable child test cases
            has_executable_children = any(
                child.is_executable() for child in case.children
            )
            if has_executable_children:
                paths.append(case.full_path)
        for child in case.children:
            self._collect_leaf_group_paths(child, paths)


def serial_open(port, baudrate=921600, timeout=1):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        if not ser.isOpen():
            logger.error(f"Error opening serial port {port}.")
            exit(1)

        logger.info(
            f"Serial port {port} opened with baud rate {baudrate} and timeout {timeout} seconds"
        )
        return ser
    except serial.SerialException as e:
        logger.error(f"Error opening serial port: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Other error: {e}")
        exit(1)


def serial_write(ser, command, sleep_duration=0):

    try:
        logger.debug(f"Sending command: {command.strip()}")

        # Send the command to the serial port
        ser.write(command.encode())

        # Add a delay after writing to the serial port
        time.sleep(sleep_duration)  # Adjust the sleep duration as needed

    except serial.SerialException as e:
        # Catch serial port exceptions and print the error message
        logger.error(f"Serial error: {e}")

    except Exception as e:
        # Catch other exceptions and print the error message
        logger.error(f"An error occurred: {e}")
        exit(1)


def serial_write_hex(ser, hex_data: bytes):
    """Send hexadecimal data to serial port"""
    try:
        logger.debug(f"Sending hex data: {hex_data.hex().upper()}")
        ser.write(hex_data)
    except serial.SerialException as e:
        logger.error(f"Serial error: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        exit(1)


def serial_wait_for_response(ser, keyword: str, timeout: float, log_file=None) -> tuple:
    """
    Wait for serial port to return response containing specified keyword (or one of keyword array)
    keyword: str or List[str]
    log_file: file object to write serial data (optional)
    Returns: (found: bool, has_any_data: bool, matched_keyword: str or None)
    """
    import collections.abc

    start_time = time.time()
    buffer = ""
    has_any_data = False

    # Support single string or string array
    if isinstance(keyword, str):
        keywords = [keyword]
    elif isinstance(keyword, collections.abc.Iterable):
        keywords = list(keyword)
    else:
        raise ValueError("keyword must be str or list of str")

    keywords_lower = [k.lower() for k in keywords]

    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            try:
                data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                buffer += data
                has_any_data = True
                # Keep real-time display of serial data while logging
                print(data, end="", flush=True)
                logger.debug(f"Received data: {repr(data)}")

                # Write to log file if provided
                if log_file:
                    log_file.write(data)
                    log_file.flush()

                for i, k in enumerate(keywords_lower):
                    if k in buffer.lower():
                        return (True, has_any_data, keywords[i])
            except Exception as e:
                logger.error(f"Read error: {e}")
        time.sleep(0.1)

    return (False, has_any_data, None)


def check_system_alive(ser, timeout: float, log_file=None) -> bool:
    """Check if system is alive, send free command and wait for response"""
    logger.info("Checking if system is alive with 'free' command...")
    serial_write(ser, "free\n")
    found, _, _ = serial_wait_for_response(ser, "total", timeout, log_file)
    return found


def print_title_info(str):
    logger.info(f"{'='*len(str)}")
    logger.info(str)
    logger.info(f"{'='*len(str)}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
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
):
    """Print test progress summary"""
    progress_pct = (current / total * 100) if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    logger.info(f"")
    logger.info(f"Progress: [{bar}] {current}/{total} ({progress_pct:.1f}%)")
    logger.info(
        f"Results:  ✅ Passed: {passed}  ❌ Failed: {failed}  ⏱ Timeout: {timeout}  💀 Hung: {hung}  💥 Crash: {crash}"
    )
    logger.info(
        f"Time:     ⏱ Case: {format_duration(case_duration)}  📊 Total: {format_duration(total_duration)}"
    )
    logger.info(f"")


def reset_device(reset_port: str, reset_baudrate: int, reset_wait: float = 5):
    if not reset_port:
        logger.warning("No reset port specified, cannot reset device.")
        return

    """Send restart command via reset serial port"""
    print_title_info("Resetting device...")

    try:
        reset_ser = serial_open(reset_port, reset_baudrate)
        logger.info(f"Reset port {reset_port} opened with baud rate {reset_baudrate}")

        # Send power on command: A0 01 01 A2
        power_on_cmd = bytes([0xA0, 0x01, 0x01, 0xA2])
        serial_write_hex(reset_ser, power_on_cmd)

        time.sleep(0.1)

        # Send power off command: A0 01 00 A1
        power_off_cmd = bytes([0xA0, 0x01, 0x00, 0xA1])
        serial_write_hex(reset_ser, power_off_cmd)

        reset_ser.close()
        logger.info("Reset command sent. Device should be restarting...")
        logger.info(f"Waiting for device to boot... ({reset_wait}s)")
        time.sleep(reset_wait)  # Wait for device to restart

    except serial.SerialException as e:
        logger.error(f"Error opening reset port: {e}")
    except Exception as e:
        logger.error(f"Reset error: {e}")


def build_test_command(group_path: str) -> str:
    """Build test command"""
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


def run_group_tests(args):
    """Run tests by group"""
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
                logger.info(f"Starting from group: {path} (index {i + 1}/{total_groups})")
                break
        if not found:
            logger.error(f"Start group '{args.start_group}' not found in test groups!")
            logger.info("Available groups containing the keyword:")
            matches = [p for p in group_paths if args.start_group.lower() in p.lower()]
            for m in matches[:10]:  # Show first 10 matches
                logger.info(f"  - {m}")
            if len(matches) > 10:
                logger.info(f"  ... and {len(matches) - 10} more")
            return

    # Slice groups to start from specified index
    groups_to_test = group_paths[start_idx:]
    skipped_groups = start_idx

    print_title_info(f"Total leaf groups to test: {len(groups_to_test)} (skipped: {skipped_groups})")

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
    stats = {"passed": 0, "failed": 0, "timeout": 0, "hung": 0, "crash": 0}

    # Total time tracking
    total_start_time = time.time()
    total_to_test = len(groups_to_test)

    # Create CSV report file
    csv_filepath = os.path.join(log_dir, "test_report.csv")
    csv_file = open(csv_filepath, "w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Index", "Group Path", "Result", "Duration (s)", "Start Time", "End Time"])
    logger.info(f"Writing test report to: {csv_filepath}")

    try:
        for idx, group_path in enumerate(groups_to_test, 1):
            # Record case start time
            case_start_time = time.time()
            case_start_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate actual index in full list
            actual_idx = start_idx + idx
            
            # Initialize result tracking
            test_result = "UNKNOWN"

            print_title_info(f"[{idx}/{total_to_test}] (#{actual_idx}/{total_groups}) Testing group: {group_path}")

            # Create log file for this test group
            log_filename = group_path.replace(".", "_").replace("*", "all") + ".log"
            log_filepath = os.path.join(log_dir, log_filename)
            log_file = open(log_filepath, "w", encoding="utf-8")
            logger.info(f"Writing log to: {log_filepath}")

            # Write header to log file
            log_file.write(f"# Test Group: {group_path}\n")
            log_file.write(
                f"# Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            log_file.write(f"{'='*60}\n\n")

            # Build and send test command
            cmd = build_test_command(group_path)
            ser.reset_input_buffer()  # Clear receive buffer
            serial_write(ser, cmd)
            log_file.write(f"Command: {cmd}\n")

            # Wait for test completion with retry logic
            wait_count = 0
            test_completed = False
            test_crashed = False

            while wait_count < args.max_wait_count:
                logger.info(
                    f"Waiting for test completion (free check count: {wait_count}/{args.max_wait_count})..."
                )

                # Wait for "DONE!" or "arm_memfault" response
                found, has_any_data, matched_keyword = serial_wait_for_response(
                    ser, ["DONE!", "arm_memfault"], args.test_timeout, log_file
                )

                if found:
                    if matched_keyword and "arm_memfault" in matched_keyword.lower():
                        # System crashed
                        logger.error(
                            f"Group {group_path} CRASHED (arm_memfault detected)!"
                        )
                        log_file.write(f"\n\n# Result: CRASH (arm_memfault)\n")
                        stats["crash"] += 1
                        test_crashed = True
                        test_result = "CRASH"
                    else:
                        logger.info(f"Group {group_path} completed successfully.")
                        log_file.write(f"\n\n# Result: PASSED\n")
                        stats["passed"] += 1
                        test_completed = True
                        test_result = "PASSED"
                    break

                # Timeout, check if system is alive
                if has_any_data:
                    # Received some data, system is not hung, continue waiting (no count increment)
                    logger.info(
                        "Received data during wait, system is alive. Continuing to wait..."
                    )
                    continue
                else:
                    # No data received, send free command to check system
                    wait_count += 1  # Only increment when doing free check
                    logger.warning(
                        f"No data received within {args.test_timeout}s, checking system status (attempt {wait_count}/{args.max_wait_count})..."
                    )
                    system_alive = check_system_alive(ser, args.test_timeout, log_file)
                    if system_alive:
                        logger.info(
                            "System is still alive (free responded). Continuing to wait..."
                        )
                        continue
                    else:
                        # System not responding, consider it hung
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

            # Calculate case duration
            case_end_time = time.time()
            case_end_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            case_duration = case_end_time - case_start_time
            total_duration = case_end_time - total_start_time

            # Write to CSV report
            csv_writer.writerow([
                actual_idx,
                group_path,
                test_result,
                f"{case_duration:.2f}",
                case_start_datetime,
                case_end_datetime
            ])
            csv_file.flush()  # Ensure data is written immediately

            # Write end time and duration to log file
            log_file.write(
                f"\n# End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            log_file.write(f"# Duration: {format_duration(case_duration)}\n")
            log_file.close()

            logger.info(f"Case duration: {format_duration(case_duration)}")

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

    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    finally:
        ser.close()
        logger.info("Serial port closed.")

        # Calculate final total duration
        final_total_duration = time.time() - total_start_time

        # Write summary to CSV
        csv_writer.writerow([])  # Empty row
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
        if total_to_test > 0:
            pass_rate = stats["passed"] / total_to_test * 100
            csv_writer.writerow(["Pass Rate (%)", f"{pass_rate:.1f}"])
        csv_writer.writerow(["Total Time (s)", f"{final_total_duration:.2f}"])
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
        logger.info(f"Total Groups:  {total_groups} (skipped: {skipped_groups}, to test: {total_to_test})")
        logger.info(f"Completed:     {completed}")
        logger.info(f"✅ Passed:     {stats['passed']}")
        logger.info(f"❌ Failed:     {stats['failed']}")
        logger.info(f"⏱ Timeout:    {stats['timeout']}")
        logger.info(f"💀 Hung:       {stats['hung']}")
        logger.info(f"💥 Crash:      {stats['crash']}")
        if total_to_test > 0:
            logger.info(f"Pass Rate:     {pass_rate:.1f}%")
        logger.info(f"")
        logger.info(f"⏱ Total Time: {format_duration(final_total_duration)}")
        if completed > 0:
            logger.info(f"📊 Avg Time:   {format_duration(avg_time)} per group")
        logger.info("=" * 60)
        logger.info(f"📄 Report:     {csv_filepath}")


def parse_xml_file(args):
    # Parse XML file
    test_parser = TestCaseParser(args.file)
    test_parser.parse()

    if args.list_tests:
        # List all test cases
        for path in test_parser.get_all_test_paths():
            logger.info(path)
    elif args.list_groups:
        # List all test groups
        for path in test_parser.get_group_paths():
            logger.info(path)
    elif args.summary:
        # Show summary only
        logger.info(f"Package: {test_parser.package_name}")
        logger.info(f"Total Groups: {test_parser.total_groups}")
        logger.info(f"Total Tests: {test_parser.total_tests}")
    else:
        # Print full structure
        test_parser.print_structure(max_depth=args.depth)


def main():
    parser = argparse.ArgumentParser(
        description="Parse dEQP test case XML file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f dEQP-GLES2-cases.xml
  %(prog)s -f dEQP-GLES2-cases.xml --depth 2
  %(prog)s -f dEQP-GLES2-cases.xml --list-tests
  %(prog)s -f dEQP-GLES2-cases.xml --list-groups
        """,
    )

    parser.add_argument("-f", "--file", required=True, help="XML test case file path")

    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=None,
        help="Maximum depth to display (default: show all)",
    )

    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all executable test case full paths",
    )

    parser.add_argument(
        "--list-groups", action="store_true", help="List all test group full paths"
    )

    parser.add_argument(
        "--test-port",
        default=None,
        help="COM serial port name, e.g., COM1 or /dev/ttyS0. Required when using --run-tests.",
    )
    parser.add_argument(
        "--test-baudrate",
        type=int,
        default=921600,
        help="Baud rate, default is 921600",
    )
    parser.add_argument(
        "--test-timeout",
        type=float,
        default=10,
        help="Timeout (seconds), default is 10 second",
    )

    parser.add_argument(
        "--reset-port",
        default=None,
        help="Serial port for device reset, e.g., COM2 or /dev/ttyUSB1.",
    )

    parser.add_argument(
        "--reset-baudrate",
        type=int,
        default=9600,
        help="Baud rate for reset port, default is 9600",
    )

    parser.add_argument(
        "--reset-wait",
        type=float,
        default=5,
        help="Wait time (seconds) after reset, default is 5 seconds",
    )

    parser.add_argument(
        "--max-wait-count",
        type=int,
        default=10,
        help="Maximum wait attempts before timeout, default is 10",
    )

    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory to store test log files. If not specified, a timestamped directory will be created.",
    )

    parser.add_argument(
        "--start-group",
        default=None,
        help="Start testing from the specified group (skip groups before this one). Can be a full group path or a partial match.",
    )

    parser.add_argument(
        "--summary", action="store_true", help="Show summary information only"
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests by group (send commands via serial port)",
    )

    args = parser.parse_args()

    if args.run_tests:
        if not args.test_port:
            parser.error("--test-port is required when using --run-tests")
        run_group_tests(args)
    else:
        parse_xml_file(args)


if __name__ == "__main__":
    main()
