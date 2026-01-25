#!/usr/bin/env python3
"""
GESTIMA - CLI helper pro spouštění a správu aplikace
Použití: python3 gestima.py [command]
"""

import os
import sys
import subprocess
import getpass
import asyncio
from pathlib import Path

# Get project directory
PROJECT_DIR = Path(__file__).parent
VENV_DIR = PROJECT_DIR / "venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
VENV_PIP = VENV_DIR / "bin" / "pip"

class Gestima:
    """CLI helper pro GESTIMA"""

    @staticmethod
    def check_venv() -> bool:
        """Zkontroluj, že venv existuje a je aktivní"""
        if not VENV_DIR.exists():
            print("❌ Virtual environment not found. Run: python3 gestima.py setup")
            return False
        return True

    @staticmethod
    def setup():
        """Inicializuj venv a instaluj dependencies"""
        print("📦 GESTIMA Setup")
        print("")

        # Vytvoř venv
        if not VENV_DIR.exists():
            print("✓ Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        else:
            print("✓ Virtual environment already exists")

        # Upgrade pip
        print("✓ Upgrading pip...")
        subprocess.run([str(VENV_PIP), "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)

        # Instaluj dependencies
        print("✓ Installing dependencies...")
        requirements = PROJECT_DIR / "requirements.txt"
        subprocess.run([str(VENV_PIP), "install", "-r", str(requirements)], check=True)

        print("")
        print("✅ Setup complete!")
        print("")
        print("Next steps:")
        print("  python3 gestima.py run")
        print("")

    @staticmethod
    def run():
        """Spusť aplikaci"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🚀 GESTIMA 1.0 - Starting...")
        print("📍 URL: http://localhost:8000")
        print("📊 API Docs: http://localhost:8000/docs")
        print("")
        print("Press CTRL+C to stop")
        print("")

        os.chdir(PROJECT_DIR)
        subprocess.run([
            str(VENV_PYTHON), "-m", "uvicorn",
            "app.gestima_app:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])

    @staticmethod
    def test(*args):
        """Spusť testy"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🧪 Running tests...")
        print("")

        os.chdir(PROJECT_DIR)
        test_args = list(args) if args else []
        subprocess.run([str(VENV_PYTHON), "-m", "pytest", "-v"] + test_args)

    @staticmethod
    def test_critical():
        """Spusť pouze kritické testy"""
        print("🧪 Running critical tests...")
        print("")
        Gestima.test("-m", "critical")

    @staticmethod
    def shell():
        """Aktivuj interactive shell s venv"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🐚 GESTIMA Interactive Shell")
        print("Type 'exit()' to quit")
        print("")

        os.chdir(PROJECT_DIR)
        subprocess.run([str(VENV_PYTHON)])

    @staticmethod
    def create_admin():
        """Vytvoř prvního admin uživatele"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("👤 GESTIMA - Create Admin User")
        print("")

        # Input username
        username = input("Username: ").strip()
        if not username or len(username) < 3:
            print("❌ Username must be at least 3 characters")
            sys.exit(1)

        # Input password (hidden)
        password = getpass.getpass("Password (min 8 chars): ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            sys.exit(1)

        # Confirm password
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            sys.exit(1)

        print("")
        print("Creating admin user...")

        # Run async function
        os.chdir(PROJECT_DIR)
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            f"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.auth_service import create_user
from app.models import UserRole

async def _create_admin():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            user = await create_user(
                db=db,
                username='{username}',
                password='{password}',
                role=UserRole.ADMIN
            )
            print(f"✅ Admin user created: {{user.username}}")
        except Exception as e:
            print(f"❌ Error: {{e}}")
            raise

asyncio.run(_create_admin())
"""
        ])

        if result.returncode == 0:
            print("")
            print("You can now login at: http://localhost:8000")
        else:
            sys.exit(1)

    @staticmethod
    def backup():
        """Vytvoř zálohu databáze"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("💾 GESTIMA - Backup Database")
        print("")

        os.chdir(PROJECT_DIR)
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            """
from app.services.backup_service import create_backup, list_backups

backup_path = create_backup()
print(f"✅ Backup created: {backup_path}")
print("")
print("Available backups:")
for b in list_backups():
    print(f"  {b['name']} ({b['size_mb']} MB) - {b['created_at']}")
"""
        ])

        if result.returncode != 0:
            sys.exit(1)

    @staticmethod
    def seed_demo():
        """Vytvoř demo data (parts)"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🌱 GESTIMA - Seed Demo Data")
        print("")

        os.chdir(PROJECT_DIR)
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            """
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.seed_data import seed_demo_parts

async def _seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        await seed_demo_parts(db)
        print("✅ Demo data created")

asyncio.run(_seed())
"""
        ])

        if result.returncode != 0:
            sys.exit(1)

    @staticmethod
    def clean_demo():
        """Smaž všechny demo data (parts s notes obsahující 'DEMO')"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🧹 GESTIMA - Clean Demo Data")
        print("")

        os.chdir(PROJECT_DIR)
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            """
import asyncio
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.part import Part

async def _clean():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(
            select(Part).where(Part.notes.like('%DEMO%'))
        )
        demo_parts = result.scalars().all()

        if not demo_parts:
            print("No demo data found.")
            return

        print(f"Found {len(demo_parts)} demo parts:")
        for part in demo_parts:
            print(f"  - {part.part_number} ({part.name})")

        for part in demo_parts:
            await db.delete(part)

        await db.commit()
        print(f"\\n✅ Deleted {len(demo_parts)} demo parts")

asyncio.run(_clean())
"""
        ])

        if result.returncode != 0:
            sys.exit(1)

    @staticmethod
    def backup_list():
        """Zobraz dostupné zálohy"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("💾 GESTIMA - Available Backups")
        print("")

        os.chdir(PROJECT_DIR)
        subprocess.run([
            str(VENV_PYTHON), "-c",
            """
from app.services.backup_service import list_backups

backups = list_backups()
if not backups:
    print("No backups found.")
else:
    for b in backups:
        print(f"  {b['name']} ({b['size_mb']} MB) - {b['created_at']}")
"""
        ])

    @staticmethod
    def backup_restore(backup_name: str):
        """Obnov databázi ze zálohy"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("💾 GESTIMA - Restore Database")
        print("")
        print(f"⚠️  WARNING: This will OVERWRITE the current database!")
        print(f"   Restoring from: {backup_name}")
        print("")

        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("❌ Restore cancelled")
            sys.exit(1)

        os.chdir(PROJECT_DIR)
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            f"""
from pathlib import Path
from app.config import settings
from app.services.backup_service import restore_backup

backup_path = settings.BASE_DIR / "backups" / "{backup_name}"
if not backup_path.exists():
    print(f"❌ Backup not found: {{backup_path}}")
    exit(1)

restore_backup(backup_path)
print("✅ Database restored successfully!")
print("")
print("⚠️  Restart the application to apply changes.")
"""
        ])

        if result.returncode != 0:
            sys.exit(1)

    @staticmethod
    def help():
        """Zobraz dostupné příkazy"""
        print("GESTIMA 1.1 - CLI Helper")
        print("")
        print("Usage: python3 gestima.py [command]")
        print("")
        print("Commands:")
        print("  setup           Inicializuj venv a instaluj dependencies")
        print("  run             Spusť aplikaci (http://localhost:8000)")
        print("  create-admin    Vytvoř admin uživatele (username + password)")
        print("  seed-demo       Vytvoř demo data (3 vzorové díly)")
        print("  clean-demo      Smaž všechny demo data")
        print("  backup          Vytvoř zálohu databáze")
        print("  backup-list     Zobraz dostupné zálohy")
        print("  backup-restore  Obnov databázi ze zálohy")
        print("  test            Spusť všechny testy")
        print("  test-critical   Spusť pouze kritické testy")
        print("  shell           Interactive Python shell s venv")
        print("  help            Zobraz tuto zprávu")
        print("")
        print("Examples:")
        print("  python3 gestima.py setup")
        print("  python3 gestima.py create-admin")
        print("  python3 gestima.py run")
        print("  python3 gestima.py seed-demo          # Vytvoří DEMO-001, DEMO-002, DEMO-003")
        print("  python3 gestima.py clean-demo         # Smaže všechny DEMO díly")
        print("  python3 gestima.py backup")
        print("  python3 gestima.py backup-restore gestima_backup_20260123_120000.db.gz")
        print("  python3 gestima.py test -k 'test_pricing'")
        print("")

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        Gestima.help()
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "setup":
        Gestima.setup()
    elif command == "run":
        Gestima.run()
    elif command == "create-admin":
        Gestima.create_admin()
    elif command == "seed-demo":
        Gestima.seed_demo()
    elif command == "clean-demo":
        Gestima.clean_demo()
    elif command == "backup":
        Gestima.backup()
    elif command == "backup-list":
        Gestima.backup_list()
    elif command == "backup-restore":
        if not args:
            print("❌ Usage: python3 gestima.py backup-restore <backup_name>")
            sys.exit(1)
        Gestima.backup_restore(args[0])
    elif command == "test":
        Gestima.test(*args)
    elif command == "test-critical":
        Gestima.test_critical()
    elif command == "shell":
        Gestima.shell()
    elif command == "help" or command == "-h" or command == "--help":
        Gestima.help()
    else:
        print(f"❌ Unknown command: {command}")
        print("")
        Gestima.help()
        sys.exit(1)

if __name__ == "__main__":
    main()
