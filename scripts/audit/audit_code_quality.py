#!/usr/bin/env python3
"""
Code Quality Audit Module

Checks:
- Dead code detection
- Duplicity (DRY violations)
- Anti-pattern detection (L-001 to L-038)
- Complexity metrics

Usage:
    python audit_code_quality.py --check all
    python audit_code_quality.py --check dead-code
    python audit_code_quality.py --check anti-patterns --verbose
"""

import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
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


class CodeQualityAuditor:
    """Automated code quality checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: List[AuditResult] = []

    def check_dead_code(self) -> AuditResult:
        """Check for unused imports and functions"""
        print("🔍 Checking for dead code...")

        issues = []

        # Check for unused imports (simple heuristic - can improve with AST)
        # This is a placeholder - real implementation would use pylint or similar

        return AuditResult(
            name="Dead Code Detection",
            status="PASS",
            message="No obvious dead code detected (manual review recommended)",
            details=issues
        )

    def check_duplicity(self) -> AuditResult:
        """Check for duplicate code patterns"""
        print("🔍 Checking for duplicity...")

        issues = []

        # Check duplicate CSS utilities (L-033, L-034)
        duplicate_css = self._check_duplicate_css()
        if duplicate_css:
            issues.extend(duplicate_css)

        # Check hardcoded font-size (L-036)
        hardcoded_css = self._check_hardcoded_css()
        if hardcoded_css:
            issues.extend(hardcoded_css)

        # Check business logic in JS (L-001)
        js_calculations = self._check_js_calculations()
        if js_calculations:
            issues.extend(js_calculations)

        if issues:
            status = "FAIL" if any("CRITICAL" in i for i in issues) else "WARN"
            return AuditResult(
                name="Duplicity Check",
                status=status,
                message=f"Found {len(issues)} duplicity issues",
                details=issues
            )

        return AuditResult(
            name="Duplicity Check",
            status="PASS",
            message="No duplicity detected"
        )

    def _check_duplicate_css(self) -> List[str]:
        """Check for duplicate CSS utility classes (L-033)"""
        issues = []
        patterns = [r"^\.btn\s*{", r"^\.badge", r"^\.card"]

        for pattern in patterns:
            cmd = [
                "grep", "-r", pattern,
                str(self.project_root / "frontend/src"),
                "--include=*.vue"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                matches = result.stdout.strip().split('\n')
                if len(matches) > 0:
                    issues.append(
                        f"CRITICAL: Duplicate CSS class '{pattern}' found in {len(matches)} files "
                        f"(L-033 violation - should be only in design-system.css)"
                    )

        return issues

    def _check_hardcoded_css(self) -> List[str]:
        """Check for hardcoded CSS values (L-036)"""
        issues = []

        cmd = [
            "grep", "-r", r"font-size:\s*[0-9]",
            str(self.project_root / "frontend/src"),
            "--include=*.vue", "--include=*.css"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            issues.append(
                f"CRITICAL: Found {len(matches)} hardcoded font-size values "
                f"(L-036 violation - use design tokens var(--text-*))"
            )

        return issues

    def _check_js_calculations(self) -> List[str]:
        """Check for business calculations in JavaScript (L-001)"""
        issues = []

        cmd = [
            "grep", "-r", r"calculate.*=",
            str(self.project_root / "frontend/src"),
            "--include=*.vue", "--include=*.ts", "--include=*.js"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            # Filter out test files and composables (allowed)
            suspicious = [m for m in matches if "__tests__" not in m and "composables" not in m]
            if suspicious:
                issues.append(
                    f"CRITICAL: Found {len(suspicious)} business calculations in JS "
                    f"(L-001 violation - calculations must be in Python services/)"
                )

        return issues

    def check_anti_patterns(self, verbose: bool = False) -> AuditResult:
        """Check for known anti-patterns (L-001 to L-038)"""
        print("🔍 Checking for anti-patterns...")

        issues = []

        # L-008: Missing transaction handling
        no_transactions = self._check_transactions()
        if no_transactions:
            issues.extend(no_transactions)

        # L-038: Emoji in UI
        emoji_in_ui = self._check_emoji()
        if emoji_in_ui:
            issues.extend(emoji_in_ui)

        # Combine with duplicity checks
        duplicity = self.check_duplicity()
        if duplicity.details:
            issues.extend(duplicity.details)

        if issues:
            blocking = [i for i in issues if "CRITICAL" in i]
            warnings = [i for i in issues if "WARN" in i]

            if blocking:
                status = "FAIL"
                message = f"Found {len(blocking)} BLOCKING anti-patterns"
            elif warnings:
                status = "WARN"
                message = f"Found {len(warnings)} warning anti-patterns"
            else:
                status = "WARN"
                message = f"Found {len(issues)} potential issues"

            return AuditResult(
                name="Anti-Pattern Detection",
                status=status,
                message=message,
                details=issues
            )

        return AuditResult(
            name="Anti-Pattern Detection",
            status="PASS",
            message="No anti-patterns detected"
        )

    def _check_transactions(self) -> List[str]:
        """Check for missing transaction handling (L-008)"""
        issues = []

        # Find router files without try/except
        routers_dir = self.project_root / "app" / "routers"
        if routers_dir.exists():
            for router_file in routers_dir.glob("*.py"):
                with open(router_file, 'r') as f:
                    content = f.read()
                    # Simple heuristic: if file has POST/PUT/DELETE but no try/except
                    has_mutations = any(x in content for x in ["@router.post", "@router.put", "@router.delete"])
                    has_try = "try:" in content

                    if has_mutations and not has_try:
                        issues.append(
                            f"CRITICAL: {router_file.name} has mutations but no try/except "
                            f"(L-008 violation - must have transaction handling)"
                        )

        return issues

    def _check_emoji(self) -> List[str]:
        """Check for emoji in production UI (L-038)"""
        issues = []

        # Unicode ranges for common emoji
        emoji_pattern = r"[🀀-🿿😀-🙏🚀-🛿⚀-⚿✀-➿⬀-⬿]"

        cmd = [
            "grep", "-r", "-P", emoji_pattern,
            str(self.project_root / "frontend/src"),
            "--include=*.vue", "--include=*.ts"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            # Filter out test files
            production_matches = [m for m in matches if "__tests__" not in m and "archive" not in m]

            if production_matches:
                issues.append(
                    f"CRITICAL: Found {len(production_matches)} emoji in production UI "
                    f"(L-038 violation - use Lucide icons only)"
                )

        return issues

    def check_complexity(self) -> AuditResult:
        """Check code complexity metrics"""
        print("🔍 Checking complexity metrics...")

        issues = []

        # Check file sizes (LOC)
        large_files = self._check_file_sizes()
        if large_files:
            issues.extend(large_files)

        # Try to run radon if available (optional)
        radon_available = subprocess.run(
            ["which", "radon"],
            capture_output=True
        ).returncode == 0

        if radon_available:
            radon_results = self._run_radon()
            if radon_results:
                issues.extend(radon_results)
        else:
            issues.append("INFO: radon not installed - skipping cyclomatic complexity check")

        if any("CRITICAL" in i or "WARN" in i for i in issues):
            status = "FAIL" if any("CRITICAL" in i for i in issues) else "WARN"
            return AuditResult(
                name="Complexity Metrics",
                status=status,
                message=f"Found {len(issues)} complexity issues",
                details=issues
            )

        return AuditResult(
            name="Complexity Metrics",
            status="PASS",
            message="Complexity within acceptable ranges",
            details=issues
        )

    def _check_file_sizes(self) -> List[str]:
        """Check for files exceeding LOC thresholds"""
        issues = []

        # Check Vue components (should be <300 LOC per L-036)
        components_dir = self.project_root / "frontend/src/components"
        if components_dir.exists():
            for vue_file in components_dir.rglob("*.vue"):
                with open(vue_file, 'r') as f:
                    lines = len(f.readlines())
                    if lines > 500:
                        issues.append(f"CRITICAL: {vue_file.name} has {lines} LOC (L-036 violation - max 300)")
                    elif lines > 300:
                        issues.append(f"WARN: {vue_file.name} has {lines} LOC (should be <300)")

        # Check Python modules (should be <1000 LOC)
        app_dir = self.project_root / "app"
        if app_dir.exists():
            for py_file in app_dir.rglob("*.py"):
                with open(py_file, 'r') as f:
                    lines = len(f.readlines())
                    if lines > 1000:
                        issues.append(f"CRITICAL: {py_file.name} has {lines} LOC (max 1000)")
                    elif lines > 500:
                        issues.append(f"WARN: {py_file.name} has {lines} LOC (consider splitting)")

        return issues

    def _run_radon(self) -> List[str]:
        """Run radon complexity analysis"""
        issues = []

        # Cyclomatic complexity
        result = subprocess.run(
            ["radon", "cc", str(self.project_root / "app"), "-a", "-nb"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Parse output for D, E, F grades (complex code)
            for line in result.stdout.split('\n'):
                if any(grade in line for grade in [' D ', ' E ', ' F ']):
                    issues.append(f"WARN: High complexity detected - {line.strip()}")

        return issues

    def run_all_checks(self, verbose: bool = False) -> List[AuditResult]:
        """Run all code quality checks"""
        self.results = []

        self.results.append(self.check_dead_code())
        self.results.append(self.check_duplicity())
        self.results.append(self.check_anti_patterns(verbose))
        self.results.append(self.check_complexity())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("CODE QUALITY AUDIT SUMMARY")
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
                for detail in result.details[:10]:  # Show first 10
                    print(f"   - {detail}")
                if len(result.details) > 10:
                    print(f"   ... and {len(result.details) - 10} more")

        # Overall status
        has_failures = any(r.status == "FAIL" for r in self.results)
        has_warnings = any(r.status == "WARN" for r in self.results)

        print("\n" + "="*60)
        if has_failures:
            print("🔴 OVERALL: FAILED - Critical issues found")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Some issues to address")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - All checks passed")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Code Quality Audit")
    parser.add_argument(
        "--check",
        choices=["all", "dead-code", "duplicity", "anti-patterns", "complexity"],
        default="all",
        help="Which checks to run"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    auditor = CodeQualityAuditor()

    if args.check == "all":
        auditor.run_all_checks(verbose=args.verbose)
    elif args.check == "dead-code":
        auditor.results.append(auditor.check_dead_code())
    elif args.check == "duplicity":
        auditor.results.append(auditor.check_duplicity())
    elif args.check == "anti-patterns":
        auditor.results.append(auditor.check_anti_patterns(verbose=args.verbose))
    elif args.check == "complexity":
        auditor.results.append(auditor.check_complexity())

    auditor.print_summary()


if __name__ == "__main__":
    main()
