from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints  # Asegúrate de importar tus rutas

app = FastAPI(title="Asistente de Calendario IA")

# CONFIGURACIÓN DE CORS: Permite que React se conecte
origins = [
    "http://localhost:5173",  # Puerto por defecto de Vite/React
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, etc.
    allow_headers=["*"],  # Permite todos los encabezados
)

# Incluir las rutas que están en app/api/endpoints.py
app.include_router(endpoints.router)

@app.get("/")
def read_root():
    return {"message": "Backend de IA corriendo exitosamente 🚀"}