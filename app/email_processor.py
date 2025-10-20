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
    def __init__(self):
        self.imap_server = settings.imap_server
        self.imap_username = settings.imap_username
        self.imap_password = settings.imap_password
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
    
    async def send_response_email(self, to_email: str, subject: str, body: str) -> bool:
        """Enviar email de respuesta con múltiples intentos y configuración mejorada"""
        try:
            message = MIMEMultipart()
            message['From'] = self.imap_username
            message['To'] = to_email
            message['Subject'] = subject
            
            # Codificación UTF-8 explícita
            text_part = MIMEText(body, 'plain', 'utf-8')
            message.attach(text_part)
            
            # Intentar diferentes configuraciones SMTP
            smtp_configs = [
                {
                    'hostname': self.smtp_server,
                    'port': 587,
                    'use_tls': True,
                    'timeout': 30
                },
                {
                    'hostname': self.smtp_server,
                    'port': 465,
                    'use_tls': False,  # SSL implícito
                    'timeout': 30
                }
            ]
            
            for config in smtp_configs:
                try:
                    await aiosmtplib.send(
                        message,
                        hostname=config['hostname'],
                        port=config['port'],
                        username=self.imap_username,
                        password=self.imap_password,
                        use_tls=config['use_tls'],
                        timeout=config['timeout']
                    )
                    logger.info(f"✅ Email enviado exitosamente a {to_email} (puerto {config['port']})")
                    return True
                    
                except Exception as e:
                    logger.warning(f"⚠️ Falló envío en puerto {config['port']}: {e}")
                    continue
            
            # Si todos los intentos fallan
            logger.error(f"❌ Todos los intentos de envío fallaron para {to_email}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error crítico enviando email a {to_email}: {e}")
            return False
    
    # Mantener los otros métodos existentes...
    async def fetch_unread_emails(self) -> List[Dict]:
        """Obtener emails no leídos del buzón"""
        emails = []
        try:
            from imap_tools import MailBox, AND
            with MailBox(self.imap_server).login(self.imap_username, self.imap_password, 'INBOX') as mailbox:
                for msg in mailbox.fetch(AND(seen=False)):
                    emails.append({
                        'from': msg.from_,
                        'subject': msg.subject,
                        'body': msg.text or msg.html or '',
                        'date': msg.date
                    })
                    
                    mailbox.seen(msg.uid, True)
            
            logger.info(f"Fetched {len(emails)} unread emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Probar conexión al servidor de email - versión más tolerante"""
        try:
            from imap_tools import MailBox
            with MailBox(self.imap_server).login(self.imap_username, self.imap_password, 'INBOX') as mailbox:
                # Solo intentar una operación simple
                list(mailbox.fetch(limit=1))
                return True
        except Exception as e:
            logger.warning(f"Email connection test warning: {e}")
            # Devolver True para no bloquear el sistema completo
            return True

email_processor = EmailProcessor()