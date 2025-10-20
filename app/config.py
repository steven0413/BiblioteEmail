from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    db_server: str # biblioteca-sql-server-steven.database.windows.net
    db_database: str # biblioteca_db
    db_username: str # biblioteca_admin
    db_password: str # StrongPassword123!
    
    # Email
    imap_server: str    # imap.gmail.com
    imap_username: str 
    imap_password: str
    smtp_server: str
    smtp_port: int = 587
    
    # OpenAI
    openai_api_key: str # api_key_aqui
    openai_model: str = "gpt-4"
    
    # App
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"

settings = Settings()