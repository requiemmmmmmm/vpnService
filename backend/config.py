from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    bot_token: str
    backend_url: str = "http://backend:8000"
    wg_interface: str = "wg0"
    wg_server_public_key: str = ""
    wg_server_endpoint: str = ""
    wg_dns: str = "1.1.1.1"
    wg_subnet: str = "10.8.0.0/24"
    wg_server_ip: str = "10.8.0.1"
    wg_mock: bool = False
    device_limit: int = 5

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
