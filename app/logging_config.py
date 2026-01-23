"""GESTIMA - Logging konfigurace"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter pro structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Přidat exception info pokud existuje
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Přidat extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "part_id"):
            log_data["part_id"] = record.part_id
        if hasattr(record, "operation_id"):
            log_data["operation_id"] = record.operation_id

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(debug: bool = False) -> None:
    """
    Nastavení logging pro celou aplikaci

    Args:
        debug: Pokud True, loguje se na DEBUG level a do console
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (JSON pro produkci)
    if not debug:
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "gestima.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # Utlumit SQLAlchemy verbose logging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Utlumit uvicorn access log (jen errors)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger.info("Logging initialized", extra={"debug_mode": debug})


def get_logger(name: str) -> logging.Logger:
    """Získat logger pro modul"""
    return logging.getLogger(name)
