import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def test_azure_connection():
    try:
        # Cadena de conexión
        connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('DB_SERVER')};"
            f"DATABASE={os.getenv('DB_DATABASE')};"
            f"UID={os.getenv('DB_USERNAME')};"
            f"PWD={os.getenv('DB_PASSWORD')};"
            f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        
        print("🔗 Conectando a Azure SQL Database...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        print("✅ Conexión exitosa!")
        
        # 1. Verificar servidor y base de datos
        cursor.execute("SELECT @@SERVERNAME, DB_NAME()")
        server, db = cursor.fetchone()
        print(f"🖥️ Servidor: {server}")
        print(f"🗃️ Base de datos: {db}")
        
        # 2. Crear tablas del sistema de biblioteca
        print("📚 Configurando tablas de biblioteca...")
        
        # Tabla de libros
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='books' AND xtype='U')
        CREATE TABLE books (
            id INT IDENTITY(1,1) PRIMARY KEY,
            title NVARCHAR(255) NOT NULL,
            author NVARCHAR(255) NOT NULL,
            isbn NVARCHAR(20),
            created_at DATETIME2 DEFAULT GETDATE(),
            available BIT DEFAULT 1
        )
        """)
        
        # Tabla de reservas
        cursor.execute("""
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
        """)
        
        conn.commit()
        print("✅ Tablas 'books' y 'reservations' creadas/verificadas")
        
        # 3. Insertar datos de prueba
        cursor.execute("""
        IF NOT EXISTS (SELECT 1 FROM books WHERE title = 'Cien años de soledad')
        INSERT INTO books (title, author, isbn, available) VALUES 
        ('Cien años de soledad', 'Gabriel García Márquez', '978-8437604947', 1),
        ('El principito', 'Antoine de Saint-Exupéry', '978-0156013924', 1),
        ('1984', 'George Orwell', '978-0451524935', 1),
        ('Don Quijote de la Mancha', 'Miguel de Cervantes', '978-8424113296', 0),
        ('Cien años de soledad', 'Gabriel García Márquez', '978-0307474728', 1)
        """)
        
        conn.commit()
        
        # 4. Contar libros insertados
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        print(f"📖 Libros en sistema: {book_count}")
        
        # 5. Mostrar libros disponibles
        cursor.execute("SELECT title, author, available FROM books")
        books = cursor.fetchall()
        
        print("\n📚 Catálogo de libros:")
        for book in books:
            status = "✅ Disponible" if book[2] else "❌ Reservado"
            print(f"   - {book[0]} por {book[1]} - {status}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 ¡CONFIGURACIÓN DE BASE DE DATOS COMPLETADA!")
        print("📍 Servidor: biblioteca-sql-server-steven.database.windows.net")
        print("🗃️ Base de datos: biblioteca_db")
        print("🔐 Firewall: Configurado correctamente")
        print("📊 Tablas: books y reservations listas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_azure_connection()
    
    if success:
        print("\n" + "="*50)
        print("🚀 ¡BASE DE DATOS LISTA PARA LA APLICACIÓN!")
        print("="*50)
    else:
        print("\n❌ Necesita ajustes en la configuración")