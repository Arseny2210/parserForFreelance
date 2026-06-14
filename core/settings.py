from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/freelance_market"
    )
    database_url_sync: str = (
        "postgresql://postgres:postgres@localhost:5432/freelance_market"
    )

    proxy_enabled: bool = False
    proxy_url: Optional[str] = None

    request_timeout: int = 30
    max_retries: int = 5
    throttle_delay: float = 1.0
    exponential_backoff_base: float = 2.0
    exponential_backoff_max: float = 60.0

    user_agent_rotation_enabled: bool = True

    export_dir: str = "exports"
    charts_dir: str = "reports/charts"

    log_level: str = "DEBUG"
    log_file: str = "logs/freelance_parser.log"

    nlp_model: str = "en_core_web_sm"

    scrapers_enabled: list[str] = [
        "upwork",
        "freelancer",
        "guru",
        "fl",
        "kwork",
        "freelancehunt",
    ]

    max_concurrent_requests: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
