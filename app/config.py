from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    secret_key: str

    # Groq — основной
    groq_api_key:    Optional[str] = None
    ai_model:        str = "llama-3.3-70b-versatile"

    # GigaChat — резервный
    gigachat_api_key:   Optional[str] = None
    gigachat_model:     str = "GigaChat"

    class Config:
        env_file = ".env"


settings = Settings()