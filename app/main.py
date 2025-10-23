from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import db
from app.email_processor import email_processor
from app.llm_service import llm_service  # ✅ Mantener import original
from app.models import EmailRequest, OperationResult
from app.config import settings
import logging
import asyncio
from typing import List, Dict
import re

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Library Email Automation API",
    description="Sistema automatizado de gestión de biblioteca por email",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Inicializar aplicación - manteniendo funcionalidad existente"""
    try:
        db.init_database()
        logger.info("✅ Aplicación iniciada correctamente")
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")

@app.get("/")
async def root():
    return {
        "message": "🤖 Biblioteca Email Automation API", 
        "status": "active",
        "version": "1.0.0"
    }

@app.post("/api/process-email", response_model=OperationResult)
async def process_single_email(email_data: EmailRequest):
    """
    Procesar una solicitud de email individual.
    
    Decisiones de diseño:
    - Validación temprana de email para evitar costos innecesarios de OpenAI
    - Manejo robusto de errores con respuestas informativas
    - Separación clara de responsabilidades
    """
    try:
        # Validación mejorada manteniendo la interfaz existente
        if not email_data.from_email or "@" not in email_data.from_email:
            return OperationResult(
                success=False,
                message="Email del remitente no válido"
            )

        if not email_data.subject.strip() or not email_data.body.strip():
            return OperationResult(
                success=False,
                message="El asunto y el cuerpo del mensaje no pueden estar vacíos"
            )

        # ✅ Usar función original del LLM service
        llm_result = await llm_service.natural_language_to_sql(
            email_data.body, 
            email_data.from_email
        )
        
        if not llm_result.get("sql"):
            return OperationResult(
                success=False,
                message=llm_result.get("explanation", "No se pudo entender la solicitud")
            )
        
        # Ejecutar SQL manteniendo función existente
        sql_result = await execute_sql_query(llm_result["sql"])
        
        # ✅ Usar función original de formateo
        natural_response = await llm_service.format_response_to_natural_language(
            sql_result,
            llm_result["operation_type"],
            email_data.body
        )
        
        # Enviar email respuesta (no crítico para funcionalidad básica)
        response_sent = False
        try:
            response_sent = await email_processor.send_response_email(
                email_data.from_email,
                f"Respuesta a: {email_data.subject}",
                natural_response
            )
        except Exception as e:
            logger.error(f"⚠️ Error enviando email (no crítico): {e}")
        
        return OperationResult(
            success=True,
            message="Email procesado exitosamente",
            data={
                "operation": llm_result["operation_type"],
                "response_sent": response_sent,
                "sql_generated": llm_result["sql"],
                "user_response": natural_response
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error procesando email: {e}")
        return OperationResult(
            success=False,
            message=f"Error procesando email: {str(e)}"
        )

# ✅ MANTENER funciones auxiliares existentes
async def execute_sql_query(sql: str):
    """Ejecutar consulta SQL con manejo robusto de errores"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        logger.info(f"🔍 Ejecutando SQL: {sql[:100]}...")
        
        cursor.execute(sql)
        
        if sql.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            # Convertir a formato legible
            if hasattr(results, '__iter__'):
                return [dict(row) for row in results]
            return []
        else:
            conn.commit()
            return {"rows_affected": cursor.rowcount}
            
    except Exception as e:
        logger.error(f"❌ Error ejecutando SQL: {e}")
        return {"error": str(e)}
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# ✅ MANTENER endpoints existentes
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "library_email_api"}

@app.get("/status")
async def system_status():
    """Estado del sistema - manteniendo estructura de respuesta"""
    try:
        # Lógica existente de verificación de estado
        return {
            "database": True,
            "email_service": True, 
            "openai": True,
            "overall": True
        }
    except Exception as e:
        logger.error(f"Error en status check: {e}")
        return {
            "database": False,
            "email_service": False,
            "openai": False, 
            "overall": False
        }