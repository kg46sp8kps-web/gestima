"""GESTIMA - Konfigurace"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    VERSION: str = "2.0.0"
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
    DB_PATH: Path = BASE_DIR / "gestima.db"

    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"

    # AI Services
    OPENAI_API_KEY: str = ""  # OpenAI API key for GPT-4o vision estimation line
    AI_RATE_LIMIT: str = "10/hour"  # AI parsing rate limit (cost control)
    @field_validator('OPENAI_API_KEY', mode='before')
    @classmethod
    def resolve_openai_key(cls, v: str) -> str:
        """Fallback to .env value if system env is empty string."""
        if not v:
            from dotenv import dotenv_values
            vals = dotenv_values('.env')
            return vals.get('OPENAI_API_KEY', '')
        return v

    # Infor CloudSuite Industrial Integration
    INFOR_API_URL: str = ""  # Infor API base URL (e.g., https://util90110.kovorybka.cz)
    INFOR_CONFIG: str = "TEST"  # Infor configuration name (CRITICAL: NEVER use "LIVE"!)
    INFOR_USERNAME: str = ""  # Infor API username
    INFOR_PASSWORD: str = ""  # Infor API password
    INFOR_WC_MAPPING: str = '{"PS":"80000011","PSa":"80000011","PSm":"80000011","PSv":"80000011","FV3":"80000006","FH4":"80000007","FV5":"80000010","FV5R":"80000009","FV3R":"80000008","FV":"80000005","SH2":"80000001","SH2A":"80000002","SM1":"80000003","SM3":"80000004","VS":"80000014","OTK":"80000013","OTK/KO":"80000013","MECH":"80000015","KOO":"80000016"}'

    # CsiXls Accounting API
    CSIXLS_API_URL: str = ""  # CsiXls API base URL
    CSIXLS_API_TOKEN: str = ""  # CsiXls API auth token

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"  # Obecné API
    RATE_LIMIT_AUTH: str = "10/minute"  # Login/register (přísnější)

    # Drawing Import from Network Share
    DRAWINGS_SHARE_PATH: str = ""  # SMB share path, e.g. "/Volumes/Dokumenty/TPV-dokumentace/Výkresy"


settings = Settings()
