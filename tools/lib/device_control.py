#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Control Module - Reset and system check functions
"""

import logging
import time

import serial

from .serial_utils import (
    serial_open,
    serial_write,
    serial_write_hex,
    serial_wait_for_response,
)
from .utils import print_title_info

logger = logging.getLogger(__name__)


def check_system_alive(
    ser: serial.Serial, timeout: float, log_file=None, print_output: bool = False
) -> bool:
    """
    Check if system is alive by sending 'free' command

    Args:
        ser: Serial port object
        timeout: Timeout in seconds
        log_file: File object to write serial data (optional)
        print_output: Whether to print received data to console (default: False)

    Returns:
        True if system responded, False otherwise
    """
    logger.info("Checking if system is alive with 'free' command...")
    serial_write(ser, "free\n")
    found, _, _, _ = serial_wait_for_response(
        ser, "total", timeout, log_file, print_output
    )
    return found


def reset_device(reset_port: str, reset_baudrate: int, reset_wait: float = 5) -> None:
    """
    Send restart command via reset serial port

    Args:
        reset_port: Serial port name for reset control
        reset_baudrate: Baud rate for reset port
        reset_wait: Wait time after reset in seconds, default 5
    """
    if not reset_port:
        logger.warning("No reset port specified, cannot reset device.")
        return

    print_title_info("Resetting device...")

    try:
        reset_ser = serial_open(reset_port, reset_baudrate)
        logger.info(
            "Reset port %s opened with baud rate %s", reset_port, reset_baudrate
        )

        # Send power on command: A0 01 01 A2
        power_on_cmd = bytes([0xA0, 0x01, 0x01, 0xA2])
        serial_write_hex(reset_ser, power_on_cmd)

        time.sleep(0.1)

        # Send power off command: A0 01 00 A1
        power_off_cmd = bytes([0xA0, 0x01, 0x00, 0xA1])
        serial_write_hex(reset_ser, power_off_cmd)

        reset_ser.close()
        logger.info("Reset command sent. Device should be restarting...")

        # Countdown display for waiting
        logger.info("Waiting for device to boot... (%ss)", reset_wait)
        remaining = int(reset_wait)
        while remaining > 0:
            print(f"\r  ⏳ Countdown: {remaining}s remaining...  ", end="", flush=True)
            time.sleep(1)
            remaining -= 1
        print("\r  ✅ Device boot wait complete.            ", flush=True)

    except serial.SerialException as e:
        logger.error("Error opening reset port: %s", e)
    except (OSError, IOError) as e:
        logger.exception("Reset error: %s", e)
