"""GESTIMA - Backup Service pro SQLite databázi"""

import gzip
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def create_backup(
    backup_dir: Optional[Path] = None,
    compress: bool = True,
    retention_count: int = 7
) -> Path:
    """
    Vytvoří zálohu SQLite databáze.

    Používá sqlite3.backup() API - bezpečné i pro WAL mode.

    Args:
        backup_dir: Složka pro zálohy (default: PROJECT_DIR/backups)
        compress: Komprimovat gzip (default: True)
        retention_count: Kolik záloh ponechat (default: 7)

    Returns:
        Path k vytvořené záloze

    Raises:
        FileNotFoundError: Pokud zdrojová DB neexistuje
        sqlite3.Error: Při chybě zálohování
    """
    db_path = settings.DB_PATH

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Backup directory
    if backup_dir is None:
        backup_dir = settings.BASE_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp pro název souboru
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"gestima_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name

    logger.info(f"Creating backup: {backup_path}")

    # SQLite backup API - bezpečné pro WAL mode
    source_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(backup_path))

    try:
        source_conn.backup(dest_conn)
        logger.info(f"Backup created: {backup_path}")
    finally:
        source_conn.close()
        dest_conn.close()

    # Komprese
    final_path = backup_path
    if compress:
        gz_path = backup_path.with_suffix(".db.gz")
        with open(backup_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()  # Smaž nekomprimovaný
        final_path = gz_path
        logger.info(f"Compressed to: {gz_path}")

    # Rotace - ponech pouze posledních N záloh
    cleanup_old_backups(backup_dir, retention_count)

    return final_path


def cleanup_old_backups(backup_dir: Path, retention_count: int) -> int:
    """
    Smaže staré zálohy, ponechá pouze posledních N.

    Args:
        backup_dir: Složka se zálohami
        retention_count: Kolik záloh ponechat

    Returns:
        Počet smazaných záloh
    """
    # Najdi všechny backup soubory
    backups = sorted(
        [f for f in backup_dir.glob("gestima_backup_*.db*")],
        key=lambda f: f.stat().st_mtime,
        reverse=True  # Nejnovější první
    )

    # Smaž staré
    deleted = 0
    for old_backup in backups[retention_count:]:
        old_backup.unlink()
        logger.info(f"Deleted old backup: {old_backup}")
        deleted += 1

    return deleted


def list_backups(backup_dir: Optional[Path] = None) -> list[dict]:
    """
    Vrátí seznam dostupných záloh.

    Returns:
        List of dicts: {name, path, size_mb, created_at}
    """
    if backup_dir is None:
        backup_dir = settings.BASE_DIR / "backups"

    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("gestima_backup_*.db*"), reverse=True):
        stat = f.stat()
        backups.append({
            "name": f.name,
            "path": str(f),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return backups


def restore_backup(backup_path: Path) -> bool:
    """
    Obnoví databázi ze zálohy.

    POZOR: Toto přepíše aktuální databázi!

    Args:
        backup_path: Cesta k záloze (.db nebo .db.gz)

    Returns:
        True při úspěchu

    Raises:
        FileNotFoundError: Pokud záloha neexistuje
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    db_path = settings.DB_PATH

    # Dekomprimuj pokud je gzip
    if backup_path.suffix == ".gz":
        temp_db = backup_path.with_suffix("")  # Odstraň .gz
        with gzip.open(backup_path, "rb") as f_in:
            with open(temp_db, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        source_path = temp_db
        cleanup_temp = True
    else:
        source_path = backup_path
        cleanup_temp = False

    try:
        # Použij SQLite backup API pro obnovení
        source_conn = sqlite3.connect(str(source_path))
        dest_conn = sqlite3.connect(str(db_path))

        try:
            source_conn.backup(dest_conn)
            logger.info(f"Database restored from: {backup_path}")
        finally:
            source_conn.close()
            dest_conn.close()
    finally:
        if cleanup_temp and source_path.exists():
            source_path.unlink()

    return True
