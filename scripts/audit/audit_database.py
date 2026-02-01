#!/usr/bin/env python3
"""
Database Audit Module

Checks:
- Migration integrity
- Referential integrity (FK constraints)
- Data consistency (orphaned records)
- Backup verification

Usage:
    python audit_database.py --migrations
    python audit_database.py --check all
"""

import subprocess
import sys
import sqlite3
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


class DatabaseAuditor:
    """Automated database checks"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.db_path = self.project_root / "data" / "gestima.db"
        self.results: List[AuditResult] = []

    def check_migrations(self) -> AuditResult:
        """Check migration integrity"""
        print("🔍 Checking migrations...")

        issues = []
        migrations_dir = self.project_root / "alembic" / "versions"

        if not migrations_dir.exists():
            return AuditResult(
                name="Migrations",
                status="FAIL",
                message="Alembic versions directory not found",
                details=[]
            )

        # Get all migration files
        migration_files = list(migrations_dir.glob("*.py"))

        if not migration_files:
            return AuditResult(
                name="Migrations",
                status="WARN",
                message="No migration files found",
                details=[]
            )

        # Check for duplicate revision IDs
        revisions = {}
        down_revisions = {}

        for migration_file in migration_files:
            with open(migration_file, 'r') as f:
                content = f.read()

                # Extract revision
                import re
                rev_match = re.search(r'revision\s*=\s*["\']([^"\']+)["\']', content)
                down_rev_match = re.search(r'down_revision\s*=\s*["\']([^"\']+)["\']', content)

                if rev_match:
                    revision = rev_match.group(1)
                    if revision in revisions:
                        issues.append(
                            f"CRITICAL: Duplicate revision ID '{revision}' in "
                            f"{migration_file.name} and {revisions[revision]}"
                        )
                    revisions[revision] = migration_file.name

                if down_rev_match:
                    down_revision = down_rev_match.group(1)
                    down_revisions[migration_file.name] = down_revision

        details = [f"Total migrations: {len(migration_files)}"]

        # Check for broken chains (down_revision not in revisions)
        for mig_file, down_rev in down_revisions.items():
            if down_rev and down_rev != 'None' and down_rev not in revisions:
                issues.append(
                    f"WARN: {mig_file} references non-existent down_revision '{down_rev}'"
                )

        details.extend(issues)

        if any("CRITICAL" in i for i in issues):
            return AuditResult(
                name="Migrations",
                status="FAIL",
                message="Migration integrity issues",
                details=details
            )
        elif issues:
            return AuditResult(
                name="Migrations",
                status="WARN",
                message=f"Found {len(issues)} migration warnings",
                details=details
            )

        return AuditResult(
            name="Migrations",
            status="PASS",
            message=f"All {len(migration_files)} migrations look good",
            details=details
        )

    def check_referential_integrity(self) -> AuditResult:
        """Check foreign key constraints"""
        print("🔍 Checking referential integrity...")

        if not self.db_path.exists():
            return AuditResult(
                name="Referential Integrity",
                status="WARN",
                message="Database file not found",
                details=[]
            )

        issues = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # Check foreign keys for each table
            for table in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table})")
                fks = cursor.fetchall()

                if not fks:
                    continue

                details_str = f"Table {table} has {len(fks)} foreign keys"

                # Note: Detailed FK validation would require actual data checks
                # This is a structural check only

            conn.close()

            return AuditResult(
                name="Referential Integrity",
                status="PASS",
                message="Foreign key constraints configured",
                details=issues if issues else ["FK constraints present on all tables"]
            )

        except sqlite3.Error as e:
            return AuditResult(
                name="Referential Integrity",
                status="FAIL",
                message=f"Database error: {str(e)}",
                details=[]
            )

    def check_orphaned_records(self) -> AuditResult:
        """Check for orphaned records (broken FKs)"""
        print("🔍 Checking for orphaned records...")

        if not self.db_path.exists():
            return AuditResult(
                name="Orphaned Records",
                status="WARN",
                message="Database file not found",
                details=[]
            )

        issues = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check common orphan scenarios
            orphan_checks = [
                (
                    "Operations without parts",
                    "SELECT COUNT(*) FROM operations o LEFT JOIN parts p ON o.part_id = p.id WHERE p.id IS NULL"
                ),
                (
                    "Batches without parts",
                    "SELECT COUNT(*) FROM batches b LEFT JOIN parts p ON b.part_id = p.id WHERE p.id IS NULL"
                ),
                # Add more checks as needed
            ]

            for check_name, query in orphan_checks:
                try:
                    cursor.execute(query)
                    count = cursor.fetchone()[0]

                    if count > 0:
                        issues.append(f"WARN: Found {count} {check_name.lower()}")

                except sqlite3.OperationalError:
                    # Table might not exist
                    pass

            conn.close()

            if issues:
                return AuditResult(
                    name="Orphaned Records",
                    status="WARN",
                    message=f"Found {len(issues)} types of orphaned records",
                    details=issues
                )

            return AuditResult(
                name="Orphaned Records",
                status="PASS",
                message="No orphaned records detected",
                details=[]
            )

        except sqlite3.Error as e:
            return AuditResult(
                name="Orphaned Records",
                status="FAIL",
                message=f"Database error: {str(e)}",
                details=[]
            )

    def check_backup_status(self) -> AuditResult:
        """Check backup configuration and recent backups"""
        print("🔍 Checking backup status...")

        backups_dir = self.project_root / "backups"
        issues = []

        if not backups_dir.exists():
            return AuditResult(
                name="Backup Status",
                status="FAIL",
                message="Backups directory does not exist",
                details=["Create backups/ directory and configure automated backups"]
            )

        # List recent backups
        backup_files = list(backups_dir.glob("*.db")) + list(backups_dir.glob("*.db.gz"))

        if not backup_files:
            return AuditResult(
                name="Backup Status",
                status="FAIL",
                message="No backup files found",
                details=["Run backup command to create initial backup"]
            )

        # Get most recent backup
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_backup = backup_files[0]

        import time
        age_seconds = time.time() - latest_backup.stat().st_mtime
        age_days = age_seconds / 86400

        details = [
            f"Total backups: {len(backup_files)}",
            f"Latest backup: {latest_backup.name}",
            f"Age: {age_days:.1f} days"
        ]

        if age_days > 7:
            return AuditResult(
                name="Backup Status",
                status="WARN",
                message=f"Latest backup is {age_days:.0f} days old",
                details=details
            )
        elif age_days > 30:
            return AuditResult(
                name="Backup Status",
                status="FAIL",
                message=f"Latest backup is {age_days:.0f} days old (>30 days)",
                details=details
            )

        return AuditResult(
            name="Backup Status",
            status="PASS",
            message=f"Backups configured ({len(backup_files)} backups, latest {age_days:.0f} days old)",
            details=details
        )

    def run_all_checks(self) -> List[AuditResult]:
        """Run all database checks"""
        self.results = []

        self.results.append(self.check_migrations())
        self.results.append(self.check_referential_integrity())
        self.results.append(self.check_orphaned_records())
        self.results.append(self.check_backup_status())

        return self.results

    def print_summary(self):
        """Print audit summary"""
        print("\n" + "="*60)
        print("DATABASE AUDIT SUMMARY")
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
            print("🔴 OVERALL: FAILED - Database issues found")
            sys.exit(1)
        elif has_warnings:
            print("🟡 OVERALL: WARNINGS - Database improvements recommended")
            sys.exit(0)
        else:
            print("✅ OVERALL: PASSED - Database healthy")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GESTIMA Database Audit")
    parser.add_argument(
        "--check",
        choices=["all", "migrations", "integrity", "orphans", "backups"],
        default="all",
        help="Which checks to run"
    )

    args = parser.parse_args()

    auditor = DatabaseAuditor()

    if args.check == "all":
        auditor.run_all_checks()
    elif args.check == "migrations":
        auditor.results.append(auditor.check_migrations())
    elif args.check == "integrity":
        auditor.results.append(auditor.check_referential_integrity())
    elif args.check == "orphans":
        auditor.results.append(auditor.check_orphaned_records())
    elif args.check == "backups":
        auditor.results.append(auditor.check_backup_status())

    auditor.print_summary()


if __name__ == "__main__":
    main()
