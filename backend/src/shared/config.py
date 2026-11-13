from urllib.parse import quote_plus
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path
from urllib.parse import quote_plus

# config.py lives at: backend/src/shared/config.py
# parents[0] = src/shared
# parents[1] = src
# parents[2] = backend
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_user: str = Field(default="postgres", validation_alias="DB_USER")
    db_password: str = Field(validation_alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str = Field(default="university_tickets", validation_alias="DB_NAME")

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    @property
    def database_url(self) -> str:
        pw = quote_plus(self.db_password)
        return (
            f"postgresql+asyncpg://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()