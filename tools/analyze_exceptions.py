#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze EXCEPTION entries in test_report.csv and extract exception reasons from log files.
Creates a new CSV with exception reasons added.
"""

import os
import csv
import argparse
import re


def get_log_filename(group_path: str) -> str:
    """
    Convert group path to log filename.

    Args:
        group_path: Test group path (e.g., dEQP-GLES2.functional.clip_control)

    Returns:
        Log filename (e.g., dEQP-GLES2_functional_clip_control.log)
    """
    return group_path.replace(".", "_").replace("*", "all") + ".log"


def extract_exception_reason(log_filepath: str) -> str:
    """
    Extract exception reason from log file by finding 'libc++abi:' line.

    Args:
        log_filepath: Path to the log file

    Returns:
        Exception reason string, or empty string if not found
    """
    if not os.path.exists(log_filepath):
        return f"[Log file not found: {log_filepath}]"

    try:
        with open(log_filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "libc++abi:" in line:
                    # Extract the full line, strip whitespace
                    reason = line.strip()
                    return reason
    except Exception as e:
        return f"[Error reading log: {e}]"

    return "[libc++abi: not found in log]"


def analyze_exceptions(csv_filepath: str, output_filepath: str) -> None:
    """
    Analyze EXCEPTION entries and create new CSV with exception reasons.

    Args:
        csv_filepath: Path to input test_report.csv
        output_filepath: Path to output CSV file
    """
    log_dir = os.path.dirname(csv_filepath)

    # Read input CSV
    with open(csv_filepath, "r", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    if not rows:
        print("Error: Empty CSV file")
        return

    # Get header and add new column
    header = rows[0]
    header.append("Exception Reason")

    # Process data rows
    exception_count = 0
    for i, row in enumerate(rows[1:], start=1):
        if len(row) < 3:
            row.append("")
            continue

        result = row[2]  # Result column

        if result == "EXCEPTION":
            group_path = row[1]  # Group Path column
            log_filename = get_log_filename(group_path)
            log_filepath = os.path.join(log_dir, log_filename)

            reason = extract_exception_reason(log_filepath)
            row.append(reason)
            exception_count += 1
            print(f"[{i}] {group_path}: {reason[:80]}...")
        else:
            row.append("")

    # Write output CSV
    with open(output_filepath, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)

    print(f"\nAnalysis complete:")
    print(f"  Total EXCEPTION entries: {exception_count}")
    print(f"  Output saved to: {output_filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze EXCEPTION entries in test_report.csv and extract exception reasons"
    )
    parser.add_argument("csv_file", help="Path to test_report.csv")
    parser.add_argument(
        "-o",
        "--output",
        help="Output CSV file path (default: <input>_with_reasons.csv)",
    )

    args = parser.parse_args()

    csv_filepath = args.csv_file

    if not os.path.exists(csv_filepath):
        print(f"Error: CSV file not found: {csv_filepath}")
        return 1

    # Generate output path
    if args.output:
        output_filepath = args.output
    else:
        base, ext = os.path.splitext(csv_filepath)
        output_filepath = f"{base}_with_reasons{ext}"

    analyze_exceptions(csv_filepath, output_filepath)
    return 0


if __name__ == "__main__":
    exit(main())
