#!/usr/bin/env python3
"""
Performance Audit Module

Checks:
- N+1 query detection
- API response times
- Frontend bundle size
- Database indexes

Usage:
    python audit_performance.py --n-plus-one
    python audit_performance.py --check all
"""

import subprocess
import sys
import re
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


class PerformanceAuditor:
    """Automated performance checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: List[AuditResult] = []

    def check_n_plus_one_queries(self) -> AuditResult:
        """Check for potential N+1 query patterns"""
        print("🔍 Checking for N+1 query patterns...")

        issues = []
        routers_dir = self.project_root / "app" / "routers"

        if not routers_dir.exists():
            return AuditResult(
                name="N+1 Queries",
                status="WARN",
                message="Routers directory not found",
                details=[]
            )

        # Look for queries inside loops
        for router_file in routers_dir.glob("*.py"):
            with open(router_file, 'r') as f:
                content = f.read()
                lines = content.split('\n')

                in_loop = False
                loop_indent = 0

                for i, line in enumerate(lines, 1):
                    # Detect loop start
                    if re.match(r'\s*for\s+.+\s+in\s+', line):
                        in_loop = True
                        loop_indent = len(line) - len(line.lstrip())

                    # Check if we exited loop
                    if in_loop:
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= loop_indent and line.strip():
                            in_loop = False

                    # Check for DB queries inside loop
                    if in_loop and ('session.execute' in line or 'session.query' in line or 'await' in line):
                        issues.append(
                            f"WARN: Possible N+1 query in {router_file.name}:{i} - "
                            f"query inside loop"
                        )

        # Check for lazy loading in models
        models_dir = self.project_root / "app" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.py"):
                with open(model_file, 'r') as f:
                    content = f.read()
                    # Look for relationship without lazy parameter or lazy="select"
                    if 'relationship(' in content:
                        # Check if using joinedload/selectinload
                        if 'lazy=' not in content or 'lazy="select"' in content:
                            issues.append(
                                f"INFO: {model_file.name} uses default lazy loading - "
                                f"consider joinedload/selectinload for better performance"
                            )

        if issues:
            critical = [i for i in issues if "WARN" in i]
            if critical:
                return AuditResult(
                    name="N+1 Queries",
                    status="WARN",
                    message=f"Found {len(critical)} potential N+1 query patterns",
                    details=issues
                )
            else:
                return AuditResult(
                    name="N+1 Queries",
                    status="PASS",
                    message="No critical N+1 patterns (some info items)",
                    details=issues
                )

        return AuditResult(
            name="N+1 Queries",
            status="PASS",
            message="No N+1 query patterns detected"
        )

    def check_bundle_size(self) -> AuditResult:
        """Check frontend bundle size"""
        print("🔍 Checking frontend bundle size...")

        frontend_dir = self.project_root / "frontend"
        dist_dir = frontend_dir / "dist" / "assets"

        if not dist_dir.exists():
            return AuditResult(
                name="Bundle Size",
                status="WARN",
                message="Frontend not built - run 'npm run build' first",
                details=[]
            )

        issues = []
        js_files = list(dist_dir.glob("*.js"))

        if not js_files:
            return AuditResult(
                name="Bundle Size",
                status="WARN",
                message="No JS bundles found in dist/",
                details=[]
            )

        total_size = 0
        large_files = []

        for js_file in js_files:
            size_kb = js_file.stat().st_size / 1024

            total_size += size_kb

            # Check individual file sizes
            if 'vendor' in js_file.name:
                # Vendor bundle threshold: 1MB
                if size_kb > 1024:
                    large_files.append(f"WARN: {js_file.name} is {size_kb:.0f}KB (>1MB)")
                elif size_kb > 1536:
                    large_files.append(f"CRITICAL: {js_file.name} is {size_kb:.0f}KB (>1.5MB)")
            else:
                # Main bundle threshold: 500KB
                if size_kb > 500:
                    large_files.append(f"WARN: {js_file.name} is {size_kb:.0f}KB (>500KB)")
                elif size_kb > 800:
                    large_files.append(f"CRITICAL: {js_file.name} is {size_kb:.0f}KB (>800KB)")

        details = [f"Total bundle size: {total_size:.0f}KB"] + large_files

        if any("CRITICAL" in f for f in large_files):
            return AuditResult(
                name="Bundle Size",
                status="FAIL",
                message=f"Bundle too large ({total_size:.0f}KB)",
                details=details
            )
        elif large_files:
            return AuditResult(
                name="Bundle Size",
                status="WARN",
                message=f"Bundle size acceptable but improvable ({total_size:.0f}KB)",
                details=details
            )

        return AuditResult(
            name="Bundle Size",
            status="PASS",
            message=f"Bundle size good ({total_size:.0f}KB)",
            details=details
        )

    def check_database_indexes(self) -> AuditResult:
        """Check for missing database indexes"""
        print("🔍 Checking database indexes...")

        issues = []

        # Check if frequently queried columns are indexed
        # This requires analyzing both models and query patterns

        models_dir = self.project_root / "app" / "models"
        routers_dir = self.project_root / "app" / "routers"

        if not models_dir.exists() or not routers_dir.exists():
            return AuditResult(
                name="Database Indexes",
                status="WARN",
                message="Cannot analyze - models or routers directory not found",
                details=[]
            )

        # Find frequently filtered columns in routers
        filter_patterns = {}
        for router_file in routers_dir.glob("*.py"):
            with open(router_file, 'r') as f:
                content = f.read()
                # Look for filter/where clauses
                matches = re.findall(r'\.filter\((\w+)\.(\w+)\s*==', content)
                for model, column in matches:
                    key = f"{model}.{column}"
                    filter_patterns[key] = filter_patterns.get(key, 0) + 1

        # Check if these columns have indexes in models
        for model_file in models_dir.glob("*.py"):
            with open(model_file, 'r') as f:
                content = f.read()
                model_name = model_file.stem.title().replace('_', '')

                # Find indexed columns
                indexed_cols = re.findall(r'(\w+)\s*=\s*Column\([^)]*index=True', content)

                # Check if frequently filtered columns are indexed
                for pattern, count in filter_patterns.items():
                    if pattern.startswith(model_name) and count > 3:
                        col = pattern.split('.')[1]
                        if col not in indexed_cols and col not in ['id', 'created_at']:
                            issues.append(
                                f"WARN: Column {pattern} filtered {count} times but not indexed"
                            )

        if issues:
            return AuditResult(
                name="Database Indexes",
                status="WARN",
                message=f"Found {len(issues)} potentially missing indexes",
                details=issues
            )

        return AuditResult(
            name="Database Indexes",
            status="PASS",
            message="Database indexes appear adequate",
            details=[]
        )

    def run_all_checks(self) -> List[AuditResult]:
        """Run all performance checks"""
        self.results = []

        self.results.append(self.check_n_plus_one_queries())
        self.results.append(self.check_bundle_size())
        self.results.append(self.check_database_indexes())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("PERFORMANCE AUDIT SUMMARY")
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
            print("🔴 OVERALL: FAILED - Performance issues found")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Performance can be improved")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - Performance looks good")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Performance Audit")
    parser.add_argument(
        "--check",
        choices=["all", "n-plus-one", "bundle", "indexes"],
        default="all",
        help="Which checks to run"
    )

    args = parser.parse_args()

    auditor = PerformanceAuditor()

    if args.check == "all":
        auditor.run_all_checks()
    elif args.check == "n-plus-one":
        auditor.results.append(auditor.check_n_plus_one_queries())
    elif args.check == "bundle":
        auditor.results.append(auditor.check_bundle_size())
    elif args.check == "indexes":
        auditor.results.append(auditor.check_database_indexes())

    auditor.print_summary()


if __name__ == "__main__":
    main()
