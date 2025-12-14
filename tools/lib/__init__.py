"""dEQP Auto Test Library"""

from .test_parser import TestCase, TestCaseParser
from .serial_utils import (
    serial_open,
    serial_write,
    serial_write_hex,
    serial_wait_for_response,
)
from .device_control import check_system_alive, reset_device
from .utils import format_duration, print_title_info, print_progress, setup_logger
from .test_runner import run_group_tests, build_test_command

__all__ = [
    "TestCase",
    "TestCaseParser",
    "serial_open",
    "serial_write",
    "serial_write_hex",
    "serial_wait_for_response",
    "check_system_alive",
    "reset_device",
    "format_duration",
    "print_title_info",
    "print_progress",
    "setup_logger",
    "run_group_tests",
    "build_test_command",
]
