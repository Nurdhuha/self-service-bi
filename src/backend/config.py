import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "olist"
    DB_USER: str = "postgres_readonly"
    DB_PASSWORD: str = ""
    
    MODEL_PATH: str = "../training/sql_llama_lora_model"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Load from .env if it exists in the current directory
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
