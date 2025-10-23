from pydantic import BaseModel, EmailStr, validator, field_validator
from datetime import datetime
from typing import Optional, List, Dict
import re
from enum import Enum

class OperationType(str, Enum):
    """
    Tipos de operaciones soportadas por el sistema.
    
    Decidí usar Enum porque:
    - Proporciona validación automática de tipos
    - Es más explícito que strings mágicos
    - Facilita el autocompletado en IDEs
    - Reduce errores de tipeo
    """
    RESERVE_BOOK = "RESERVE_BOOK"
    RENEW_RESERVATION = "RENEW_RESERVATION" 
    CANCEL_RESERVATION = "CANCEL_RESERVATION"
    ADD_BOOK = "ADD_BOOK"
    REMOVE_BOOK = "REMOVE_BOOK"
    LIST_BOOKS = "LIST_BOOKS"
    ERROR = "ERROR"

class Book(BaseModel):
    """
    Modelo que representa un libro en el sistema.
    
    Decisiones de diseño:
    - Uso Optional para campos que pueden ser NULL en BD
    - ISBN como string para soportar formatos internacionales
    - Available con valor por defecto True (los libros nuevos están disponibles)
    - Created_at se genera automáticamente si no se proporciona
    
    Campos requeridos vs opcionales basado en uso real:
    - Título y autor son obligatorios (sin ellos no tiene sentido el registro)
    - ISBN es opcional porque no todos los libros lo tienen
    """
    
    id: Optional[int] = None
    title: str
    author: str
    isbn: Optional[str] = None
    created_at: Optional[datetime] = None
    available: bool = True

    @field_validator('title', 'author')
    @classmethod
    def validate_not_empty(cls, value: str) -> str:
        """
        Validar que título y autor no estén vacíos.
        
        He visto que los usuarios a veces envían espacios en blanco,
        por eso hago strip() antes de validar.
        """
        if not value or not value.strip():
            raise ValueError('El título y autor son obligatorios')
        return value.strip()

    @field_validator('isbn')
    @classmethod
    def validate_isbn_format(cls, value: Optional[str]) -> Optional[str]:
        """
        Validar formato ISBN básico si se proporciona.
        
        No valido ISBN real porque:
        - Los usuarios pueden cometer errores al tipear
        - Algunos libros antiguos no tienen ISBN estándar
        - Es más importante tener el libro que validar perfectamente el ISBN
        """
        if value is None:
            return value
            
        # Limpiar guiones y espacios
        clean_isbn = re.sub(r'[-\s]', '', value)
        
        # Validar longitud básica (ISBN-10 o ISBN-13)
        if not re.match(r'^(\d{10}|\d{13})$', clean_isbn):
            raise ValueError('Formato ISBN inválido. Debe tener 10 o 13 dígitos')
            
        return clean_isbn

class Reservation(BaseModel):
    """
    Modelo que representa una reserva de libro.
    
    Decisiones de diseño:
    - User_email es required para saber quién reservó
    - Timestamps automáticos si no se proporcionan
    - Active por defecto True (las reservas nuevas están activas)
    - Book_id required para relación con libros
    
    Aprendí que es mejor:
    - Usar datetime para compatibilidad con diferentes zonas horarias
    - Tener campos opcionales para timestamps de renovación
    """
    
    id: Optional[int] = None
    book_id: int
    user_email: str
    reserved_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    active: bool = True

    @field_validator('user_email')
    @classmethod
    def validate_user_email(cls, value: str) -> str:
        """
        Validar formato de email del usuario.
        
        Uso una regex simple pero efectiva porque:
        - Las validaciones estrictas de email a veces rechazan formatos válidos
        - Es más importante capturar el email que validarlo perfectamente
        - Los usuarios pueden usar emails con dominios nuevos o internacionales
        """
        if not value or '@' not in value:
            raise ValueError('El email debe tener un formato válido')
        
        # Regex básica pero suficiente para la mayoría de casos
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value.strip()):
            raise ValueError('Formato de email inválido')
            
        return value.strip().lower()  # Normalizar a minúsculas

    @field_validator('book_id')
    @classmethod 
    def validate_book_id(cls, value: int) -> int:
        """
        Validar que book_id sea positivo.
        
        Aunque la BD tiene ID autoincremental, valido aquí también porque:
        - Previene errores si alguien usa la API directamente
        - Es una validación barata que puede evitar problemas
        - Los IDs negativos nunca son válidos en nuestro sistema
        """
        if value <= 0:
            raise ValueError('El ID del libro debe ser un número positivo')
        return value

class EmailRequest(BaseModel):
    """
    Modelo para solicitudes de procesamiento de email.
    
    Este modelo es crucial porque:
    - Es la entrada principal del sistema
    - Debe ser robusto contra datos malformados
    - Necesita validaciones tempranas para evitar costos de OpenAI
    
    Decisiones de validación:
    - Valido formato de email temprano para fallar rápido
    - Strip() automático para evitar espacios en blanco
    - Longitud mínima en body para evitar spam o emails vacíos
    """
    
    subject: str
    body: str
    from_email: str

    @field_validator('subject', 'body', 'from_email')
    @classmethod
    def validate_not_empty_or_whitespace(cls, value: str) -> str:
        """
        Validar que los campos no estén vacíos o solo tengan espacios.
        
        He visto casos donde:
        - Los usuarios pegan texto con muchos espacios
        - Algunos clientes de email envían subjects vacíos
        - Es mejor normalizar temprano que procesar basura
        """
        if not value or not value.strip():
            raise ValueError('Este campo no puede estar vacío')
        return value.strip()

    @field_validator('from_email')
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        """
        Validar formato de email con regex específica.
        
        Uso esta regex porque:
        - Es más permisiva que la estándar (soporta nuevos TLDs)
        - Rechaza emails obviamente inválidos
        - Es rápida de ejecutar
        """
        cleaned_value = value.strip()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, cleaned_value):
            raise ValueError('Formato de email inválido')
            
        return cleaned_value

    @field_validator('body')
    @classmethod
    def validate_body_length(cls, value: str) -> str:
        """
        Validar longitud mínima del cuerpo del mensaje.
        
        Decidí un mínimo de 10 caracteres porque:
        - Mensajes más cortos probablemente no tienen sentido
        - Evita procesar spam o mensajes de prueba
        - Mensajes legítimos suelen ser más largos
        """
        if len(value.strip()) < 10:
            raise ValueError('El mensaje debe tener al menos 10 caracteres')
        return value

class OperationResult(BaseModel):
    """
    Modelo estandarizado para respuestas de la API.
    
    Este modelo proporciona:
    - Consistencia en todas las respuestas
    - Facilita el debugging y logging
    - Estructura predecible para frontends
    
    Decidí incluir un campo 'data' opcional porque:
    - Algunas operaciones no retornan datos adicionales
    - Es más flexible que tener múltiples modelos de respuesta
    - Sigue el patrón común en APIs REST
    """
    
    success: bool
    message: str
    data: Optional[Dict] = None
    operation_type: Optional[OperationType] = None

    @field_validator('message')
    @classmethod
    def validate_message_not_empty(cls, value: str) -> str:
        """Validar que el mensaje no esté vacío."""
        if not value or not value.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return value.strip()

class EmailProcessingResult(BaseModel):
    """
    Modelo para resultados de procesamiento de emails.
    
    Lo creé para:
    - Seguimiento de qué emails se procesaron
    - Estadísticas de rendimiento del sistema
    - Debugging de problemas específicos
    """
    
    email_from: str
    processed_at: datetime
    operation_type: OperationType
    success: bool
    error_message: Optional[str] = None
    processing_time_ms: Optional[float] = None

class SystemStats(BaseModel):
    """
    Modelo para estadísticas del sistema.
    
    Útil para:
    - Monitoreo de salud del sistema
    - Dashboard de administración
    - Alertas de rendimiento
    """
    
    total_books: int
    available_books: int
    active_reservations: int
    unique_users: int
    system_uptime_minutes: float
    last_processed_email: Optional[datetime] = None

# Modelos de respuesta para endpoints específicos
class ProcessEmailsResponse(BaseModel):
    """
    Respuesta para el endpoint de procesamiento batch de emails.
    """
    success: bool
    message: str
    emails_processed: int
    details: List[Dict] = []

class SystemStatus(BaseModel):
    """
    Respuesta para el endpoint de estado del sistema.
    
    Decidí hacerlo tolerante a fallos porque:
    - Que falle un servicio no debería hacer caer todo el endpoint
    - Es mejor mostrar estado parcial que nada
    - Los monitores externos necesitan respuestas consistentes
    """
    database: bool
    email_service: bool
    openai: bool
    overall: bool

# Utilidades para validación de datos
class DataValidators:
    """
    Utilidades de validación reutilizables.
    
    Las separé en una clase porque:
    - Se usan en múltiples modelos
    - Facilitan testing unitario
    - Centralizan la lógica de validación
    """
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validar formato de email reutilizable."""
        if not email or '@' not in email:
            raise ValueError('Email inválido')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            raise ValueError('Formato de email inválido')
            
        return email.strip().lower()
    
    @staticmethod
    def validate_not_empty(value: str, field_name: str) -> str:
        """Validar que un string no esté vacío."""
        if not value or not value.strip():
            raise ValueError(f'{field_name} no puede estar vacío')
        return value.strip()
    
    @staticmethod
    def validate_positive_number(value: int, field_name: str) -> int:
        """Validar que un número sea positivo."""
        if value <= 0:
            raise ValueError(f'{field_name} debe ser un número positivo')
        return value