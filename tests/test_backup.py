"""Testy pro backup service"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.services.backup_service import (
    create_backup,
    cleanup_old_backups,
    list_backups,
    restore_backup,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Vytvoř dočasnou DB pro testy"""
    db_path = tmp_path / "test.db"

    # Vytvoř DB s testovacími daty
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test (value) VALUES ('original')")
    conn.commit()
    conn.close()

    # Monkey-patch settings
    class MockSettings:
        DB_PATH = db_path
        BASE_DIR = tmp_path

    monkeypatch.setattr("app.services.backup_service.settings", MockSettings())

    return db_path


class TestCreateBackup:
    def test_creates_backup_file(self, temp_db, tmp_path):
        """Backup vytvoří soubor"""
        backup_dir = tmp_path / "backups"
        backup_path = create_backup(backup_dir=backup_dir, compress=False)

        assert backup_path.exists()
        assert backup_path.suffix == ".db"

    def test_creates_compressed_backup(self, temp_db, tmp_path):
        """Backup vytvoří komprimovaný soubor"""
        backup_dir = tmp_path / "backups"
        backup_path = create_backup(backup_dir=backup_dir, compress=True)

        assert backup_path.exists()
        assert backup_path.name.endswith(".db.gz")

    def test_backup_contains_data(self, temp_db, tmp_path):
        """Záloha obsahuje data"""
        backup_dir = tmp_path / "backups"
        backup_path = create_backup(backup_dir=backup_dir, compress=False)

        # Ověř data v záloze
        conn = sqlite3.connect(str(backup_path))
        result = conn.execute("SELECT value FROM test").fetchone()
        conn.close()

        assert result[0] == "original"

    def test_raises_if_db_not_exists(self, tmp_path, monkeypatch):
        """Vyhodí chybu pokud DB neexistuje"""
        class MockSettings:
            DB_PATH = tmp_path / "nonexistent.db"
            BASE_DIR = tmp_path

        monkeypatch.setattr("app.services.backup_service.settings", MockSettings())

        with pytest.raises(FileNotFoundError):
            create_backup()


class TestCleanupOldBackups:
    def test_keeps_retention_count(self, tmp_path):
        """Ponechá správný počet záloh"""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Vytvoř 5 fake záloh
        for i in range(5):
            (backup_dir / f"gestima_backup_2024010{i}_120000.db.gz").touch()

        # Ponech pouze 3
        deleted = cleanup_old_backups(backup_dir, retention_count=3)

        assert deleted == 2
        remaining = list(backup_dir.glob("gestima_backup_*.db*"))
        assert len(remaining) == 3


class TestListBackups:
    def test_lists_backups(self, temp_db, tmp_path):
        """Vrátí seznam záloh"""
        backup_dir = tmp_path / "backups"
        create_backup(backup_dir=backup_dir, compress=True)

        backups = list_backups(backup_dir=backup_dir)

        assert len(backups) >= 1
        assert all("name" in b for b in backups)
        assert all("size_mb" in b for b in backups)
        assert all("created_at" in b for b in backups)

    def test_empty_if_no_backups(self, tmp_path, monkeypatch):
        """Prázdný seznam pokud neexistují zálohy"""
        class MockSettings:
            BASE_DIR = tmp_path

        monkeypatch.setattr("app.services.backup_service.settings", MockSettings())

        backups = list_backups()
        assert backups == []


class TestRestoreBackup:
    def test_restores_from_backup(self, temp_db, tmp_path):
        """Obnoví DB ze zálohy"""
        backup_dir = tmp_path / "backups"

        # Vytvoř zálohu
        backup_path = create_backup(backup_dir=backup_dir, compress=False)

        # Změň originální DB
        conn = sqlite3.connect(str(temp_db))
        conn.execute("UPDATE test SET value = 'modified'")
        conn.commit()
        conn.close()

        # Ověř změnu
        conn = sqlite3.connect(str(temp_db))
        assert conn.execute("SELECT value FROM test").fetchone()[0] == "modified"
        conn.close()

        # Obnov ze zálohy
        restore_backup(backup_path)

        # Ověř obnovení
        conn = sqlite3.connect(str(temp_db))
        assert conn.execute("SELECT value FROM test").fetchone()[0] == "original"
        conn.close()

    def test_restores_from_compressed(self, temp_db, tmp_path):
        """Obnoví DB z komprimované zálohy"""
        backup_dir = tmp_path / "backups"

        # Vytvoř komprimovanou zálohu
        backup_path = create_backup(backup_dir=backup_dir, compress=True)

        # Změň originální DB
        conn = sqlite3.connect(str(temp_db))
        conn.execute("UPDATE test SET value = 'modified'")
        conn.commit()
        conn.close()

        # Obnov ze zálohy
        restore_backup(backup_path)

        # Ověř obnovení
        conn = sqlite3.connect(str(temp_db))
        assert conn.execute("SELECT value FROM test").fetchone()[0] == "original"
        conn.close()

    def test_raises_if_backup_not_exists(self, temp_db, tmp_path):
        """Vyhodí chybu pokud záloha neexistuje"""
        with pytest.raises(FileNotFoundError):
            restore_backup(tmp_path / "nonexistent.db.gz")
