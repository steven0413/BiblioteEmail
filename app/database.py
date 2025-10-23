import logging
from app.config import settings
import time

logger = logging.getLogger(__name__)

class Database:
    """
    Gestor de conexiones y operaciones de base de datos.
    
    Decisiones técnicas:
    - PyODBC para mejor compatibilidad con Azure SQL
    - Modo simulación para desarrollo sin BD
    - Reintentos automáticos para problemas de conexión transitorios
    """
    
    def __init__(self):
        self.connection_string = self._build_connection_string()
    
    def _build_connection_string(self):
        """Construir cadena de conexión para SQL Server"""
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={settings.db_server};"
            f"DATABASE={settings.db_database};"
            f"UID={settings.db_username};"
            f"PWD={settings.db_password};"
            f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
    
    def get_connection(self):
        """Obtener conexión con manejo robusto de errores"""
        try:
            import pyodbc
            # conexión con reintentos
            for attempt in range(3):
                try:
                    conn = pyodbc.connect(self.connection_string)
                    logger.info("✅ Conexión a BD establecida")
                    return conn
                except pyodbc.OperationalError as e:
                    if "timeout" in str(e).lower() and attempt < 2:
                        logger.warning(f"⏰ Timeout, reintentando... ({attempt + 1}/3)")
                        time.sleep(2)
                        continue
                    raise
            
        except ImportError:
            logger.warning("🔧 PyODBC no disponible - modo simulación activado")
            return MockConnection()
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            logger.info("🔧 Modo simulación activado")
            return MockConnection()
    
    def init_database(self):
        """Inicializar tablas si no existen"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            tables_sql = [
                """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='books' AND xtype='U')
                CREATE TABLE books (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    title NVARCHAR(255) NOT NULL,
                    author NVARCHAR(255) NOT NULL,
                    isbn NVARCHAR(20),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    available BIT DEFAULT 1
                )
                """,
                """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='reservations' AND xtype='U')
                CREATE TABLE reservations (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    book_id INT FOREIGN KEY REFERENCES books(id),
                    user_email NVARCHAR(255) NOT NULL,
                    reserved_at DATETIME2 DEFAULT GETDATE(),
                    renewed_at DATETIME2,
                    expires_at DATETIME2,
                    active BIT DEFAULT 1
                )
                """
            ]
            
            for sql in tables_sql:
                cursor.execute(sql)
            conn.commit()
            logger.info("✅ Tablas inicializadas correctamente")
            
        except Exception as e:
            logger.warning(f"⚠️ BD en modo simulación: {e}")


class MockConnection:
    def cursor(self):
        return MockCursor()
    def commit(self):
        pass
    def close(self):
        pass

class MockCursor:
    def __init__(self):
        self.rowcount = 1
    def execute(self, query, params=None):
        logger.info(f"🔧 [SIMULACIÓN] Ejecutando: {query[:100]}...")
        return self
    def fetchall(self):
        return [
            {"id": 1, "title": "Cien años de soledad", "author": "Gabriel García Márquez", "available": True}
        ]
    def fetchone(self):
        return {"id": 1, "title": "Cien años de soledad", "author": "Gabriel García Márquez", "available": True}
    def close(self):
        pass


db = Database()