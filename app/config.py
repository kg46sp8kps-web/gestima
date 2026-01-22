"""GESTIMA - Konfigurace"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "gestima.db"
    
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    
    # Polotovar - přídavky
    STOCK_ALLOWANCE_DIAMETER: float = 3.0
    STOCK_ALLOWANCE_LENGTH: float = 5.0
    STOCK_ALLOWANCE_CUT: float = 3.0
    STANDARD_BAR_LENGTH: float = 3000.0
    MAX_BAR_FEEDER_LENGTH: float = 1200.0


settings = Settings()
