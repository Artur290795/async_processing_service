from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field(min_length=1)
    database_url: str
    rabbitmq_url: str
    webhook_timeout_seconds: float = Field(default=5, gt=0)
    outbox_poll_interval_seconds: float = Field(default=1, gt=0)
    outbox_batch_size: int = Field(default=100, ge=1, le=1_000)
    processing_min_delay_seconds: float = Field(default=2, ge=0)
    processing_max_delay_seconds: float = Field(default=5, ge=0)
    processing_success_rate: float = Field(default=0.9, ge=0, le=1)
    retry_delays_seconds: str = "1,2,4"

    @property
    def retry_delays(self) -> tuple[float, ...]:
        return tuple(float(delay.strip()) for delay in self.retry_delays_seconds.split(","))


@lru_cache
def get_settings() -> Settings:
    return Settings()
