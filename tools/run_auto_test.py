#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dEQP Auto Test Tool

Parse dEQP test case XML file and run tests via serial port.
"""

import argparse
import logging

from lib.test_parser import TestCaseParser
from lib.test_runner import run_group_tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_xml_file(args) -> None:
    """Parse and display XML file content"""
    test_parser = TestCaseParser(args.file)
    test_parser.parse()

    if args.list_tests:
        for path in test_parser.get_all_test_paths():
            logger.info(path)
    elif args.list_groups:
        for path in test_parser.get_group_paths():
            logger.info(path)
    elif args.summary:
        logger.info(f"Package: {test_parser.package_name}")
        logger.info(f"Total Groups: {test_parser.total_groups}")
        logger.info(f"Total Tests: {test_parser.total_tests}")
    else:
        test_parser.print_structure(max_depth=args.depth)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="Parse dEQP test case XML file and run tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f dEQP-GLES2-cases.xml
  %(prog)s -f dEQP-GLES2-cases.xml --depth 2
  %(prog)s -f dEQP-GLES2-cases.xml --list-tests
  %(prog)s -f dEQP-GLES2-cases.xml --list-groups
  %(prog)s -f dEQP-GLES2-cases.xml --run-tests --test-port /dev/ttyUSB1
  %(prog)s -f dEQP-GLES2-cases.xml --run-tests --test-port /dev/ttyUSB1 --reset-port /dev/ttyUSB2
  %(prog)s -f dEQP-GLES2-cases.xml --run-tests --test-port /dev/ttyUSB1 --start-group shaders
        """,
    )

    # Input file
    parser.add_argument("-f", "--file", required=True, help="XML test case file path")

    # Display options
    parser.add_argument(
        "-d", "--depth", type=int, default=None,
        help="Maximum depth to display (default: show all)"
    )
    parser.add_argument(
        "--list-tests", action="store_true",
        help="List all executable test case full paths"
    )
    parser.add_argument(
        "--list-groups", action="store_true",
        help="List all test group full paths"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show summary information only"
    )

    # Test execution options
    parser.add_argument(
        "--run-tests", action="store_true",
        help="Run tests by group (send commands via serial port)"
    )
    parser.add_argument(
        "--test-port", default=None,
        help="Serial port for test commands (e.g., /dev/ttyUSB0). Required with --run-tests"
    )
    parser.add_argument(
        "--test-baudrate", type=int, default=921600,
        help="Baud rate for test port (default: 921600)"
    )
    parser.add_argument(
        "--test-timeout", type=float, default=10,
        help="Timeout in seconds for test response (default: 10)"
    )

    # Reset options
    parser.add_argument(
        "--reset-port", default=None,
        help="Serial port for device reset (e.g., /dev/ttyUSB1)"
    )
    parser.add_argument(
        "--reset-baudrate", type=int, default=9600,
        help="Baud rate for reset port (default: 9600)"
    )
    parser.add_argument(
        "--reset-wait", type=float, default=5,
        help="Wait time after reset in seconds (default: 5)"
    )

    # Test control options
    parser.add_argument(
        "--max-wait-count", type=int, default=10,
        help="Maximum wait attempts before timeout (default: 10)"
    )
    parser.add_argument(
        "--log-dir", default=None,
        help="Directory for test logs. Auto-created with timestamp if not specified"
    )
    parser.add_argument(
        "--start-group", default=None,
        help="Start testing from specified group (skip earlier groups)"
    )

    return parser


def main() -> None:
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.run_tests:
        if not args.test_port:
            parser.error("--test-port is required when using --run-tests")
        run_group_tests(args)
    else:
        parse_xml_file(args)


if __name__ == "__main__":
    main()
