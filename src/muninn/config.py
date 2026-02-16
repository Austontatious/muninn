import os

from pydantic import BaseModel


class Settings(BaseModel):
    db_path: str = os.getenv("MUNINN_DB_PATH", "./data/muninn.db")
    host: str = os.getenv("MUNINN_HOST", "127.0.0.1")
    port: int = int(os.getenv("MUNINN_PORT", "8000"))


settings = Settings()
