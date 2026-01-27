#!/usr/bin/env python3
"""
GESTIMA - Run database migration
Spustí init_db pro aplikaci migračních změn na schema
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db


async def main():
    print("🔧 Spouštím databázovou migraci...")
    await init_db()
    print("✅ Migrace dokončena")


if __name__ == "__main__":
    asyncio.run(main())
