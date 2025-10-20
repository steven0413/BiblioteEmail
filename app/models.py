from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional
import re

class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author: str
    isbn: Optional[str] = None
    created_at: Optional[datetime] = None
    available: bool = True

class Reservation(BaseModel):
    id: Optional[int] = None
    book_id: int
    user_email: str
    reserved_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    active: bool = True

# Modelos para respuestas de la API
class OperationResult(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class EmailRequest(BaseModel):
    subject: str
    body: str
    from_email: str

    @validator('subject', 'body', 'from_email')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Este campo no puede estar vacío')
        return v.strip()

    @validator('from_email')
    def validate_email_format(cls, v):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Formato de email inválido')
        return v