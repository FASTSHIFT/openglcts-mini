#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial Communication Utilities Module
"""

import collections.abc
import logging
import sys
import time
from typing import List, Optional, Tuple, Union

import serial

logger = logging.getLogger(__name__)


def serial_open(port: str, baudrate: int = 921600, timeout: float = 1) -> serial.Serial:
    """
    Open serial port

    Args:
        port: Serial port name (e.g., COM1, /dev/ttyUSB0)
        baudrate: Baud rate, default 921600
        timeout: Read timeout in seconds, default 1

    Returns:
        Opened serial port object
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        if not ser.isOpen():
            logger.error("Error opening serial port %s.", port)
            sys.exit(1)

        logger.info(
            "Serial port %s opened with baud rate %s and timeout %s seconds",
            port,
            baudrate,
            timeout,
        )
        return ser
    except serial.SerialException as e:
        logger.error("Error opening serial port: %s", e)
        sys.exit(1)
    except (OSError, IOError) as e:
        logger.exception("System error opening serial port: %s", e)
        sys.exit(1)


def serial_write(ser: serial.Serial, command: str, sleep_duration: float = 0) -> None:
    """
    Write string command to serial port

    Args:
        ser: Serial port object
        command: Command string to send
        sleep_duration: Delay after sending, default 0
    """
    try:
        logger.debug("Sending command: %s", command.strip())

        # Send the command to the serial port
        ser.write(command.encode())

        # Add a delay after writing to the serial port
        time.sleep(sleep_duration)

    except serial.SerialException as e:
        logger.error("Serial error: %s", e)

    except (OSError, IOError, UnicodeError) as e:
        logger.exception("System error writing to serial port: %s", e)
        sys.exit(1)


def serial_write_hex(ser: serial.Serial, hex_data: bytes) -> None:
    """
    Send hexadecimal data to serial port

    Args:
        ser: Serial port object
        hex_data: Bytes data to send
    """
    try:
        logger.debug("Sending hex data: %s", hex_data.hex().upper())
        ser.write(hex_data)
    except serial.SerialException as e:
        logger.error("Serial error: %s", e)
    except (OSError, IOError) as e:
        logger.exception("System error writing hex data to serial port: %s", e)
        sys.exit(1)


def serial_collect_until_idle(
    ser: serial.Serial,
    max_timeout: float,
    idle_timeout: float = 0.5,
) -> Tuple[bool, str]:
    """
    Collect serial data until no new data for idle_timeout seconds
    or max_timeout is reached.

    Args:
        ser: Serial port object
        max_timeout: Maximum total time to wait
        idle_timeout: Time with no data before considering transmission complete

    Returns:
        Tuple of (has_any_data, buffer)
    """
    start_time = time.time()
    last_data_time = start_time
    buffer = ""
    has_any_data = False
    poll_interval = 0.01  # 10ms polling interval

    while True:
        current_time = time.time()

        # Check max timeout
        if current_time - start_time >= max_timeout:
            break

        bytes_waiting = ser.in_waiting
        if bytes_waiting > 0:
            try:
                raw_data = ser.read(bytes_waiting)
                data = raw_data.decode("utf-8", errors="ignore")
                buffer += data
                has_any_data = True
                last_data_time = current_time
            except (OSError, IOError, UnicodeDecodeError) as e:
                logger.error("Read error: %s", e)
        else:
            time.sleep(poll_interval)

        # Check idle timeout (only after receiving some data)
        if has_any_data and (current_time - last_data_time >= idle_timeout):
            break

    return (has_any_data, buffer)


def scan_keywords(buffer: str, keywords: List[str]) -> Optional[str]:
    """
    Scan buffer for keywords (case-insensitive).

    Args:
        buffer: Data buffer to scan
        keywords: List of keywords to search for

    Returns:
        Matched keyword or None
    """
    buffer_lower = buffer.lower()
    for keyword in keywords:
        if keyword.lower() in buffer_lower:
            return keyword
    return None


def serial_wait_for_response(
    ser: serial.Serial,
    keyword: Union[str, List[str]],
    timeout: float,
    log_file=None,
    print_output: bool = False,
) -> Tuple[bool, bool, Optional[str], str]:
    """
    Wait for serial response, collect data until idle, then check for keywords.

    Data collection continues until:
    1. No new data received for idle_timeout seconds (transmission complete)
    2. Or max timeout is reached

    After collection, scan the buffer for keywords.

    Args:
        ser: Serial port object
        keyword: Single keyword string or list of keywords to match
        timeout: Maximum timeout in seconds
        log_file: File object to write serial data (optional)
        print_output: Whether to print received data to console
        idle_timeout: Time with no new data before considering transmission complete

    Returns:
        Tuple of (found, has_any_data, matched_keyword, buffer):
        - found: Whether keyword was found
        - has_any_data: Whether any data was received
        - matched_keyword: The matched keyword string or None
        - buffer: All collected serial data
    """
    # Normalize keywords
    if isinstance(keyword, str):
        keywords = [keyword]
    elif isinstance(keyword, collections.abc.Iterable):
        keywords = list(keyword)
    else:
        raise ValueError("keyword must be str or list of str")

    # Collect data until idle
    has_any_data, buffer = serial_collect_until_idle(ser, timeout)

    # Output to console and log file
    if buffer:
        if print_output:
            print(buffer, end="", flush=True)
        if log_file:
            log_file.write(buffer)
            log_file.flush()

    # Scan for keywords after data collection is complete
    matched = scan_keywords(buffer, keywords)

    return (matched is not None, has_any_data, matched, buffer)
