#!/usr/bin/env python3
"""
Test Coverage Audit Module

Checks:
- Unit test coverage (pytest, vitest)
- Critical business logic tests
- Edge cases coverage
- Missing tests for new endpoints

Usage:
    python audit_tests.py --coverage
    python audit_tests.py --critical-only
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class AuditResult:
    """Result of a single audit check"""
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    details: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []


class TestAuditor:
    """Automated test coverage checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: List[AuditResult] = []

    def check_backend_coverage(self) -> AuditResult:
        """Check backend test coverage with pytest"""
        print("🔍 Checking backend test coverage...")

        try:
            # Run pytest with coverage
            result = subprocess.run(
                [
                    "pytest",
                    "tests/",
                    "--cov=app",
                    "--cov-report=term-missing",
                    "--cov-report=json",
                    "-q"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse coverage report
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)

                    # Check critical modules
                    services_coverage = self._get_module_coverage(coverage_data, 'app/services')
                    routers_coverage = self._get_module_coverage(coverage_data, 'app/routers')

                    details = [
                        f"Total coverage: {total_coverage:.1f}%",
                        f"Services coverage: {services_coverage:.1f}%",
                        f"Routers coverage: {routers_coverage:.1f}%"
                    ]

                    # Determine status based on thresholds
                    if services_coverage >= 90 and routers_coverage >= 80:
                        status = "PASS"
                        message = f"Excellent coverage - {total_coverage:.1f}%"
                    elif services_coverage >= 75 and routers_coverage >= 60:
                        status = "WARN"
                        message = f"Acceptable coverage - {total_coverage:.1f}% (improve services/routers)"
                    else:
                        status = "FAIL"
                        message = f"Insufficient coverage - {total_coverage:.1f}% (services <75% or routers <60%)"

                    return AuditResult(
                        name="Backend Coverage",
                        status=status,
                        message=message,
                        details=details
                    )

        except subprocess.TimeoutExpired:
            return AuditResult(
                name="Backend Coverage",
                status="FAIL",
                message="Tests timed out (>60s)",
                details=[]
            )
        except Exception as e:
            return AuditResult(
                name="Backend Coverage",
                status="FAIL",
                message=f"Error running tests: {str(e)}",
                details=[]
            )

        return AuditResult(
            name="Backend Coverage",
            status="WARN",
            message="Could not determine coverage",
            details=[]
        )

    def _get_module_coverage(self, coverage_data: dict, module_prefix: str) -> float:
        """Extract coverage for specific module"""
        files = coverage_data.get('files', {})
        module_files = {k: v for k, v in files.items() if k.startswith(module_prefix)}

        if not module_files:
            return 0.0

        total_statements = sum(f['summary']['num_statements'] for f in module_files.values())
        covered_statements = sum(f['summary']['covered_lines'] for f in module_files.values())

        if total_statements == 0:
            return 0.0

        return (covered_statements / total_statements) * 100

    def check_frontend_coverage(self) -> AuditResult:
        """Check frontend test coverage with vitest"""
        print("🔍 Checking frontend test coverage...")

        frontend_dir = self.project_root / "frontend"
        if not frontend_dir.exists():
            return AuditResult(
                name="Frontend Coverage",
                status="WARN",
                message="Frontend directory not found",
                details=[]
            )

        try:
            # Run vitest with coverage
            result = subprocess.run(
                ["npm", "run", "test:unit", "--", "--coverage", "--run"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse coverage from output (vitest outputs to console)
            coverage_pattern = r"All files.*?(\d+\.?\d*)"
            import re
            match = re.search(coverage_pattern, result.stdout)

            if match:
                total_coverage = float(match.group(1))

                details = [f"Total frontend coverage: {total_coverage:.1f}%"]

                # Thresholds for frontend
                if total_coverage >= 80:
                    status = "PASS"
                    message = f"Good coverage - {total_coverage:.1f}%"
                elif total_coverage >= 60:
                    status = "WARN"
                    message = f"Acceptable coverage - {total_coverage:.1f}% (aim for 80%+)"
                else:
                    status = "FAIL"
                    message = f"Low coverage - {total_coverage:.1f}% (minimum 60%)"

                return AuditResult(
                    name="Frontend Coverage",
                    status=status,
                    message=message,
                    details=details
                )

        except subprocess.TimeoutExpired:
            return AuditResult(
                name="Frontend Coverage",
                status="FAIL",
                message="Frontend tests timed out (>60s)",
                details=[]
            )
        except Exception as e:
            return AuditResult(
                name="Frontend Coverage",
                status="WARN",
                message=f"Could not run frontend tests: {str(e)}",
                details=[]
            )

        return AuditResult(
            name="Frontend Coverage",
            status="WARN",
            message="Could not determine frontend coverage",
            details=[]
        )

    def check_critical_tests(self) -> AuditResult:
        """Check that critical business logic tests pass"""
        print("🔍 Running critical tests...")

        try:
            # Run pytest with critical marker
            result = subprocess.run(
                ["pytest", "tests/", "-m", "critical", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output for pass/fail counts
            output = result.stdout + result.stderr

            # Extract test results
            import re
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)

            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0

            details = [
                f"Critical tests passed: {passed}",
                f"Critical tests failed: {failed}"
            ]

            if failed == 0 and passed > 0:
                return AuditResult(
                    name="Critical Tests",
                    status="PASS",
                    message=f"All {passed} critical tests passed ✅",
                    details=details
                )
            elif failed > 0:
                return AuditResult(
                    name="Critical Tests",
                    status="FAIL",
                    message=f"{failed} critical tests FAILED ❌",
                    details=details + [result.stdout]
                )
            else:
                return AuditResult(
                    name="Critical Tests",
                    status="WARN",
                    message="No critical tests found (add @pytest.mark.critical)",
                    details=details
                )

        except subprocess.TimeoutExpired:
            return AuditResult(
                name="Critical Tests",
                status="FAIL",
                message="Critical tests timed out",
                details=[]
            )
        except Exception as e:
            return AuditResult(
                name="Critical Tests",
                status="FAIL",
                message=f"Error running critical tests: {str(e)}",
                details=[]
            )

    def check_missing_tests(self) -> AuditResult:
        """Check for API endpoints without tests"""
        print("🔍 Checking for untested API endpoints...")

        issues = []

        # Find all router endpoints
        routers_dir = self.project_root / "app" / "routers"
        if not routers_dir.exists():
            return AuditResult(
                name="Missing Tests",
                status="WARN",
                message="Routers directory not found",
                details=[]
            )

        import re
        endpoint_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']')

        endpoints = []
        for router_file in routers_dir.glob("*.py"):
            with open(router_file, 'r') as f:
                content = f.read()
                matches = endpoint_pattern.findall(content)
                for method, path in matches:
                    endpoints.append((router_file.stem, method, path))

        # Find all test functions
        tests_dir = self.project_root / "tests"
        test_functions = []
        if tests_dir.exists():
            for test_file in tests_dir.glob("test_*.py"):
                with open(test_file, 'r') as f:
                    content = f.read()
                    # Simple heuristic: function name contains router name
                    test_matches = re.findall(r'def (test_\w+)', content)
                    test_functions.extend(test_matches)

        # Check coverage (simple heuristic)
        untested = []
        for router, method, path in endpoints:
            # Check if there's a test that might cover this
            # (simple check - looks for router name in test functions)
            router_clean = router.replace('_router', '')
            has_test = any(router_clean in tf for tf in test_functions)

            if not has_test:
                untested.append(f"{method.upper()} {path} (from {router}.py)")

        if untested:
            return AuditResult(
                name="Missing Tests",
                status="WARN",
                message=f"Found {len(untested)} potentially untested endpoints",
                details=untested[:10]  # Show first 10
            )

        return AuditResult(
            name="Missing Tests",
            status="PASS",
            message=f"All {len(endpoints)} endpoints appear to have test coverage",
            details=[]
        )

    def run_all_checks(self) -> List[AuditResult]:
        """Run all test audit checks"""
        self.results = []

        self.results.append(self.check_backend_coverage())
        self.results.append(self.check_frontend_coverage())
        self.results.append(self.check_critical_tests())
        self.results.append(self.check_missing_tests())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("TEST COVERAGE AUDIT SUMMARY")
        print("="*60)

        for result in self.results:
            status_emoji = {
                "PASS": "✅",
                "WARN": "🟡",
                "FAIL": "🔴"
            }
            emoji = status_emoji.get(result.status, "❓")

            print(f"\n{emoji} {result.name}: {result.status}")
            print(f"   {result.message}")

            if result.details:
                print(f"   Details:")
                for detail in result.details[:10]:
                    print(f"   - {detail}")
                if len(result.details) > 10:
                    print(f"   ... and {len(result.details) - 10} more")

        # Overall status
        has_failures = any(r.status == "FAIL" for r in self.results)
        has_warnings = any(r.status == "WARN" for r in self.results)

        print("\n" + "="*60)
        if has_failures:
            print("🔴 OVERALL: FAILED - Critical test issues")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Improve test coverage")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - Excellent test coverage")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Test Coverage Audit")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run coverage analysis"
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Run only critical tests"
    )

    args = parser.parse_args()

    auditor = TestAuditor()

    if args.critical_only:
        auditor.results.append(auditor.check_critical_tests())
    else:
        auditor.run_all_checks()

    auditor.print_summary()


if __name__ == "__main__":
    main()
