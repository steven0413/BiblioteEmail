from openai import OpenAI
from app.config import settings
import logging
import json
import re

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def natural_language_to_sql(self, user_request: str, user_email: str) -> dict:
        """
        Few-Shot Learning + Chain-of-Thought para conversión lenguaje natural → SQL
        """
        prompt = self._build_cot_sql_prompt(user_request, user_email)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_cot_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            sql_response = response.choices[0].message.content.strip()
            return self._parse_sql_response(sql_response)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "sql": None,
                "operation_type": "error",
                "explanation": f"Error processing request: {str(e)}"
            }
    
    def _build_cot_sql_prompt(self, user_request: str, user_email: str) -> str:
        """Chain-of-Thought prompt para razonamiento paso a paso"""
        return f"""
        USER_EMAIL: {user_email}
        USER_REQUEST: "{user_request}"

        Sigue este proceso de razonamiento paso a paso:

        PASO 1 - Identificar intención:
        ¿Qué quiere hacer el usuario? (reservar, renovar, cancelar, listar, agregar, eliminar)

        PASO 2 - Extraer entidades:
        - ¿Qué libro menciona?
        - ¿Qué autor menciona? 
        - ¿Qué información adicional proporciona?

        PASO 3 - Determinar operación:
        Basado en la intención y entidades, selecciona la operación correcta.

        PASO 4 - Construir SQL:
        Genera la consulta SQL apropiada considerando:
        - Validaciones de disponibilidad
        - Integridad referencial
        - Manejo de fechas

        PASO 5 - Verificar:
        Revisa que el SQL sea seguro y correcto.

        Ahora aplica este proceso al request del usuario.
        """
    
    def _get_cot_system_prompt(self) -> str:
        """Few-Shot Learning con ejemplos de razonamiento"""
        return """
        Eres un experto en SQL que usa Chain-of-Thought reasoning. Analiza requests paso a paso.

        ## INSTRUCCIONES CRÍTICAS:
        - DEBES responder ÚNICAMENTE con un objeto JSON válido.
        - NO incluyas ningún texto fuera del JSON.
        - El JSON debe tener exactamente las claves: "sql", "operation_type", "explanation".

        ## EJEMPLOS FEW-SHOT:

        EJEMPLO 1:
        {
            "sql": "INSERT INTO reservations (book_id, user_email, reserved_at, expires_at) SELECT id, 'usuario@email.com', GETDATE(), DATEADD(day, 14, GETDATE()) FROM books WHERE title = '1984' AND author = 'George Orwell' AND available = 1",
            "operation_type": "RESERVE_BOOK",
            "explanation": "PASO 1: Usuario quiere RESERVAR un libro. PASO 2: Libro: '1984', Autor: 'George Orwell'. PASO 3: Operación: RESERVE_BOOK. PASO 4: SQL: Insertar reserva si el libro está disponible. PASO 5: Verificado."
        }

        EJEMPLO 2:
        {
            "sql": "UPDATE reservations SET renewed_at = GETDATE(), expires_at = DATEADD(day, 7, expires_at) WHERE user_email = 'usuario@email.com' AND book_id = (SELECT id FROM books WHERE title = 'Cien años de soledad') AND active = 1",
            "operation_type": "RENEW_RESERVATION",
            "explanation": "PASO 1: Usuario quiere RENOVAR una reserva existente. PASO 2: Libro: 'Cien años de soledad'. PASO 3: Operación: RENEW_RESERVATION. PASO 4: SQL: Actualizar fechas de renovación y expiración. PASO 5: Verificado que la reserva existe y está activa."
        }

        EJEMPLO 3:
        {
            "sql": "SELECT title, author, isbn FROM books WHERE author = 'Gabriel García Márquez' AND available = 1",
            "operation_type": "LIST_BOOKS",
            "explanation": "PASO 1: Usuario quiere LISTAR libros específicos. PASO 2: Autor: 'Gabriel García Márquez', filtro: disponibles. PASO 3: Operación: LIST_BOOKS. PASO 4: SQL: Seleccionar libros del autor disponibles. PASO 5: Verificado."
        }

        ## TABLAS DISPONIBLES:
        - books (id, title, author, isbn, created_at, available)
        - reservations (id, book_id, user_email, reserved_at, renewed_at, expires_at, active)

        ## REGLAS:
        - Siempre responde en formato JSON, sin ningún texto adicional.
        - Incluye el razonamiento en "explanation".
        - Usa parámetros seguros cuando sea posible.
        - Considera el email del usuario en las queries.

        Ahora, para la solicitud del usuario, responde ÚNICAMENTE con el JSON.
        """
    
    async def format_response_to_natural_language(self, sql_result: any, operation_type: str, user_request: str) -> str:
        """
        Few-Shot Learning + Chain-of-Thought para respuestas naturales
        """
        prompt = self._build_cot_response_prompt(sql_result, operation_type, user_request)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_cot_response_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            raw_response = response.choices[0].message.content.strip()
            cleaned_response = self._clean_encoding(raw_response)
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return self._get_fallback_response(user_request, sql_result)
        
    def _clean_encoding(self, text: str) -> str:
        """Limpiar problemas de codificación en el texto"""
        try:
            # Reemplazar caracteres comúnmente mal codificados
            encoding_fixes = {
                'Â¡': '¡', 'Â¿': '¿', 'Ã¡': 'á', 'Ã©': 'é', 
                'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã±': 'ñ',
                'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó',
                'Ãš': 'Ú', 'Ã‘': 'Ñ', 'Ã¼': 'ü', 'Ãœ': 'Ü'
            }
            
            cleaned = text
            for wrong, correct in encoding_fixes.items():
                cleaned = cleaned.replace(wrong, correct)
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning encoding: {e}")
            return text
    
    def _build_cot_response_prompt(self, sql_result: any, operation_type: str, user_request: str) -> str:
        """Chain-of-Thought para construir respuestas amables"""
        return f"""
        SOLICITUD_ORIGINAL: "{user_request}"
        OPERACIÓN_EJECUTADA: {operation_type}
        RESULTADO_BD: {sql_result}

        Sigue este proceso para construir la respuesta:

        PASO 1 - Reconocer solicitud:
        Comienza mencionando explícitamente qué solicitó el usuario.

        PASO 2 - Analizar resultado:
        ¿La operación fue exitosa? ¿Hubo errores? ¿Qué datos se obtuvieron?

        PASO 3 - Estructurar mensaje:
        - Saludo amable
        - Reconocimiento de solicitud  
        - Explicación del resultado
        - Información adicional relevante
        - Cierre cordial

        PASO 4 - Aplicar tono:
        Usar lenguaje natural, cálido y coloquial en español.

        Ahora construye la respuesta paso a paso.
        """
    
    def _get_cot_response_system_prompt(self) -> str:
        """Few-Shot Learning para respuestas que cumplen parámetro 6"""
        return """
        Eres un asistente de biblioteca que construye respuestas usando Chain-of-Thought.

        ## EJEMPLOS FEW-SHOT DE RESPUESTAS:

        EJEMPLO 1 - Reserva exitosa:
        "¡Hola! Recibí tu solicitud para reservar el libro '1984'. Me complace informarte que la reserva se realizó exitosamente. El libro estará disponible para ti durante los próximos 14 días. ¡Espero que lo disfrutes!"

        EJEMPLO 2 - Reserva fallida:
        "¡Hola! Recibí tu solicitud para reservar 'Cien años de soledad'. Lamentablemente, no pude completar la reserva porque el libro no está disponible en este momento. Te sugiero intentar de nuevo en unos días o preguntar por otros libros de Gabriel García Márquez."

        EJEMPLO 3 - Listado exitoso:
        "¡Hola! Recibí tu solicitud para ver los libros disponibles. Actualmente tenemos estos títulos disponibles:\n• '1984' por George Orwell\n• 'El Principito' por Antoine de Saint-Exupéry\n¿Te gustaría reservar alguno de ellos?"

        EJEMPLO 4 - Error de sistema:
        "¡Hola! Recibí tu solicitud para renovar una reserva. Veo que no tienes reservas activas en este momento. Si quieres hacer una nueva reserva, por favor dime qué libro te interesa."

        ## REGLAS ESTRICTAS:
        - SIEMPRE comienza reconociendo la solicitud específica
        - LUEGO presenta el resultado claramente
        - Usa lenguaje NATURAL, AMABLE y COLOQUIAL
        - Mantén el tono en español cálido y profesional
        - Incluye detalles relevantes pero sé conciso

        Genera solo la respuesta final, sin el razonamiento.
        """
    
    def _get_fallback_response(self, user_request: str, sql_result: any) -> str:
        """Respuesta de fallback que cumple con parámetro 6"""
        return f"¡Hola! Recibí tu solicitud: '{user_request}'. He procesado tu solicitud y el resultado fue: {sql_result}"
    
    def _parse_sql_response(self, response: str) -> dict:
        """Parsear respuesta de OpenAI de forma más robusta"""
        try:
            # Limpiar y extraer JSON de la respuesta
            cleaned_response = response.strip()
            
            # Buscar JSON en diferentes formatos
            json_patterns = [
                r'```json\s*(.*?)\s*```',  # ```json { ... } ```
                r'```\s*(.*?)\s*```',      # ``` { ... } ```
                r'(\{.*\})'                 # { ... } directamente
            ]
            
            json_match = None
            for pattern in json_patterns:
                match = re.search(pattern, cleaned_response, re.DOTALL)
                if match:
                    json_match = match.group(1) if pattern.startswith('```json') else match.group(1)
                    break
            
            if json_match:
                cleaned_response = json_match.strip()
            
            # Intentar parsear JSON
            parsed = json.loads(cleaned_response)
            
            # Validar estructura requerida
            if not all(key in parsed for key in ["sql", "operation_type", "explanation"]):
                raise ValueError("Estructura JSON incompleta")
                
            logger.info(f"✅ JSON parseado exitosamente: {parsed['operation_type']}")
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error parseando respuesta OpenAI: {str(e)}")
            logger.info(f"📝 Respuesta cruda: {response}")
            
            # Intentar extraer información útil incluso si el JSON está malformado
            fallback_sql = self._extract_fallback_sql(response)
            fallback_operation = self._extract_operation_type(response)
            
            return {
                "sql": fallback_sql,
                "operation_type": fallback_operation or "error",
                "explanation": f"Error parsing response: {str(e)}. Raw: {response[:200]}..."
            }

    def _extract_fallback_sql(self, response: str) -> str:
        """Extraer SQL de respuesta fallback"""
        # Buscar patrones SQL comunes
        sql_patterns = [
            r'SQL:\s*(.*?)(?=\n|$)',
            r'```sql\s*(.*?)\s*```',
            r'(SELECT.*?;)',
            r'(INSERT.*?;)', 
            r'(UPDATE.*?;)',
            r'(DELETE.*?;)'
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return "SELECT * FROM books WHERE available = 1"  # SQL por defecto

    def _extract_operation_type(self, response: str) -> str:
        """Extraer tipo de operación de respuesta fallback"""
        response_upper = response.upper()
        if 'RESERVE' in response_upper or 'RESERVAR' in response_upper:
            return "RESERVE_BOOK"
        elif 'RENEW' in response_upper or 'RENOVAR' in response_upper:
            return "RENEW_RESERVATION"
        elif 'CANCEL' in response_upper or 'CANCELAR' in response_upper:
            return "CANCEL_RESERVATION" 
        elif 'ADD' in response_upper or 'AGREGAR' in response_upper:
            return "ADD_BOOK"
        elif 'REMOVE' in response_upper or 'ELIMINAR' in response_upper:
            return "REMOVE_BOOK"
        elif 'LIST' in response_upper or 'MOSTRAR' in response_upper:
            return "LIST_BOOKS"
        else:
            return "LIST_BOOKS"  # Operación por defecto
    
    async def test_connection(self) -> bool:
        """Probar conexión con OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection. Respond with 'OK'"}],
                max_tokens=5
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False

llm_service = LLMService()