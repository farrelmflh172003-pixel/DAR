import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).parent / ".env"), ".env"),
        extra="ignore"
    )

    APP_NAME: str = "Dialogue AI Representative"
    ENV: str = os.getenv("ENV", "development")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ENABLE_REALTIME_MOCK: bool = os.getenv("ENABLE_REALTIME_MOCK", "false").lower() in ("true", "1", "yes")
    OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-mini")
    GEMINI_LIVE_MODEL: str = os.getenv("GEMINI_LIVE_MODEL", "models/gemini-2.0-flash-exp")
    GEMINI_TTS_MODEL: str = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-lite-tts")
    MAX_AUDIO_CHUNK_BYTES: int = 512 * 1024  # 512 KB
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
        ).split(",") if origin.strip()
    ]

    # MariaDB Database Configuration
    MARIADB_HOST: str = os.getenv("MARIADB_HOST", "127.0.0.1")
    MARIADB_PORT: int = int(os.getenv("MARIADB_PORT", "3306"))
    MARIADB_USER: str = os.getenv("MARIADB_USER", "root")
    MARIADB_PASSWORD: str = os.getenv("MARIADB_PASSWORD", "")
    MARIADB_DATABASE: str = os.getenv("MARIADB_DATABASE", "menkopolkam_ai_hub")

    # Security & Access Control Configuration
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true" if os.getenv("ENV") in ("staging", "production") else "false").lower() in ("true", "1", "yes")
    ALLOW_ANONYMOUS_DEV: bool = os.getenv("ALLOW_ANONYMOUS_DEV", "true" if os.getenv("ENV") == "development" else "false").lower() in ("true", "1", "yes")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "menkopolkam-insecure-dev-secret-do-not-use-in-prod-32bytes!")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "menkopolkam-ai-hub")
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "menkopolkam-web")
    ACCESS_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(4 * 3600)))  # 4 jam = 14400 detik
    TICKET_TTL_SECONDS: int = int(os.getenv("TICKET_TTL_SECONDS", "60"))
    MAX_CONCURRENT_SESSIONS_PER_USER: int = int(os.getenv("MAX_CONCURRENT_SESSIONS_PER_USER", "2"))
    MAX_FAILED_HANDSHAKES_PER_IP: int = int(os.getenv("MAX_FAILED_HANDSHAKES_PER_IP", "10"))
    SESSION_IDLE_TIMEOUT_SECONDS: int = int(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", "120"))
    TRUSTED_PROXIES: list[str] = [ip.strip() for ip in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if ip.strip()]
    RATE_LIMIT_SWITCH_PROVIDER: int = int(os.getenv("RATE_LIMIT_SWITCH_PROVIDER", "5"))
    WORKERS: int = 1

    def __init__(self, **values):
        super().__init__(**values)
        self.WORKERS = self._resolve_workers_count()
        if self.ENV.lower() in ("staging", "production"):
            # Immutable security overrides for protected environments
            self.ALLOW_ANONYMOUS_DEV = False
            self.AUTH_ENABLED = True

    @staticmethod
    def _resolve_workers_count() -> int:
        import sys
        # 1. Inspect environment variables (WORKERS or Gunicorn's WEB_CONCURRENCY)
        raw_env = os.getenv("WORKERS", os.getenv("WEB_CONCURRENCY", "")).strip()
        if raw_env:
            try:
                val = int(raw_env)
                if val < 1:
                    raise ValueError(f"Invalid worker count {val}. WORKERS must be at least 1.")
                return val
            except ValueError as e:
                if "invalid literal" in str(e).lower():
                    raise ValueError(f"Malformed WORKERS configuration '{raw_env}'. Must be a valid integer.")
                raise

        # 2. Inspect CLI flags (--workers N or --workers=N)
        for i, arg in enumerate(sys.argv):
            if arg.startswith("--workers="):
                val_str = arg.split("=", 1)[1].strip()
                try:
                    val = int(val_str)
                    if val < 1:
                        raise ValueError(f"Invalid --workers value '{val_str}'. Worker count must be at least 1.")
                    return val
                except ValueError:
                    raise ValueError(f"Malformed --workers flag '{val_str}'. Must be a valid integer.")
            elif arg == "--workers" and i + 1 < len(sys.argv):
                val_str = sys.argv[i + 1].strip()
                try:
                    val = int(val_str)
                    if val < 1:
                        raise ValueError(f"Invalid --workers value '{val_str}'. Worker count must be at least 1.")
                    return val
                except ValueError:
                    raise ValueError(f"Malformed --workers flag '{val_str}'. Must be a valid integer.")

        return 1

settings = Settings()


