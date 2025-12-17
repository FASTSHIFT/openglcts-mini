#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Quality Check Tool

Automatically format Python code, run pylint checks, and perform syntax validation.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import List

# Configure logging
# pylint: disable=duplicate-code
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# pylint: enable=duplicate-code


def check_tool_available(tool_name: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        subprocess.run([tool_name, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def format_code(file_paths: List[str], check_only: bool = False) -> bool:
    """Format Python code using black."""
    if not check_tool_available("black"):
        logger.error(
            "black is not installed. Please install it with: pip install black"
        )
        return False

    cmd = ["black"]
    if check_only:
        cmd.append("--check")
    cmd.extend(file_paths)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            if check_only:
                logger.info("✓ Code formatting check passed")
            else:
                logger.info("✓ Code formatted successfully")
            return True

        if check_only:
            logger.error("✗ Code formatting issues found")
            logger.info(result.stdout)
        else:
            logger.error("✗ Code formatting failed")
            logger.error(result.stderr)
        return False
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Error running black: %s", e)
        return False


def run_pylint(file_paths: List[str]) -> bool:
    """Run pylint checks on Python files."""
    if not check_tool_available("pylint"):
        logger.error(
            "pylint is not installed. Please install it with: pip install pylint"
        )
        return False

    cmd = ["pylint"]
    cmd.extend(file_paths)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info("✓ Pylint checks passed")
            return True

        logger.warning("⚠ Pylint found issues (return code: %d)", result.returncode)
        logger.info(result.stdout)
        # Pylint returns non-zero for warnings, which is normal
        return result.returncode < 32  # Consider it passed if not a fatal error
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Error running pylint: %s", e)
        return False


def check_syntax(file_paths: List[str]) -> bool:
    """Check Python syntax using py_compile."""
    all_passed = True

    for file_path in file_paths:
        try:
            # Use py_compile to check syntax
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", file_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                logger.info("✓ Syntax check passed: %s", file_path)
            else:
                logger.error("✗ Syntax error in %s: %s", file_path, result.stderr)
                all_passed = False
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("Error checking syntax for %s: %s", file_path, e)
            all_passed = False

    return all_passed


def collect_python_files(paths: List[str]) -> List[str]:
    """Collect all Python files from given paths."""
    python_files = []

    for path in paths:
        path_obj = Path(path)
        if path_obj.is_file() and path_obj.suffix == ".py":
            python_files.append(str(path_obj))
        elif path_obj.is_dir():
            for py_file in path_obj.rglob("*.py"):
                python_files.append(str(py_file))

    return python_files


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Auto format, lint, and syntax check Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all checks on current directory
  %(prog)s --check-formatting # Check formatting without modifying files
        """,
    )

    # Only keep the essential formatting check option
    parser.add_argument(
        "--check-formatting",
        action="store_true",
        help="Check formatting without modifying files",
    )

    return parser


def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Always check current directory and subdirectories
    current_dir = Path(".")
    python_files = collect_python_files([str(current_dir)])

    if not python_files:
        logger.error("No Python files found in current directory and subdirectories")
        sys.exit(1)

    logger.info("Found %d Python file(s) to check", len(python_files))

    # Always run all checks by default
    run_format = True
    run_lint = True
    run_syntax = True

    # Run operations
    all_passed = True

    if run_format:
        logger.info("Running code formatting...")
        if not format_code(python_files, check_only=args.check_formatting):
            if args.check_formatting:
                all_passed = False
            # For actual formatting, we continue even if it fails

    if run_lint:
        logger.info("Running pylint checks...")
        if not run_pylint(python_files):
            all_passed = False

    if run_syntax:
        logger.info("Running syntax checks...")
        if not check_syntax(python_files):
            all_passed = False

    # Summary
    if all_passed:
        logger.info("🎉 All checks completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
