from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    """
    Configuración centralizada de la aplicación.
    
    Decisiones técnicas:
    - Uso pydantic-settings para validación robusta
    - Variables en inglés para consistencia con convenciones
    - Soporte para .env en desarrollo y variables de entorno en producción
    """
    
    # Database - Azure SQL
    db_server: str
    db_database: str 
    db_username: str
    db_password: str
    
    # Email - Gmail configuration
    imap_server: str = "imap.gmail.com"
    imap_username: str
    imap_password: str
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    
    # OpenAI 
    openai_api_key: str
    openai_model: str = "gpt-4"
    
    # App settings
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"

# ✅ MANTENER nombre original para compatibilidad
settings = Settings()