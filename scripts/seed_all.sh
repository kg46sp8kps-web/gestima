#!/bin/bash
# GESTIMA - Seed všechna data (bez parts a materiálů)
# Použití: bash scripts/seed_all.sh

set -e
cd "$(dirname "$0")/.."

echo "🌱 GESTIMA seed start"

python3 scripts/seed_config.py
python3 scripts/seed_material_groups.py
python3 scripts/seed_material_norms_complete.py
python3 scripts/seed_price_categories.py
python3 scripts/seed_price_tiers.py
python3 scripts/seed_work_centers.py

python3 -c "
import asyncio
from sqlalchemy import text
from app.database import async_session
from app.services.auth_service import get_password_hash

async def main():
    async with async_session() as db:
        result = await db.execute(text('SELECT COUNT(*) FROM users'))
        if result.scalar() > 0:
            print('  ⏭️  Users: již existují')
            return
        for username, password, role in [
            ('admin', 'admin123', 'ADMIN'),
            ('operator', 'operator123', 'OPERATOR'),
        ]:
            hashed = get_password_hash(password)
            await db.execute(text('''
                INSERT INTO users (username, email, hashed_password, role, is_active, created_by, updated_by, version, created_at, updated_at)
                VALUES (:u, :e, :h, :r, 1, \"system\", \"system\", 1, datetime(\"now\"), datetime(\"now\"))
            '''), {'u': username, 'e': f'{username}@gestima.local', 'h': hashed, 'r': role})
        await db.commit()
        print('  ✅ Users: admin/admin123, operator/operator123')

asyncio.run(main())
" 2>&1 | grep -v "trapped\|bcrypt\|Traceback\|^\s*\^"

echo "✅ Seed hotov"
