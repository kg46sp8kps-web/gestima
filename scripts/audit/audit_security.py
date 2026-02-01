#!/usr/bin/env python3
"""
Security Audit Module

Checks:
- OWASP Top 10 compliance
- Dependency vulnerabilities
- Input validation (Pydantic)
- Authentication & authorization

Usage:
    python audit_security.py --owasp
    python audit_security.py --check all
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


class SecurityAuditor:
    """Automated security checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: List[AuditResult] = []

    def check_hardcoded_secrets(self) -> AuditResult:
        """Check for hardcoded secrets (OWASP A02)"""
        print("🔍 Checking for hardcoded secrets...")

        issues = []
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'password'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'API key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'secret'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'token'),
        ]

        for pattern, secret_type in patterns:
            cmd = [
                "grep", "-ri", pattern,
                str(self.project_root / "app"),
                str(self.project_root / "config"),
                "--include=*.py"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                matches = result.stdout.strip().split('\n')
                # Filter out comments and test files
                real_matches = [
                    m for m in matches
                    if not m.strip().startswith('#') and 'test' not in m.lower()
                ]

                if real_matches:
                    issues.append(
                        f"CRITICAL: Found {len(real_matches)} hardcoded {secret_type} "
                        f"(OWASP A02 - use environment variables)"
                    )

        if issues:
            return AuditResult(
                name="Hardcoded Secrets",
                status="FAIL",
                message=f"Found {len(issues)} types of hardcoded secrets",
                details=issues
            )

        return AuditResult(
            name="Hardcoded Secrets",
            status="PASS",
            message="No hardcoded secrets detected"
        )

    def check_sql_injection(self) -> AuditResult:
        """Check for SQL injection vectors (OWASP A03)"""
        print("🔍 Checking for SQL injection vectors...")

        issues = []

        # Look for raw SQL execute calls
        cmd = [
            "grep", "-r", r"execute.*SELECT\|execute.*INSERT\|execute.*UPDATE\|execute.*DELETE",
            str(self.project_root / "app"),
            "--include=*.py"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            # Check if parameterized (contains ? or %(name)s)
            for match in matches:
                if '?' not in match and '%(' not in match:
                    issues.append(
                        f"WARN: Possible raw SQL without parameterization - {match[:100]}"
                    )

        if issues:
            return AuditResult(
                name="SQL Injection",
                status="WARN",
                message=f"Found {len(issues)} potential SQL injection vectors",
                details=issues[:5]
            )

        return AuditResult(
            name="SQL Injection",
            status="PASS",
            message="No SQL injection vectors (using ORM)"
        )

    def check_xss_vectors(self) -> AuditResult:
        """Check for XSS vectors (OWASP A03)"""
        print("🔍 Checking for XSS vectors...")

        issues = []

        # Check for v-html usage (potential XSS)
        cmd = [
            "grep", "-r", "v-html",
            str(self.project_root / "frontend/src"),
            "--include=*.vue"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            matches = result.stdout.strip().split('\n')
            issues.append(
                f"WARN: Found {len(matches)} v-html usages - ensure user input is sanitized"
            )
            issues.extend(matches[:5])

        if issues:
            return AuditResult(
                name="XSS Vectors",
                status="WARN",
                message=f"Found {len(issues)} potential XSS vectors",
                details=issues
            )

        return AuditResult(
            name="XSS Vectors",
            status="PASS",
            message="No XSS vectors detected"
        )

    def check_security_headers(self) -> AuditResult:
        """Check for security headers (OWASP A05)"""
        print("🔍 Checking security headers configuration...")

        issues = []
        app_file = self.project_root / "app" / "gestima_app.py"

        if not app_file.exists():
            return AuditResult(
                name="Security Headers",
                status="WARN",
                message="gestima_app.py not found",
                details=[]
            )

        with open(app_file, 'r') as f:
            content = f.read()

            required_headers = [
                ('Content-Security-Policy', 'CSP'),
                ('Strict-Transport-Security', 'HSTS'),
                ('X-Content-Type-Options', 'X-Content-Type-Options'),
            ]

            for header, name in required_headers:
                if header not in content:
                    issues.append(
                        f"CRITICAL: Missing {name} header (OWASP A05 - security misconfiguration)"
                    )

        if issues:
            return AuditResult(
                name="Security Headers",
                status="FAIL",
                message=f"Missing {len(issues)} security headers",
                details=issues
            )

        return AuditResult(
            name="Security Headers",
            status="PASS",
            message="All required security headers configured"
        )

    def check_input_validation(self) -> AuditResult:
        """Check Pydantic validation usage (L-009)"""
        print("🔍 Checking input validation...")

        issues = []
        models_dir = self.project_root / "app" / "models"

        if not models_dir.exists():
            return AuditResult(
                name="Input Validation",
                status="WARN",
                message="Models directory not found",
                details=[]
            )

        # Find BaseModel classes without Field() validations
        for model_file in models_dir.glob("*.py"):
            with open(model_file, 'r') as f:
                content = f.read()

                # Find BaseModel classes
                if 'BaseModel' in content:
                    # Simple heuristic: count field definitions vs Field() usage
                    field_defs = re.findall(r'^\s+\w+:\s*(?:int|str|float)', content, re.MULTILINE)
                    field_validations = re.findall(r'Field\(', content)

                    if len(field_defs) > len(field_validations) * 2:
                        issues.append(
                            f"WARN: {model_file.name} has many fields without Field() validation (L-009)"
                        )

        if issues:
            return AuditResult(
                name="Input Validation",
                status="WARN",
                message=f"Found {len(issues)} models with insufficient validation",
                details=issues
            )

        return AuditResult(
            name="Input Validation",
            status="PASS",
            message="Input validation appears adequate"
        )

    def check_dependencies_vulnerabilities(self) -> AuditResult:
        """Check for vulnerable dependencies (OWASP A06)"""
        print("🔍 Checking dependency vulnerabilities...")

        issues = []

        # Check Python dependencies with safety
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Parse JSON output
                import json
                try:
                    vulns = json.loads(result.stdout)
                    critical = [v for v in vulns if v.get('severity', '').lower() == 'critical']
                    high = [v for v in vulns if v.get('severity', '').lower() == 'high']

                    if critical:
                        issues.append(f"CRITICAL: {len(critical)} CRITICAL vulnerabilities in Python dependencies")
                    if high:
                        issues.append(f"WARN: {len(high)} HIGH vulnerabilities in Python dependencies")

                except json.JSONDecodeError:
                    issues.append("WARN: Could not parse safety check output")

        except (subprocess.TimeoutExpired, FileNotFoundError):
            issues.append("INFO: safety not installed - skipping Python dependency check")

        # Check npm dependencies
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            try:
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                import json
                try:
                    audit = json.loads(result.stdout)
                    vulnerabilities = audit.get('metadata', {}).get('vulnerabilities', {})

                    critical = vulnerabilities.get('critical', 0)
                    high = vulnerabilities.get('high', 0)

                    if critical > 0:
                        issues.append(f"CRITICAL: {critical} CRITICAL vulnerabilities in npm dependencies")
                    if high > 0:
                        issues.append(f"WARN: {high} HIGH vulnerabilities in npm dependencies")

                except json.JSONDecodeError:
                    pass

            except (subprocess.TimeoutExpired, FileNotFoundError):
                issues.append("INFO: npm not available - skipping frontend dependency check")

        if any("CRITICAL" in i for i in issues):
            return AuditResult(
                name="Dependency Vulnerabilities",
                status="FAIL",
                message=f"Found CRITICAL vulnerabilities",
                details=issues
            )
        elif issues:
            return AuditResult(
                name="Dependency Vulnerabilities",
                status="WARN",
                message=f"Found {len(issues)} dependency issues",
                details=issues
            )

        return AuditResult(
            name="Dependency Vulnerabilities",
            status="PASS",
            message="No known vulnerabilities in dependencies"
        )

    def check_authentication(self) -> AuditResult:
        """Check authentication implementation"""
        print("🔍 Checking authentication setup...")

        issues = []
        auth_file = self.project_root / "app" / "routers" / "auth_router.py"

        if not auth_file.exists():
            return AuditResult(
                name="Authentication",
                status="FAIL",
                message="auth_router.py not found",
                details=[]
            )

        with open(auth_file, 'r') as f:
            content = f.read()

            # Check for password hashing
            if 'hash' not in content.lower() and 'bcrypt' not in content.lower():
                issues.append("CRITICAL: No password hashing detected")

            # Check for JWT/cookie usage
            if 'jwt' not in content.lower() and 'cookie' not in content.lower():
                issues.append("CRITICAL: No JWT or cookie-based auth detected")

            # Check for HttpOnly cookies (ADR-005)
            if 'httponly' not in content.lower():
                issues.append("WARN: HttpOnly cookie flag not explicitly set")

        if any("CRITICAL" in i for i in issues):
            return AuditResult(
                name="Authentication",
                status="FAIL",
                message="Critical authentication issues",
                details=issues
            )
        elif issues:
            return AuditResult(
                name="Authentication",
                status="WARN",
                message=f"Found {len(issues)} auth issues",
                details=issues
            )

        return AuditResult(
            name="Authentication",
            status="PASS",
            message="Authentication setup looks good"
        )

    def run_all_checks(self) -> List[AuditResult]:
        """Run all security checks"""
        self.results = []

        self.results.append(self.check_hardcoded_secrets())
        self.results.append(self.check_sql_injection())
        self.results.append(self.check_xss_vectors())
        self.results.append(self.check_security_headers())
        self.results.append(self.check_input_validation())
        self.results.append(self.check_dependencies_vulnerabilities())
        self.results.append(self.check_authentication())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("SECURITY AUDIT SUMMARY")
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
            print("🔴 OVERALL: FAILED - Critical security issues found")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Security improvements recommended")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - No security issues detected")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Security Audit")
    parser.add_argument(
        "--check",
        choices=["all", "owasp", "secrets", "deps", "auth"],
        default="all",
        help="Which checks to run"
    )

    args = parser.parse_args()

    auditor = SecurityAuditor()

    if args.check == "all" or args.check == "owasp":
        auditor.run_all_checks()
    elif args.check == "secrets":
        auditor.results.append(auditor.check_hardcoded_secrets())
    elif args.check == "deps":
        auditor.results.append(auditor.check_dependencies_vulnerabilities())
    elif args.check == "auth":
        auditor.results.append(auditor.check_authentication())

    auditor.print_summary()


if __name__ == "__main__":
    main()
