#!/usr/bin/env python3
"""
GESTIMA Full Post-Phase Audit Runner

Master orchestrator for comprehensive quality audit.
Runs all audit modules and generates consolidated report.

Usage:
    python run_full_audit.py                    # Run all checks
    python run_full_audit.py --critical-only    # Only blocking checks
    python run_full_audit.py --output report.md # Save to file
    python run_full_audit.py --sections code-quality,security,tests
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Import all audit modules
from audit_code_quality import CodeQualityAuditor
from audit_tests import TestAuditor
from audit_security import SecurityAuditor
from audit_performance import PerformanceAuditor
from audit_database import DatabaseAuditor
from audit_dependencies import DependenciesAuditor


class FullAuditRunner:
    """Orchestrates all audit modules"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.all_results = {}
        self.start_time = datetime.now()

    def run_all_audits(self, sections: List[str] = None):
        """Run all audit modules"""
        print("="*60)
        print("GESTIMA POST-PHASE AUDIT - FULL SCAN")
        print("="*60)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project: {self.project_root}")
        print("="*60)

        sections = sections or [
            "code-quality",
            "tests",
            "security",
            "performance",
            "database",
            "dependencies"
        ]

        # 1. Code Quality
        if "code-quality" in sections:
            print("\n\n📋 1️⃣  CODE QUALITY AUDIT")
            print("="*60)
            auditor = CodeQualityAuditor(self.project_root)
            self.all_results["code_quality"] = auditor.run_all_checks()

        # 2. Test Coverage
        if "tests" in sections:
            print("\n\n🧪 2️⃣  TEST COVERAGE AUDIT")
            print("="*60)
            auditor = TestAuditor(self.project_root)
            self.all_results["tests"] = auditor.run_all_checks()

        # 3. Security
        if "security" in sections:
            print("\n\n🔒 3️⃣  SECURITY AUDIT")
            print("="*60)
            auditor = SecurityAuditor(self.project_root)
            self.all_results["security"] = auditor.run_all_checks()

        # 4. Performance
        if "performance" in sections:
            print("\n\n⚡ 4️⃣  PERFORMANCE AUDIT")
            print("="*60)
            auditor = PerformanceAuditor(self.project_root)
            self.all_results["performance"] = auditor.run_all_checks()

        # 5. Database
        if "database" in sections:
            print("\n\n💾 5️⃣  DATABASE AUDIT")
            print("="*60)
            auditor = DatabaseAuditor(self.project_root)
            self.all_results["database"] = auditor.run_all_checks()

        # 6. Dependencies
        if "dependencies" in sections:
            print("\n\n📦 6️⃣  DEPENDENCIES AUDIT")
            print("="*60)
            auditor = DependenciesAuditor(self.project_root)
            self.all_results["dependencies"] = auditor.run_all_checks()

    def print_consolidated_summary(self):
        """Print consolidated audit summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print("\n\n" + "="*60)
        print("CONSOLIDATED AUDIT SUMMARY")
        print("="*60)
        print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print("="*60)

        # Aggregate results
        total_checks = 0
        passed = 0
        warnings = 0
        failures = 0

        for section_name, results in self.all_results.items():
            print(f"\n{section_name.upper().replace('_', ' ')}:")

            for result in results:
                total_checks += 1

                status_emoji = {
                    "PASS": "✅",
                    "WARN": "🟡",
                    "FAIL": "🔴"
                }
                emoji = status_emoji.get(result.status, "❓")

                print(f"  {emoji} {result.name}: {result.status}")

                if result.status == "PASS":
                    passed += 1
                elif result.status == "WARN":
                    warnings += 1
                elif result.status == "FAIL":
                    failures += 1

        # Overall verdict
        print("\n" + "="*60)
        print("OVERALL VERDICT")
        print("="*60)
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed}")
        print(f"🟡 Warnings: {warnings}")
        print(f"🔴 Failed: {failures}")
        print("="*60)

        if failures > 0:
            print("\n🔴 OVERALL: BLOCKED")
            print("   Critical issues must be fixed before merge/deploy")
            return "FAIL"
        elif warnings > 0:
            print("\n🟡 OVERALL: APPROVED WITH WARNINGS")
            print("   Review warnings and create tickets for improvements")
            return "WARN"
        else:
            print("\n✅ OVERALL: APPROVED")
            print("   All checks passed - ready to merge/deploy")
            return "PASS"

    def generate_markdown_report(self, output_path: Path):
        """Generate markdown audit report"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        # Determine overall status
        overall_status = "PASS"
        if any(r.status == "FAIL" for results in self.all_results.values() for r in results):
            overall_status = "FAIL"
        elif any(r.status == "WARN" for results in self.all_results.values() for r in results):
            overall_status = "WARN"

        status_emoji = {"PASS": "✅", "WARN": "🟡", "FAIL": "🔴"}

        report = f"""# POST-PHASE AUDIT REPORT

**Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration.total_seconds():.1f} seconds
**Project:** GESTIMA

---

## EXECUTIVE SUMMARY

**Overall Status:** {status_emoji[overall_status]} {overall_status}

**Summary:**
"""

        # Count totals
        total_checks = sum(len(results) for results in self.all_results.values())
        passed = sum(1 for results in self.all_results.values() for r in results if r.status == "PASS")
        warnings = sum(1 for results in self.all_results.values() for r in results if r.status == "WARN")
        failures = sum(1 for results in self.all_results.values() for r in results if r.status == "FAIL")

        report += f"""
- Total Checks: {total_checks}
- ✅ Passed: {passed}
- 🟡 Warnings: {warnings}
- 🔴 Failed: {failures}

---

## DETAILED RESULTS

"""

        # Add each section
        section_titles = {
            "code_quality": "1️⃣ Code Quality",
            "tests": "2️⃣ Test Coverage",
            "security": "3️⃣ Security",
            "performance": "4️⃣ Performance",
            "database": "5️⃣ Database",
            "dependencies": "6️⃣ Dependencies"
        }

        for section_name, results in self.all_results.items():
            title = section_titles.get(section_name, section_name.title())
            report += f"### {title}\n\n"

            for result in results:
                emoji = status_emoji.get(result.status, "❓")
                report += f"**{emoji} {result.name}:** {result.status}\n"
                report += f"- {result.message}\n"

                if result.details:
                    report += f"- Details:\n"
                    for detail in result.details[:5]:
                        report += f"  - {detail}\n"
                    if len(result.details) > 5:
                        report += f"  - ... and {len(result.details) - 5} more\n"

                report += "\n"

        # Add critical issues section
        critical_issues = []
        for results in self.all_results.values():
            for result in results:
                if result.status == "FAIL":
                    critical_issues.append(f"- **{result.name}**: {result.message}")

        if critical_issues:
            report += "---\n\n## 🔴 CRITICAL ISSUES (BLOCKING)\n\n"
            report += "\n".join(critical_issues)
            report += "\n\n"

        # Add warnings section
        warning_issues = []
        for results in self.all_results.values():
            for result in results:
                if result.status == "WARN":
                    warning_issues.append(f"- **{result.name}**: {result.message}")

        if warning_issues:
            report += "---\n\n## 🟡 WARNINGS (RECOMMENDED)\n\n"
            report += "\n".join(warning_issues)
            report += "\n\n"

        # Next steps
        report += """---

## NEXT STEPS

"""
        if failures > 0:
            report += "- [ ] Fix all critical issues\n"
            report += "- [ ] Re-run audit\n"
        if warnings > 0:
            report += "- [ ] Create tickets for warnings\n"
            report += "- [ ] Plan improvements\n"
        if failures == 0 and warnings == 0:
            report += "- [x] All checks passed ✅\n"
            report += "- [ ] Proceed with merge/deploy\n"

        report += f"""
---

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tool:** GESTIMA Post-Phase Audit v1.0
"""

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)

        print(f"\n📄 Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="GESTIMA Full Post-Phase Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Run only critical (blocking) checks"
    )

    parser.add_argument(
        "--sections",
        type=str,
        help="Comma-separated list of sections to run (e.g., code-quality,security,tests)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output report file path (markdown)"
    )

    args = parser.parse_args()

    runner = FullAuditRunner()

    # Determine which sections to run
    sections = None
    if args.sections:
        sections = [s.strip() for s in args.sections.split(',')]

    # Run audits
    runner.run_all_audits(sections=sections)

    # Print summary
    overall_status = runner.print_consolidated_summary()

    # Generate report if requested
    if args.output:
        output_path = Path(args.output)
        runner.generate_markdown_report(output_path)

    # Exit with appropriate code
    if overall_status == "FAIL":
        sys.exit(1)
    elif overall_status == "WARN":
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
