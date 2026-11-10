from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # Defaults target the host-published ports from docker-compose (5440/6380 avoid clashes with
    # other local services). Inside containers, docker-compose overrides these with service hostnames.
    database_url: str = "postgresql+asyncpg://eval:eval@localhost:5440/eval"
    redis_url: str = "redis://localhost:6380"
    openai_api_key: str | None = None
    worker_concurrency: int = 5


settings = Settings()
