#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Control Module - Reset and system check functions
"""

import serial
import time
import logging

from .serial_utils import serial_open, serial_write, serial_write_hex, serial_wait_for_response
from .utils import print_title_info

logger = logging.getLogger(__name__)


def check_system_alive(ser: serial.Serial, timeout: float, log_file=None) -> bool:
    """
    Check if system is alive by sending 'free' command
    
    Args:
        ser: Serial port object
        timeout: Timeout in seconds
        log_file: File object to write serial data (optional)
        
    Returns:
        True if system responded, False otherwise
    """
    logger.info("Checking if system is alive with 'free' command...")
    serial_write(ser, "free\n")
    found, _, _ = serial_wait_for_response(ser, "total", timeout, log_file)
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
        
        # Countdown display for waiting
        logger.info(f"Waiting for device to boot... ({reset_wait}s)")
        remaining = int(reset_wait)
        while remaining > 0:
            print(f"\r  ⏳ Countdown: {remaining}s remaining...  ", end="", flush=True)
            time.sleep(1)
            remaining -= 1
        print(f"\r  ✅ Device boot wait complete.            ", flush=True)

    except serial.SerialException as e:
        logger.error(f"Error opening reset port: {e}")
    except Exception as e:
        logger.error(f"Reset error: {e}")
