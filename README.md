# 🤖 Biblioteca Email Automation

## 🎯 ¿Qué problema resuelvo?

Soy un sistema que automatiza la gestión de una biblioteca mediante correo electrónico. 
Los usuarios me envían emails en español (ej: "Quiero reservar 1984") y yo:

1. **Comprendo** lo que realmente quieren usando IA
2. **Convierto** su mensaje a consultas SQL seguras  
3. **Ejecuto** las operaciones en la base de datos
4. **Respondo** con una explicación clara y amable

## 🚀 Características principales

### ✨ Procesamiento Inteligente
- **Lenguaje natural** → Los usuarios hablan como humanos, no como robots
- **OpenAI GPT-4** → Mejor comprensión del español y contexto
- **Chain-of-Thought** → Razonamiento paso a paso para mayor precisión

### 🛡️ Robustez y Seguridad
- **Validaciones estrictas** → Prevengo inyecciones SQL y datos corruptos
- **Manejo elegante de errores** → El sistema nunca se cae, siempre responde
- **Modo simulación** → Funciono incluso cuando los servicios externos fallan

### 📧 Comunicación Humana
- **Respuestas naturales** → No soy un robot, hablo como persona
- **Tono amable y coloquial** → Trato a los usuarios con respeto y calidez
- **Explicaciones claras** → Los usuarios entienden qué pasó con su solicitud

## 🏗️ Arquitectura - Decisiones que tomé

### ¿Por qué FastAPI?
```python
# Elegí FastAPI porque:
# - Es rápido (muy importante para APIs)
# - Tiene documentación automática (Swagger)
# - Soporta async/await nativamente
# - La comunidad es excelente

app/
├── main.py          # Orquestador principal - endpoints y rutas
├── config.py        # Configuración centralizada - una sola fuente de verdad
├── database.py      # Todo lo relacionado con BD - separación clara
├── llm_service.py   # Cerebro del sistema - procesamiento de lenguaje
├── email_processor.py # Comunicación con email - entrada/salida
└── models.py        # Modelos de datos - validación y estructura

Decidí esta separación porque: Cada archivo tiene una responsabilidad única y clara. Si falla el email, la IA sigue funcionando. Si falla la IA, la base de datos sigue respondiendo.

🔧 Instalación y Configuración
Requisitos del sistema
Python 3.11+ (probé con 3.11, 3.12 y 3.13 - 3.14 tiene warnings)

Azure SQL Database o SQL Server local

Cuenta de Gmail (funciona mejor con apps)

API Key de OpenAI (GPT-4 tiene mejor español)

Configuración rápida
# 1. Clonar y entrar al directorio
cd biblioteca-email

# 2. Instalar dependencias (las justas y necesarias)
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales

# 4. Ejecutar (sin reload por ahora)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Variables de entorno
# Base de datos - Azure SQL es más estable que local
DB_SERVER=tu-servidor.database.windows.net
DB_DATABASE=biblioteca_db
DB_USERNAME=admin
DB_PASSWORD=contraseña-segura

# Email - Gmail es lo que más entienden los usuarios
IMAP_USERNAME=tu-email@gmail.com
IMAP_PASSWORD=contraseña-de-app  # ¡No la personal!

# OpenAI - GPT-4 vale la pena el costo
OPENAI_API_KEY=sk-tu-key-real
OPENAI_MODEL=gpt-4

🎮 Cómo usarme
# Ejecutar el servidor y visitar:
http://localhost:8000/api/docs

Operaciones que entiendo:
"Reservar [libro]" → Creo una reserva si está disponible
"Renovar mi reserva de [libro]" → Extiendo el plazo
"Cancelar reserva de [libro]" → Marco como inactiva
"Ver libros de [autor]" → Listo disponibles
"¿Qué libros tienen?" → Muestro todo el catálogo