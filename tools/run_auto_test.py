#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional
import serial
import time
import logging

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


def serial_wait_for_response(ser, keyword: str, timeout: float) -> tuple:
    """
    Wait for serial port to return response containing specified keyword (or one of keyword array)
    keyword: str or List[str]
    Returns: (found: bool, has_any_data: bool)
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

    keywords = [k.lower() for k in keywords]

    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            try:
                data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                buffer += data
                has_any_data = True
                # Keep real-time display of serial data while logging
                print(data, end="", flush=True)
                logger.debug(f"Received data: {repr(data)}")

                for k in keywords:
                    if k in buffer.lower():
                        return (True, has_any_data)
            except Exception as e:
                logger.error(f"Read error: {e}")
        time.sleep(0.1)

    return (False, has_any_data)


def check_system_alive(ser, timeout: float) -> bool:
    """Check if system is alive, send free command and wait for response"""
    logger.info("Checking if system is alive with 'free' command...")
    serial_write(ser, "free\n")
    found, _ = serial_wait_for_response(ser, "total", timeout)
    return found


def print_title_info(str):
    logger.info(f"{'='*len(str)}")
    logger.info(str)
    logger.info(f"{'='*len(str)}")


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

    print_title_info(f"Total leaf groups to test: {total_groups}")

    # Open serial port
    ser = serial_open(args.test_port, args.test_baudrate, args.test_timeout)

    # Clear serial buffer
    ser.reset_input_buffer()

    reset_device(args.reset_port, args.reset_baudrate, args.reset_wait)

    try:
        for idx, group_path in enumerate(group_paths, 1):
            print_title_info(f"[{idx}/{total_groups}] Testing group: {group_path}")

            # Build and send test command
            cmd = build_test_command(group_path)
            ser.reset_input_buffer()  # Clear receive buffer
            serial_write(ser, cmd)

            # Wait for test completion with retry logic
            wait_count = 0
            test_completed = False

            while wait_count < args.max_wait_count:
                wait_count += 1
                logger.info(f"Waiting for test completion (attempt {wait_count}/{args.max_wait_count})...")

                # Wait for "DONE!" response
                found, has_any_data = serial_wait_for_response(ser, ["DONE!"], args.test_timeout)

                if found:
                    logger.info(f"Group {group_path} completed successfully.")
                    test_completed = True
                    break

                # Timeout, check if system is alive
                if has_any_data:
                    # Received some data, system is not hung, continue waiting
                    logger.info("Received data during wait, system is alive. Continuing to wait...")
                    continue
                else:
                    # No data received, send free command to check system
                    logger.warning(f"No data received within {args.test_timeout}s, checking system status...")
                    system_alive = check_system_alive(ser, args.test_timeout)
                    if system_alive:
                        logger.info("System is still alive (free responded). Continuing to wait...")
                        continue
                    else:
                        # System not responding, consider it hung
                        logger.error("System is not responding! Breaking wait loop.")
                        break

            if not test_completed:
                if wait_count >= args.max_wait_count:
                    logger.error(f"Group {group_path} exceeded max wait count ({args.max_wait_count}). Moving to next test.")
                else:
                    logger.error(f"Group {group_path} failed - system hung.")

            # Restart system regardless of success or failure
            reset_device(args.reset_port, args.reset_baudrate, args.reset_wait)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    finally:
        ser.close()
        logger.info("Serial port closed.")


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
