#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial Communication Utilities Module
"""

import serial
import time
import collections.abc
import logging
from typing import List, Optional, Tuple, Union

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


def serial_write(ser: serial.Serial, command: str, sleep_duration: float = 0) -> None:
    """
    Write string command to serial port

    Args:
        ser: Serial port object
        command: Command string to send
        sleep_duration: Delay after sending, default 0
    """
    try:
        logger.debug(f"Sending command: {command.strip()}")

        # Send the command to the serial port
        ser.write(command.encode())

        # Add a delay after writing to the serial port
        time.sleep(sleep_duration)

    except serial.SerialException as e:
        logger.error(f"Serial error: {e}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        exit(1)


def serial_write_hex(ser: serial.Serial, hex_data: bytes) -> None:
    """
    Send hexadecimal data to serial port

    Args:
        ser: Serial port object
        hex_data: Bytes data to send
    """
    try:
        logger.debug(f"Sending hex data: {hex_data.hex().upper()}")
        ser.write(hex_data)
    except serial.SerialException as e:
        logger.error(f"Serial error: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        exit(1)


def serial_wait_for_response(
    ser: serial.Serial,
    keyword: Union[str, List[str]],
    timeout: float,
    log_file=None,
    print_output: bool = False,
) -> Tuple[bool, bool, Optional[str]]:
    """
    Wait for serial port to return response containing specified keyword

    Args:
        ser: Serial port object
        keyword: Single keyword string or list of keywords to match
        timeout: Timeout in seconds
        log_file: File object to write serial data (optional)
        print_output: Whether to print received data to console (default: False)

    Returns:
        Tuple of (found, has_any_data, matched_keyword):
        - found: Whether keyword was found
        - has_any_data: Whether any data was received
        - matched_keyword: The matched keyword string or None
    """
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
                # Print serial data to console if enabled
                if print_output:
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


def collect_crash_log(
    ser: serial.Serial,
    log_file=None,
    print_output: bool = False,
    idle_timeout: float = 2.0,
    max_total: float = 10.0,
) -> str:
    """
    Keep collecting serial log until no new data for idle_timeout seconds or
    total time exceeds max_total seconds.

    Args:
        ser: Serial port object
        log_file: File object to write serial data (optional)
        print_output: Whether to print received data to console (default: False)
        idle_timeout: Seconds to wait with no new data before stopping
        max_total: Maximum total seconds to collect

    Returns:
        Collected log string
    """
    start_time = time.time()
    last_data_time = time.time()
    buffer = ""
    while True:
        if ser.in_waiting > 0:
            try:
                data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                buffer += data
                last_data_time = time.time()
                if print_output:
                    print(data, end="", flush=True)
                if log_file:
                    log_file.write(data)
                    log_file.flush()
            except Exception as e:
                logger.error(f"Read error during crash log: {e}")
        else:
            time.sleep(0.1)
        if time.time() - last_data_time > idle_timeout:
            break
        if time.time() - start_time > max_total:
            logger.warning(
                f"Crash log collection reached max_total={max_total}s, force stop."
            )
            break
    return buffer
