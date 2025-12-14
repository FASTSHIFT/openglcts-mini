#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dEQP Test Case XML Parser Module
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional
import logging

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
        logger.info("Package: %s", self.package_name)
        logger.info("Total Groups: %s", self.total_groups)
        logger.info("Total Tests: %s", self.total_tests)
        logger.info("-" * 60)

        for case in self.root_cases:
            self._print_case(case, depth=0, max_depth=max_depth)

    def _print_case(self, case: TestCase, depth: int, max_depth: Optional[int]) -> None:
        """Recursively print test case"""
        if max_depth is not None and depth > max_depth:
            return

        indent = "  " * depth
        type_indicator = "[G]" if case.is_group() else "[T]"
        logger.info("%s%s %s (%s)", indent, type_indicator, case.name, case.case_type)

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
        """Get all leaf test group full paths
        (minimum test groups containing executable test cases)"""
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
