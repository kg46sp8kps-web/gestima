"""GESTIMA - Konfigurace"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    VERSION: str = "1.6.0"
    DEBUG: bool = False  # BEZPEČNOST: Default False pro produkci

    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_VIA_ENV"

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validace SECRET_KEY - nesmí být default hodnota v produkci."""
        if v == "CHANGE_THIS_IN_PRODUCTION_VIA_ENV":
            import os
            # V produkci (bez DEBUG) je to KRITICKÁ chyba
            if os.getenv("DEBUG", "false").lower() not in ("true", "1", "yes"):
                raise ValueError(
                    "SECRET_KEY není nastavena! Nastavte ji v .env souboru: "
                    "SECRET_KEY=your-secure-random-key-at-least-32-chars"
                )
        if len(v) < 32:
            raise ValueError("SECRET_KEY musí mít alespoň 32 znaků")
        return v
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECURE_COOKIE: bool = False  # True pro HTTPS (produkce)

    # CORS - seznam povolených originů oddělených čárkou
    # Prázdný string = žádný CORS (same-origin only)
    # Příklad: "https://gestima.example.com,https://admin.example.com"
    CORS_ORIGINS: str = ""
    
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "gestima.db"
    
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    
    # Backup
    BACKUP_RETENTION_COUNT: int = 7  # Kolik záloh ponechat
    BACKUP_COMPRESS: bool = True  # Komprimovat gzip

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"  # Obecné API
    RATE_LIMIT_AUTH: str = "10/minute"  # Login/register (přísnější)

    # Polotovar - přídavky
    STOCK_ALLOWANCE_DIAMETER: float = 3.0
    STOCK_ALLOWANCE_LENGTH: float = 5.0
    STOCK_ALLOWANCE_CUT: float = 3.0
    STANDARD_BAR_LENGTH: float = 3000.0
    MAX_BAR_FEEDER_LENGTH: float = 1200.0


settings = Settings()
