from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints  # Tus rutas actuales
from app.database.database import init_db  # ← NUEVA LINEA: Importamos el inicializador de la DB
import dotenv  # ← AGREGAR ESTA LÍNEA
from contextlib import asynccontextmanager

# ← AGREGAR ESTA LÍNEA: Carga las llaves del .env antes de cualquier otra cosa
dotenv.load_dotenv()

# CONFIGURACIÓN DE CORS: Permite que React se conecte
origins = [
    "http://localhost:5173",  # Puerto por defecto de Vite/React
    "http://127.0.0.1:5173",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lo que se ejecuta al encender el servidor
    init_db()
    yield
    # Lo que se ejecuta al apagar el servidor (si necesitas cerrar conexiones)

app = FastAPI(title="Asistente de Calendario IA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, etc.
    allow_headers=["*"],  # Permite todos los encabezados
)

# Incluir las rutas que están en app/api/endpoints.py
app.include_router(endpoints.router)