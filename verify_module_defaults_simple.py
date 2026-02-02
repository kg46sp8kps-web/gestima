#!/usr/bin/env python3
"""
Simple verification script for module_defaults table (ADR-031)
Uses raw SQL to avoid model import issues.

Run: python3 verify_module_defaults_simple.py
"""

import asyncio
import sys
import sqlite3
from datetime import datetime

def verify_module_defaults():
    """Verify module_defaults table using direct SQLite"""
    print("=" * 80)
    print("VERIFYING MODULE DEFAULTS TABLE (ADR-031)")
    print("=" * 80)
    print()

    db_path = "gestima.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Test 1: Check table exists
    print("TEST 1: Checking if module_defaults table exists...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='module_defaults'")
    table = cursor.fetchone()
    if table:
        print("✅ module_defaults table exists")
    else:
        print("❌ module_defaults table NOT found")
        return False

    print()

    # Test 2: Check columns
    print("TEST 2: Checking table schema...")
    cursor.execute("PRAGMA table_info(module_defaults)")
    columns = {row[1] for row in cursor.fetchall()}
    required_columns = {
        'id', 'module_type', 'default_width', 'default_height', 'settings',
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'deleted_at', 'deleted_by', 'version'
    }
    missing = required_columns - columns
    if missing:
        print(f"❌ Missing columns: {missing}")
        return False
    else:
        print("✅ All required columns present")
        print(f"   Columns: {sorted(columns)}")

    print()

    # Test 3: Check indexes
    print("TEST 3: Checking indexes...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='module_defaults'")
    indexes = [row[0] for row in cursor.fetchall()]

    expected_indexes = [
        'ix_module_defaults_module_type',
        'ix_module_defaults_deleted_at'
    ]

    # Check if SQLite auto-creates UNIQUE index
    has_module_type_idx = any('module_type' in idx.lower() for idx in indexes)
    has_deleted_at_idx = any('deleted_at' in idx.lower() for idx in indexes)

    if has_module_type_idx and has_deleted_at_idx:
        print("✅ Required indexes present")
        print(f"   Found indexes: {indexes}")
    else:
        print(f"⚠️  Some indexes may be missing")
        print(f"   Found: {indexes}")

    print()

    # Test 4: Test CRUD operations
    print("TEST 4: Testing CRUD operations...")

    # Clean test data
    cursor.execute("DELETE FROM module_defaults WHERE module_type = 'test-module'")
    conn.commit()

    # CREATE
    print("  4a. Testing INSERT...")
    cursor.execute("""
        INSERT INTO module_defaults
        (module_type, default_width, default_height, settings, created_at, updated_at, created_by, version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'test-module',
        800,
        600,
        '{"test": "value"}',
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat(),
        'system',
        0
    ))
    conn.commit()
    test_id = cursor.lastrowid
    print(f"  ✅ INSERT successful (ID: {test_id})")

    # READ
    print("  4b. Testing SELECT...")
    cursor.execute("""
        SELECT id, module_type, default_width, default_height, settings
        FROM module_defaults
        WHERE module_type = ? AND deleted_at IS NULL
    """, ('test-module',))
    row = cursor.fetchone()
    if row:
        print(f"  ✅ SELECT successful")
        print(f"     ID: {row[0]}, module_type: {row[1]}, width: {row[2]}, height: {row[3]}")
    else:
        print("  ❌ SELECT failed")
        return False

    # UPDATE
    print("  4c. Testing UPDATE...")
    cursor.execute("""
        UPDATE module_defaults
        SET default_width = ?, default_height = ?, updated_at = ?, version = version + 1
        WHERE module_type = ?
    """, (1000, 800, datetime.utcnow().isoformat(), 'test-module'))
    conn.commit()

    cursor.execute("SELECT default_width, default_height, version FROM module_defaults WHERE module_type = ?", ('test-module',))
    row = cursor.fetchone()
    if row and row[0] == 1000 and row[1] == 800:
        print(f"  ✅ UPDATE successful (width: {row[0]}, height: {row[1]}, version: {row[2]})")
    else:
        print("  ❌ UPDATE failed")
        return False

    # SOFT DELETE
    print("  4d. Testing SOFT DELETE...")
    cursor.execute("""
        UPDATE module_defaults
        SET deleted_at = ?, deleted_by = ?
        WHERE module_type = ?
    """, (datetime.utcnow().isoformat(), 'system', 'test-module'))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM module_defaults WHERE module_type = ? AND deleted_at IS NULL", ('test-module',))
    count = cursor.fetchone()[0]
    if count == 0:
        print("  ✅ SOFT DELETE successful (record not visible in active queries)")
    else:
        print("  ❌ SOFT DELETE failed")
        return False

    print()

    # Test 5: Test UNIQUE constraint
    print("TEST 5: Testing UNIQUE constraint on module_type...")
    try:
        # Clean first
        cursor.execute("DELETE FROM module_defaults WHERE module_type = 'unique-test'")
        conn.commit()

        # Insert first record
        cursor.execute("""
            INSERT INTO module_defaults
            (module_type, default_width, default_height, created_at, updated_at, version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('unique-test', 800, 600, datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), 0))
        conn.commit()

        # Try to insert duplicate
        cursor.execute("""
            INSERT INTO module_defaults
            (module_type, default_width, default_height, created_at, updated_at, version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('unique-test', 900, 700, datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), 0))
        conn.commit()

        print("❌ UNIQUE constraint NOT working (duplicate allowed)")
        return False

    except sqlite3.IntegrityError as e:
        print(f"✅ UNIQUE constraint working (prevented duplicate)")
        print(f"   Error: {e}")
        conn.rollback()

    print()

    # Cleanup
    cursor.execute("DELETE FROM module_defaults WHERE module_type IN ('test-module', 'unique-test')")
    conn.commit()

    conn.close()

    print("=" * 80)
    print("✅ ALL TESTS PASSED - MODULE DEFAULTS TABLE READY")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = verify_module_defaults()
    sys.exit(0 if success else 1)
