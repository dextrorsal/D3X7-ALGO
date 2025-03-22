#!/usr/bin/env python3
"""
D3X7-ALGO Test Runner

This script provides a convenient way to run all tests or specific test suites
with proper configuration and nice output formatting.

Usage:
    ./run_tests.py [OPTIONS]

Options:
    --unit           Run only unit tests
    --integration    Run only integration tests
    --devnet        Run only devnet tests
    --mainnet       Run only mainnet tests
    --coverage      Generate coverage report
    --verbose       Show detailed test output
    --noanchor      Skip anchor-related tests
"""

import os
import sys
import time
import argparse
import pytest
import asyncio
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

class TestRunner:
    def __init__(self):
        self.test_dir = Path(__file__).parent / "tests"
        self.results: Dict[str, Dict] = {}
        
    def _print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}= {text}{' '*(77-len(text))}={Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

    def _print_result(self, name: str, passed: int, failed: int, duration: float):
        """Print test results with color coding."""
        status = f"{Fore.GREEN}PASSED{Style.RESET_ALL}" if failed == 0 else f"{Fore.RED}FAILED{Style.RESET_ALL}"
        print(f"{name:.<40} {status} ({passed} passed, {failed} failed) in {duration:.2f}s")

    def run_test_suite(self, path: str, name: str, args: List[str]) -> Dict:
        """Run a specific test suite and return results."""
        start_time = time.time()
        
        # Add coverage args if requested
        if "--coverage" in args:
            args.extend(["--cov=src/trading", "--cov-report=term-missing"])
            
        # Add noanchor flag if requested
        if "--noanchor" in args:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "true"
            args.remove("--noanchor")  # Remove it since pytest doesn't recognize it
        
        # Run pytest with provided arguments
        result = pytest.main([str(path)] + args)
        
        duration = time.time() - start_time
        passed = 0 if result != 0 else 1  # Simplified for now
        failed = 1 if result != 0 else 0
        
        return {
            "passed": passed,
            "failed": failed,
            "duration": duration
        }

    def run_tests(self, args: argparse.Namespace):
        """Run all specified test suites."""
        pytest_args = ["--no-header"]  # Base pytest arguments
        if args.verbose:
            pytest_args.append("-v")
        if args.noanchor:
            pytest_args.append("--noanchor")
        
        self._print_header("D3X7-ALGO Test Suite")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Determine which tests to run
        if not any([args.unit, args.integration, args.devnet, args.mainnet]):
            # Run all tests if no specific suite is selected
            args.unit = args.integration = True

        # Run Unit Tests
        if args.unit:
            self._print_header("Running Unit Tests")
            unit_path = self.test_dir / "unit"
            self.results["unit"] = self.run_test_suite(unit_path, "Unit Tests", pytest_args)

        # Run Integration Tests
        if args.integration:
            if args.devnet or not args.mainnet:
                self._print_header("Running Devnet Integration Tests")
                devnet_path = self.test_dir / "integration/devnet"
                self.results["devnet"] = self.run_test_suite(devnet_path, "Devnet Tests", pytest_args)

            if args.mainnet or not args.devnet:
                self._print_header("Running Mainnet Integration Tests")
                mainnet_path = self.test_dir / "integration/mainnet"
                self.results["mainnet"] = self.run_test_suite(mainnet_path, "Mainnet Tests", pytest_args)

        # Print Summary
        self._print_header("Test Summary")
        total_passed = total_failed = 0
        total_duration = 0.0

        for name, result in self.results.items():
            self._print_result(
                name,
                result["passed"],
                result["failed"],
                result["duration"]
            )
            total_passed += result["passed"]
            total_failed += result["failed"]
            total_duration += result["duration"]

        print(f"\nTotal: {total_passed + total_failed} tests")
        print(f"Time taken: {total_duration:.2f} seconds")
        
        if total_failed > 0:
            print(f"\n{Fore.RED}❌ Some tests failed!{Style.RESET_ALL}")
            sys.exit(1)
        else:
            print(f"\n{Fore.GREEN}✅ All tests passed!{Style.RESET_ALL}")
            sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="D3X7-ALGO Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--devnet", action="store_true", help="Run only devnet tests")
    parser.add_argument("--mainnet", action="store_true", help="Run only mainnet tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", action="store_true", help="Show detailed test output")
    parser.add_argument("--noanchor", action="store_true", help="Skip anchor-related tests")
    
    args = parser.parse_args()
    runner = TestRunner()
    runner.run_tests(args)

if __name__ == "__main__":
    main() 