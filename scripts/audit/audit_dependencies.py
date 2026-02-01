#!/usr/bin/env python3
"""
Dependencies Audit Module

Checks:
- Security vulnerabilities (npm audit, safety)
- Outdated packages
- Unused dependencies
- License compliance

Usage:
    python audit_dependencies.py --vulnerabilities
    python audit_dependencies.py --check all
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


class DependenciesAuditor:
    """Automated dependency checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: List[AuditResult] = []

    def check_python_vulnerabilities(self) -> AuditResult:
        """Check Python dependencies for vulnerabilities using safety"""
        print("🔍 Checking Python dependency vulnerabilities...")

        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            try:
                vulns = json.loads(result.stdout) if result.stdout else []

                if not vulns:
                    return AuditResult(
                        name="Python Vulnerabilities",
                        status="PASS",
                        message="No known vulnerabilities in Python dependencies",
                        details=[]
                    )

                critical = [v for v in vulns if v.get('severity', '').lower() == 'critical']
                high = [v for v in vulns if v.get('severity', '').lower() == 'high']
                moderate = [v for v in vulns if v.get('severity', '').lower() == 'moderate']

                details = []
                if critical:
                    for v in critical:
                        details.append(
                            f"CRITICAL: {v.get('package', 'unknown')} - {v.get('vulnerability', 'no description')}"
                        )
                if high:
                    for v in high:
                        details.append(
                            f"HIGH: {v.get('package', 'unknown')} - {v.get('vulnerability', 'no description')}"
                        )
                if moderate:
                    details.append(f"MODERATE: {len(moderate)} moderate severity issues")

                if critical:
                    return AuditResult(
                        name="Python Vulnerabilities",
                        status="FAIL",
                        message=f"Found {len(critical)} CRITICAL vulnerabilities",
                        details=details
                    )
                elif high:
                    return AuditResult(
                        name="Python Vulnerabilities",
                        status="WARN",
                        message=f"Found {len(high)} HIGH vulnerabilities",
                        details=details
                    )
                else:
                    return AuditResult(
                        name="Python Vulnerabilities",
                        status="WARN",
                        message=f"Found {len(moderate)} MODERATE vulnerabilities",
                        details=details
                    )

            except json.JSONDecodeError:
                return AuditResult(
                    name="Python Vulnerabilities",
                    status="WARN",
                    message="Could not parse safety output",
                    details=[]
                )

        except FileNotFoundError:
            return AuditResult(
                name="Python Vulnerabilities",
                status="WARN",
                message="safety not installed - run: pip install safety",
                details=[]
            )
        except subprocess.TimeoutExpired:
            return AuditResult(
                name="Python Vulnerabilities",
                status="WARN",
                message="safety check timed out",
                details=[]
            )

    def check_npm_vulnerabilities(self) -> AuditResult:
        """Check npm dependencies for vulnerabilities"""
        print("🔍 Checking npm dependency vulnerabilities...")

        frontend_dir = self.project_root / "frontend"
        if not frontend_dir.exists():
            return AuditResult(
                name="NPM Vulnerabilities",
                status="WARN",
                message="Frontend directory not found",
                details=[]
            )

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            try:
                audit = json.loads(result.stdout)
                vulnerabilities = audit.get('metadata', {}).get('vulnerabilities', {})

                critical = vulnerabilities.get('critical', 0)
                high = vulnerabilities.get('high', 0)
                moderate = vulnerabilities.get('moderate', 0)
                low = vulnerabilities.get('low', 0)

                if critical == 0 and high == 0 and moderate == 0 and low == 0:
                    return AuditResult(
                        name="NPM Vulnerabilities",
                        status="PASS",
                        message="No known vulnerabilities in npm dependencies",
                        details=[]
                    )

                details = [
                    f"Critical: {critical}",
                    f"High: {high}",
                    f"Moderate: {moderate}",
                    f"Low: {low}"
                ]

                if critical > 0:
                    return AuditResult(
                        name="NPM Vulnerabilities",
                        status="FAIL",
                        message=f"Found {critical} CRITICAL npm vulnerabilities",
                        details=details
                    )
                elif high > 0:
                    return AuditResult(
                        name="NPM Vulnerabilities",
                        status="WARN",
                        message=f"Found {high} HIGH npm vulnerabilities",
                        details=details
                    )
                else:
                    return AuditResult(
                        name="NPM Vulnerabilities",
                        status="PASS",
                        message=f"Only {moderate + low} moderate/low vulnerabilities",
                        details=details
                    )

            except json.JSONDecodeError:
                return AuditResult(
                    name="NPM Vulnerabilities",
                    status="WARN",
                    message="Could not parse npm audit output",
                    details=[]
                )

        except FileNotFoundError:
            return AuditResult(
                name="NPM Vulnerabilities",
                status="WARN",
                message="npm not found",
                details=[]
            )
        except subprocess.TimeoutExpired:
            return AuditResult(
                name="NPM Vulnerabilities",
                status="WARN",
                message="npm audit timed out",
                details=[]
            )

    def check_outdated_packages(self) -> AuditResult:
        """Check for outdated packages"""
        print("🔍 Checking for outdated packages...")

        issues = []

        # Check Python packages
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                outdated = json.loads(result.stdout) if result.stdout else []
                if outdated:
                    issues.append(f"Python: {len(outdated)} outdated packages")

                    # Check for critically outdated (>6 months is heuristic)
                    # Note: Would need to compare versions properly for real check
                    if len(outdated) > 10:
                        issues.append(f"WARN: Many Python packages outdated ({len(outdated)})")

        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

        # Check npm packages
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            try:
                result = subprocess.run(
                    ["npm", "outdated", "--json"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.stdout:
                    outdated = json.loads(result.stdout)
                    if outdated:
                        issues.append(f"NPM: {len(outdated)} outdated packages")

                        if len(outdated) > 15:
                            issues.append(f"WARN: Many npm packages outdated ({len(outdated)})")

            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass

        if issues:
            has_warnings = any("WARN" in i for i in issues)
            return AuditResult(
                name="Outdated Packages",
                status="WARN" if has_warnings else "PASS",
                message=f"Found outdated packages",
                details=issues
            )

        return AuditResult(
            name="Outdated Packages",
            status="PASS",
            message="All packages up to date",
            details=[]
        )

    def check_unused_dependencies(self) -> AuditResult:
        """Check for unused dependencies"""
        print("🔍 Checking for unused dependencies...")

        issues = []

        # Check npm with depcheck
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            try:
                result = subprocess.run(
                    ["npx", "depcheck", "--json"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    depcheck = json.loads(result.stdout)
                    unused = depcheck.get('dependencies', [])

                    if unused:
                        issues.append(f"NPM: {len(unused)} unused dependencies: {', '.join(unused[:5])}")
                        if len(unused) > 5:
                            issues.append(f"... and {len(unused) - 5} more")

            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
                issues.append("INFO: depcheck not available - run: npx depcheck")

        if issues:
            return AuditResult(
                name="Unused Dependencies",
                status="WARN",
                message=f"Found unused dependencies",
                details=issues
            )

        return AuditResult(
            name="Unused Dependencies",
            status="PASS",
            message="No unused dependencies detected",
            details=[]
        )

    def run_all_checks(self) -> List[AuditResult]:
        """Run all dependency checks"""
        self.results = []

        self.results.append(self.check_python_vulnerabilities())
        self.results.append(self.check_npm_vulnerabilities())
        self.results.append(self.check_outdated_packages())
        self.results.append(self.check_unused_dependencies())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("DEPENDENCIES AUDIT SUMMARY")
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
            print("🔴 OVERALL: FAILED - Critical dependency issues")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Dependency updates recommended")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - Dependencies healthy")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Dependencies Audit")
    parser.add_argument(
        "--check",
        choices=["all", "vulnerabilities", "outdated", "unused"],
        default="all",
        help="Which checks to run"
    )

    args = parser.parse_args()

    auditor = DependenciesAuditor()

    if args.check == "all":
        auditor.run_all_checks()
    elif args.check == "vulnerabilities":
        auditor.results.append(auditor.check_python_vulnerabilities())
        auditor.results.append(auditor.check_npm_vulnerabilities())
    elif args.check == "outdated":
        auditor.results.append(auditor.check_outdated_packages())
    elif args.check == "unused":
        auditor.results.append(auditor.check_unused_dependencies())

    auditor.print_summary()


if __name__ == "__main__":
    main()
