#!/usr/bin/env python3
"""
Migration script: Replace emoji icons with string identifiers in operations table

This script updates all existing operations that have emoji in the icon field
to use proper string identifiers compatible with Lucide icons.

Emoji → String mappings:
- 🔧 → wrench (generic)
- 🔄 → rotate-cw (turning)
- ✂️ → scissors (cutting)
- 💎 → gem (grinding)
- ⚙️ → settings (milling)
- 🔩 → wrench (drilling - using wrench as fallback)
"""

import sqlite3
import sys
from pathlib import Path

# Emoji to icon string mapping
EMOJI_TO_ICON_MAP = {
    '🔧': 'wrench',
    '🔄': 'rotate-cw',
    '✂️': 'scissors',
    '💎': 'gem',
    '⚙️': 'settings',
    '🔩': 'wrench',
}

def migrate_emoji_to_icons(db_path: Path):
    """Update operations.icon from emoji to string identifiers"""

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    print(f"🔍 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM operations")
        total_ops = cursor.fetchone()[0]
        print(f"📊 Total operations: {total_ops}")

        # Count operations with emoji
        emoji_list = list(EMOJI_TO_ICON_MAP.keys())
        placeholders = ','.join(['?' for _ in emoji_list])
        cursor.execute(f"SELECT COUNT(*) FROM operations WHERE icon IN ({placeholders})", emoji_list)
        emoji_count = cursor.fetchone()[0]
        print(f"🎯 Operations with emoji: {emoji_count}")

        if emoji_count == 0:
            print("✅ No emoji found - migration not needed")
            return

        # Show sample before migration
        print("\n📋 Sample operations BEFORE migration:")
        cursor.execute("SELECT id, name, icon FROM operations WHERE icon IN ({}) LIMIT 5".format(placeholders), emoji_list)
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]} | icon='{row[2]}'")

        # Perform migration
        print(f"\n🔄 Migrating {emoji_count} operations...")
        updated_count = 0

        for emoji, icon_string in EMOJI_TO_ICON_MAP.items():
            cursor.execute(
                "UPDATE operations SET icon = ? WHERE icon = ?",
                (icon_string, emoji)
            )
            count = cursor.rowcount
            if count > 0:
                print(f"  ✓ Updated {count} operations: '{emoji}' → '{icon_string}'")
                updated_count += count

        # Commit changes
        conn.commit()
        print(f"\n✅ Migration complete! Updated {updated_count} operations")

        # Verify
        print("\n🔍 Verification:")
        cursor.execute(f"SELECT COUNT(*) FROM operations WHERE icon IN ({placeholders})", emoji_list)
        remaining_emoji = cursor.fetchone()[0]
        print(f"  Remaining emoji: {remaining_emoji}")

        # Show sample after migration
        print("\n📋 Sample operations AFTER migration:")
        cursor.execute("SELECT id, name, icon FROM operations LIMIT 5")
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]} | icon='{row[2]}'")

        if remaining_emoji > 0:
            print("\n⚠️ Warning: Some emoji still remain!")
            cursor.execute(f"SELECT DISTINCT icon FROM operations WHERE icon IN ({placeholders})", emoji_list)
            for row in cursor.fetchall():
                print(f"  - '{row[0]}'")
        else:
            print("\n🎉 All emoji successfully replaced!")

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == '__main__':
    # Database path
    project_root = Path(__file__).parent.parent
    db_path = project_root / 'gestima.db'

    print("=" * 60)
    print("GESTIMA - Emoji to Icon Migration")
    print("=" * 60)

    migrate_emoji_to_icons(db_path)
