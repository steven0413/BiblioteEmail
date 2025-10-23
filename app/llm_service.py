from openai import OpenAI
from app.config import settings
import logging
import json
import re

logger = logging.getLogger(__name__)

class LLMService:
    """
    Servicio para procesamiento de lenguaje natural usando OpenAI.
    
    Decisiones técnicas:
    - GPT-4 para mejor comprensión de contexto en español
    - Temperature baja (0.1) para SQL consistente
    - Chain-of-thought para mejor razonamiento
    - Few-shot learning con ejemplos específicos
    """
    
    def __init__(self):
        # ✅ Mantener nombres originales para compatibilidad
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def natural_language_to_sql(self, user_request: str, user_email: str) -> dict:
        """
        Convertir lenguaje natural a SQL.
        
        Args:
            user_request: Texto del usuario en español
            user_email: Email para asociar reservas
            
        Returns:
            Dict con SQL, tipo de operación y explicación
        """
        try:
            prompt = self._build_cot_prompt(user_request, user_email)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Baja temperatura para SQL consistente
                max_tokens=800
            )
            
            sql_response = response.choices[0].message.content.strip()
            return self._parse_sql_response(sql_response)
            
        except Exception as e:
            logger.error(f"❌ Error en OpenAI: {e}")
            return {
                "sql": None,
                "operation_type": "error", 
                "explanation": f"Error procesando solicitud: {str(e)}"
            }
    
    def _build_cot_prompt(self, user_request: str, user_email: str) -> str:
        """Construir prompt con chain-of-thought"""
        return f"""
        USER_EMAIL: {user_email}
        USER_REQUEST: "{user_request}"

        Sigue este proceso paso a paso:

        PASO 1 - Identificar intención del usuario
        PASO 2 - Extraer libro, autor y detalles  
        PASO 3 - Determinar operación (reservar, renovar, etc.)
        PASO 4 - Construir SQL con validaciones
        PASO 5 - Verificar que sea seguro

        Aplica estos pasos a la solicitud.
        """
    
    def _get_system_prompt(self) -> str:
        """Prompt del sistema con ejemplos específicos"""
        return """
        Eres un asistente que convierte español a SQL. Responde SOLO con JSON.

        Ejemplos:

        {
            "sql": "INSERT INTO reservations (book_id, user_email, reserved_at, expires_at) SELECT id, 'usuario@email.com', GETDATE(), DATEADD(day, 14, GETDATE()) FROM books WHERE title = '1984' AND author = 'George Orwell' AND available = 1",
            "operation_type": "RESERVE_BOOK", 
            "explanation": "Usuario quiere reservar '1984' de George Orwell"
        }

        Tablas: books (id, title, author, isbn, created_at, available)
                reservations (id, book_id, user_email, reserved_at, renewed_at, expires_at, active)

        Responde ÚNICAMENTE con JSON válido.
        """
    
    async def format_response_to_natural_language(self, sql_result: any, operation_type: str, user_request: str) -> str:
        """
        Formatear resultados de BD a respuesta natural en español.
        
        He notado que los usuarios prefieren respuestas cálidas y específicas
        en lugar de mensajes genéricos.
        """
        try:
            # Lógica existente de formateo
            if operation_type == "RESERVE_BOOK":
                if isinstance(sql_result, dict) and sql_result.get("rows_affected", 0) > 0:
                    return f"¡Hola! Recibí tu solicitud para reservar un libro. ✅ La reserva se realizó exitosamente. El libro estará disponible para ti durante 14 días."
                else:
                    return f"¡Hola! Recibí tu solicitud para reservar. ❌ No pude completar la reserva. El libro podría no estar disponible o ya tienes una reserva activa."
            
            # Respuestas para otros tipos de operaciones...
            return f"¡Hola! Procesé tu solicitud: '{user_request}'. El resultado fue: {sql_result}"
            
        except Exception as e:
            logger.error(f"Error formateando respuesta: {e}")
            return f"¡Hola! Procesé tu solicitud: '{user_request}'."
    
    def _parse_sql_response(self, response: str) -> dict:
        """Parsear respuesta de OpenAI - manteniendo lógica existente"""
        try:
            # Lógica de parsing existente
            cleaned_response = response.strip()
            json_match = re.search(r'(\{.*\})', cleaned_response, re.DOTALL)
            
            if json_match:
                parsed = json.loads(json_match.group(1))
                if all(key in parsed for key in ["sql", "operation_type", "explanation"]):
                    return parsed
            
            # Fallback si el parsing falla
            return {
                "sql": "SELECT * FROM books WHERE available = 1",
                "operation_type": "LIST_BOOKS", 
                "explanation": "No se pudo parsear la respuesta correctamente"
            }
            
        except Exception as e:
            logger.error(f"Error parseando respuesta: {e}")
            return {
                "sql": "SELECT * FROM books WHERE available = 1",
                "operation_type": "LIST_BOOKS",
                "explanation": f"Error: {str(e)}"
            }

llm_service = LLMService()