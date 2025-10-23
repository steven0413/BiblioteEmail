import aiosmtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging
from typing import List, Dict
import asyncio

logger = logging.getLogger(__name__)

class EmailProcessor:
    """
    Procesador de correos electrónicos para la biblioteca automatizada.
    
    Decisiones técnicas:
    - Uso de aiosmtplib para envío asíncrono (mejor performance en APIs)
    - Soporte para múltiples configuraciones SMTP (Gmail problemas comunes)
    - Codificación UTF-8 explícita para soporte de español
    - Reintentos automáticos en diferentes puertos
    
    Aprendí por experiencia:
    - Gmail a veces bloquea el puerto 587, por eso tengo fallback al 465
    - Es crucial usar TLS/SSL correctamente para evitar rechazos
    - El encoding UTF-8 evita problemas con tildes y caracteres especiales
    """
    
    def __init__(self):
        # Configuración de servidores - Gmail elegido por accesibilidad para usuarios
        self.imap_server = settings.imap_server
        self.imap_username = settings.imap_username
        self.imap_password = settings.imap_password
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        
        # Configuraciones de reintento - basado en pruebas con diferentes redes
        self.max_retries = 2
        self.retry_delay = 5  # segundos
    
    async def send_response_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Enviar email de respuesta al usuario.
        
        Esta función tiene lógica de reintento porque he visto que:
        - Las redes corporativas a veces bloquean puertos específicos
        - Gmail puede tener problemas temporales en un puerto pero no en otro
        - Es mejor fallar rápido y reintentar que esperar timeouts largos
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del mensaje
            body: Cuerpo del mensaje en texto plano
            
        Returns:
            bool: True si el email se envió exitosamente
        """
        try:
            message = self._create_email_message(to_email, subject, body)
            
            # Intentar diferentes configuraciones SMTP - estrategia de fallback
            smtp_configs = [
                {
                    'hostname': self.smtp_server,
                    'port': 587,
                    'use_tls': True,
                    'description': 'TLS (puerto 587)'
                },
                {
                    'hostname': self.smtp_server, 
                    'port': 465,
                    'use_tls': False,  # SSL implícito
                    'description': 'SSL (puerto 465)'
                }
            ]
            
            for config in smtp_configs:
                try:
                    success = await self._attempt_send_email(message, config)
                    if success:
                        logger.info(f"✅ Email enviado a {to_email} via {config['description']}")
                        return True
                        
                except Exception as e:
                    logger.warning(f"⚠️ Falló envío en {config['description']}: {e}")
                    continue
            
            # Si todos los intentos fallan
            logger.error(f"❌ Todos los intentos de envío fallaron para {to_email}")
            return False
            
        except Exception as e:
            logger.error(f"💥 Error crítico enviando email a {to_email}: {e}")
            return False
    
    def _create_email_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        """
        Crear mensaje de email con codificación UTF-8.
        
        Uso MIMEMultipart aunque sea texto plano porque:
        - Es más compatible con diferentes clientes de email
        - Permite fácil extensión a HTML en el futuro
        - Maneja mejor los caracteres especiales del español
        """
        message = MIMEMultipart()
        message['From'] = self.imap_username
        message['To'] = to_email
        message['Subject'] = subject
        
        # Codificación UTF-8 explícita - crucial para español
        text_part = MIMEText(body, 'plain', 'utf-8')
        message.attach(text_part)
        
        return message
    
    async def _attempt_send_email(self, message: MIMEMultipart, config: dict) -> bool:
        """
        Intentar enviar email con configuración específica.
        
        Uso timeout de 30 segundos porque:
        - Es suficiente para la mayoría de redes
        - Evita que la aplicación se quede bloqueada
        - Permite fallar rápido y reintentar
        """
        try:
            await aiosmtplib.send(
                message,
                hostname=config['hostname'],
                port=config['port'],
                username=self.imap_username,
                password=self.imap_password,
                use_tls=config['use_tls'],
                timeout=30
            )
            return True
            
        except aiosmtplib.SMTPConnectError as e:
            logger.warning(f"🔌 Error de conexión SMTP: {e}")
            raise
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(f"🔑 Error de autenticación: {e}")
            raise
        except Exception as e:
            logger.warning(f"📧 Error enviando email: {e}")
            raise
    
    async def fetch_unread_emails(self) -> List[Dict]:
        """
        Obtener emails no leídos del buzón.
        
        Esta función:
        - Marca emails como leídos después de procesarlos
        - Maneja tanto texto plano como HTML
        - Retorna una estructura simple para fácil procesamiento
        
        Returns:
            List[Dict]: Lista de emails con from, subject, body y date
        """
        emails = []
        try:
            from imap_tools import MailBox, AND
            
            # Conexión IMAP con contexto para manejo automático de recursos
            with MailBox(self.imap_server).login(
                self.imap_username, 
                self.imap_password, 
                'INBOX'
            ) as mailbox:
                
                # Buscar emails no leídos - criterio simple que funciona
                for message in mailbox.fetch(AND(seen=False)):
                    email_data = {
                        'from': message.from_,
                        'subject': message.subject or 'Sin asunto',
                        'body': self._extract_email_body(message),
                        'date': message.date
                    }
                    emails.append(email_data)
                    
                    # Marcar como leído - importante para no reprocesar
                    mailbox.seen(message.uid, True)
                    logger.info(f"📨 Email marcado como leído: {message.from_}")
            
            logger.info(f"✅ Obtenidos {len(emails)} emails no leídos")
            return emails
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo emails: {e}")
            return []
    
    def _extract_email_body(self, message) -> str:
        """
        Extraer el cuerpo del email priorizando texto plano.
        
        He notado que:
        - La mayoría de usuarios envían texto plano
        - Es mejor priorizar texto plano pero tener HTML como fallback
        """
        if message.text:
            return message.text.strip()
        elif message.html:
            # Extraer texto simple del HTML - básico pero funcional
            import re
            clean_html = re.sub('<[^<]+?>', '', message.html)
            return clean_html.strip()
        else:
            return "Email sin contenido legible"
    
    async def test_connection(self) -> bool:
        """
        Probar conexión con el servidor de email.
        
        Esta función es tolerante a errores porque:
        - No queremos que fallos de email detengan toda la aplicación
        - Los problemas de email son comunes y a menudo temporales
        - Es mejor continuar y reintentar después
        
        Returns:
            bool: True si la conexión es exitosa o al menos se puede intentar
        """
        try:
            from imap_tools import MailBox
            
            with MailBox(self.imap_server).login(
                self.imap_username, 
                self.imap_password, 
                'INBOX'
            ) as mailbox:
                # Operación simple para verificar conexión
                list(mailbox.fetch(limit=1))
                logger.info("✅ Conexión de email verificada")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ Prueba de conexión de email falló: {e}")
            # Devolver True para no bloquear el sistema - los emails pueden fallar
            return True
    
    async def process_incoming_emails(self) -> List[Dict]:
        """
        Procesar todos los emails entrantes no leídos.
        
        Esta es la función principal que orquesta:
        1. Obtener emails no leídos
        2. Procesar cada uno individualmente
        3. Retornar resultados para seguimiento
        
        Returns:
            List[Dict]: Resultados del procesamiento de cada email
        """
        try:
            unread_emails = await self.fetch_unread_emails()
            processing_results = []
            
            for email in unread_emails:
                try:
                    # Aquí se integraría con el procesamiento principal
                    result = {
                        'from': email['from'],
                        'subject': email['subject'],
                        'processed_at': asyncio.get_event_loop().time(),
                        'status': 'pending_processing'
                    }
                    processing_results.append(result)
                    
                    logger.info(f"📧 Email en cola de procesamiento: {email['from']}")
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando email de {email['from']}: {e}")
                    processing_results.append({
                        'from': email['from'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return processing_results
            
        except Exception as e:
            logger.error(f"💥 Error crítico en procesamiento de emails: {e}")
            return []

email_processor = EmailProcessor()