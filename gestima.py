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

        # Input email
        email = input("Email: ").strip()
        if not email or "@" not in email:
            print("❌ Invalid email")
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
                email='{email}',
                password='{password}',
                role=UserRole.ADMIN
            )
            print(f"✅ Admin user created: {{user.username}} ({{user.email}})")
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
    def help():
        """Zobraz dostupné příkazy"""
        print("GESTIMA 1.0 - CLI Helper")
        print("")
        print("Usage: python3 gestima.py [command]")
        print("")
        print("Commands:")
        print("  setup           Inicializuj venv a instaluj dependencies")
        print("  run             Spusť aplikaci (http://localhost:8000)")
        print("  create-admin    Vytvoř admin uživatele (first-time setup)")
        print("  test            Spusť všechny testy")
        print("  test-critical   Spusť pouze kritické testy")
        print("  shell           Interactive Python shell s venv")
        print("  help            Zobraz tuto zprávu")
        print("")
        print("Examples:")
        print("  python3 gestima.py setup")
        print("  python3 gestima.py create-admin")
        print("  python3 gestima.py run")
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
