#!/Users/lofas/miniforge3/envs/gestima-prod/bin/python
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
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Get project directory
PROJECT_DIR = Path(__file__).parent

# Use conda gestima-prod environment (has pythonocc-core)
CONDA_ENV_PYTHON = Path("/Users/lofas/miniforge3/envs/gestima-prod/bin/python")
CONDA_ENV_PIP = Path("/Users/lofas/miniforge3/envs/gestima-prod/bin/pip")

# Fallback to local venv if conda not available
VENV_DIR = PROJECT_DIR / "venv"
VENV_PYTHON = CONDA_ENV_PYTHON if CONDA_ENV_PYTHON.exists() else VENV_DIR / "bin" / "python"
VENV_PIP = CONDA_ENV_PIP if CONDA_ENV_PIP.exists() else VENV_DIR / "bin" / "pip"

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

        # Check for non-interactive mode (default credentials)
        if not sys.stdin.isatty():
            # Non-interactive mode - use defaults
            username = "admin"
            password = "asdfghjkl"
            print("📝 Non-interactive mode - using default credentials")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print("")
        else:
            # Interactive mode - ask user
            username = input("Username (default: admin): ").strip() or "admin"
            if len(username) < 3:
                print("❌ Username must be at least 3 characters")
                sys.exit(1)

            # Input password (hidden)
            password = getpass.getpass("Password (min 8 chars, default: asdfghjkl): ")
            if not password:
                password = "asdfghjkl"
            elif len(password) < 8:
                print("❌ Password must be at least 8 characters")
                sys.exit(1)

            # Confirm password if custom
            if password != "asdfghjkl":
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
        """Resetuj databázi a vytvoř kompletní demo environment"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🌱 GESTIMA - Seed Demo Environment")
        print("")
        print("⚠️  WARNING: This will RESET the database!")
        print("")

        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("❌ Seed cancelled")
            sys.exit(1)

        print("")
        print("✓ Initializing database schema...")

        os.chdir(PROJECT_DIR)

        # Init DB schema
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            """
import asyncio
from app.database import init_db

asyncio.run(init_db())
print("✅ Database schema initialized")
"""
        ])

        if result.returncode != 0:
            sys.exit(1)

        # Seed materials (V4: 8-digit codes, canonical seeds)
        print("✓ Seeding material groups (9 categories)...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_material_groups.py"
        ])
        if result.returncode != 0:
            sys.exit(1)

        print("✓ Seeding material price categories (43 categories)...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_price_categories.py"
        ])
        if result.returncode != 0:
            sys.exit(1)

        print("✓ Seeding material norms (83 conversion entries)...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_material_norms_complete.py"
        ])
        if result.returncode != 0:
            sys.exit(1)

        # Seed work centers (ADR-021: machines → work_centers)
        print("✓ Seeding work centers...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_work_centers.py"
        ])

        if result.returncode != 0:
            sys.exit(1)

        # Seed material items (concrete stock items)
        print("✓ Seeding material items (stock inventory)...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_material_items.py"
        ])

        if result.returncode != 0:
            sys.exit(1)

        # Seed demo parts
        print("✓ Seeding demo parts...")
        result = subprocess.run([
            str(VENV_PYTHON), "scripts/seed_demo_parts.py"
        ])

        if result.returncode != 0:
            sys.exit(1)

        # Create demo admin user
        print("✓ Creating demo admin user...")
        result = subprocess.run([
            str(VENV_PYTHON), "-c",
            """
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.auth_service import create_user
from app.models import UserRole

async def _create_demo_admin():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            user = await create_user(
                db=db,
                username='demo',
                password='demo123',
                role=UserRole.ADMIN
            )
            print(f"✅ Demo admin created: {user.username} / demo123")
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                print("✅ Demo admin already exists")
            else:
                raise

asyncio.run(_create_demo_admin())
"""
        ])

        print("")
        print("✅ Demo environment ready!")
        print("")
        print("Login credentials:")
        print("  Username: demo")
        print("  Password: demo123")
        print("")
        print("Run: python gestima.py run")
        print("")

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
    def restore(backup_name: str):
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

backup_path = Path("{backup_name}")
if not backup_path.exists():
    # Try in backups/ folder
    backup_path = settings.BASE_DIR / "backups" / "{backup_name}"

if not backup_path.exists():
    print(f"❌ Backup not found: {backup_name}")
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
    def deploy():
        """Deploy workflow helper (git pull + restart instructions)"""
        if not Gestima.check_venv():
            sys.exit(1)

        print("🚀 GESTIMA - Deploy Workflow")
        print("")
        print("This will pull latest code from Git and guide you through restart.")
        print("")

        # Check if in Git repo
        if not (PROJECT_DIR / ".git").exists():
            print("❌ Not a Git repository!")
            print("   Initialize Git first: git init && git remote add origin <url>")
            sys.exit(1)

        # Git pull
        print("✓ Pulling latest code from Git...")
        result = subprocess.run(["git", "pull", "origin", "main"], cwd=PROJECT_DIR)

        if result.returncode != 0:
            print("")
            print("❌ Git pull failed!")
            print("   Fix conflicts and try again.")
            sys.exit(1)

        print("")
        print("✅ Code updated successfully!")
        print("")
        print("Next steps:")
        print("")
        print("  1. Restart the application:")
        print("     - Windows Task Scheduler: schtasks /run /tn \"GESTIMA\"")
        print("     - Manual: Ctrl+C in console → python gestima.py run")
        print("")
        print("  2. Verify health check:")
        print("     curl http://localhost:8000/health")
        print("")
        print("  3. Test in browser:")
        print("     http://localhost:8000")
        print("")

    @staticmethod
    def help():
        """Zobraz dostupné příkazy"""
        print("GESTIMA 1.5 - CLI Helper")
        print("")
        print("Usage: python3 gestima.py [command]")
        print("")
        print("Commands:")
        print("  setup           Inicializuj venv a instaluj dependencies")
        print("  run             Spusť aplikaci (http://localhost:8000)")
        print("")
        print("Dev/Prod Workflow:")
        print("  seed-demo       Reset DB + seed kompletní demo environment")
        print("  deploy          Pull latest code + restart instructions")
        print("  restore <file>  Restore databázi ze zálohy")
        print("")
        print("User Management:")
        print("  create-admin    Vytvoř admin uživatele (username + password)")
        print("")
        print("Data Management:")
        print("  clean-demo      Smaž všechny demo data (parts)")
        print("  backup          Vytvoř zálohu databáze")
        print("  backup-list     Zobraz dostupné zálohy")
        print("")
        print("Testing:")
        print("  test            Spusť všechny testy")
        print("  test-critical   Spusť pouze kritické testy")
        print("")
        print("Other:")
        print("  shell           Interactive Python shell s venv")
        print("  help            Zobraz tuto zprávu")
        print("")
        print("Examples:")
        print("")
        print("  # First-time setup")
        print("  python3 gestima.py setup")
        print("  python3 gestima.py seed-demo          # Reset DB + demo data + demo admin")
        print("  python3 gestima.py run")
        print("")
        print("  # Development workflow")
        print("  python3 gestima.py test               # Run tests")
        print("  git commit && git push")
        print("")
        print("  # Production deployment")
        print("  python3 gestima.py deploy             # Git pull + restart guide")
        print("")
        print("  # Testing with production data")
        print("  python3 gestima.py restore backup.db.gz")
        print("  python3 gestima.py run")
        print("  python3 gestima.py seed-demo          # Reset back to demo")
        print("")
        print("  # Backup management")
        print("  python3 gestima.py backup")
        print("  python3 gestima.py backup-list")
        print("")
        print("See DEPLOYMENT.md for complete deployment guide.")
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
    elif command == "restore":
        if not args:
            print("❌ Usage: python3 gestima.py restore <backup_file>")
            print("   Example: python3 gestima.py restore gestima_backup_20260127.db.gz")
            sys.exit(1)
        Gestima.restore(args[0])
    elif command == "backup-restore":
        # Legacy alias for 'restore'
        if not args:
            print("❌ Usage: python3 gestima.py restore <backup_file>")
            sys.exit(1)
        Gestima.restore(args[0])
    elif command == "deploy":
        Gestima.deploy()
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
