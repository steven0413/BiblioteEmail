import logging
from app.config import settings

logger = logging.getLogger(__name__)

class Database:
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
        """Obtener conexión - modo simulación mejorado"""
        try:
            import pyodbc
            conn = pyodbc.connect(self.connection_string)
            return conn
        except ImportError:
            logger.warning("pyodbc no disponible - modo simulación activado")
            return MockConnection()
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            logger.info("Modo simulación activado para desarrollo")
            return MockConnection()
    
    def init_database(self):
        """Inicializar tablas - funciona en modo real o simulación"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Scripts de creación de tablas
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
            logger.info("✅ Tablas de base de datos inicializadas")
            
        except Exception as e:
            logger.warning(f"⚠️ Base de datos en modo simulación: {e}")

class MockConnection:
    """Conexión simulada mejorada"""
    def cursor(self):
        return MockCursor()
    
    def commit(self):
        pass
    
    def close(self):
        pass

class MockCursor:
    """Cursor simulado con datos de ejemplo y rowcount"""
    def __init__(self):
        self.rowcount = 1  # Inicializar rowcount para operaciones DML

    def execute(self, query, params=None):
        logger.info(f"🔧 [MODO SIMULACIÓN] Ejecutando: {query[:100]}...")
        
        # Simular rowcount basado en el tipo de query
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            self.rowcount = 0  # SELECT no afecta rows
        else:
            self.rowcount = 1  # INSERT/UPDATE/DELETE afecta 1 row
        
        return self
    
    def fetchall(self):
        # Datos de ejemplo para demostración
        return [
            {"id": 1, "title": "Cien años de soledad", "author": "Gabriel García Márquez", "available": True},
            {"id": 2, "title": "1984", "author": "George Orwell", "available": True},
            {"id": 3, "title": "Don Quijote", "author": "Miguel de Cervantes", "available": False}
        ]
    
    def fetchone(self):
        return {"id": 1, "title": "Cien años de soledad", "author": "Gabriel García Márquez", "available": True}
    
    def close(self):
        pass

db = Database()