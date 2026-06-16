from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import List

router = APIRouter()

# Esquema para validar los datos que se enviarán desde React
class RequestCalendario(BaseModel):
    usuarios: List[EmailStr]  # Recibe una lista de correos válidos
    duracion: int             # Duración de la reunión en minutos

@router.post("/api/buscar-huecos")
async def buscar_huecos(datos: RequestCalendario):
    return {
        "status": "success",
        "recibido": {
            "usuarios": datos.usuarios,
            "duracion": datos.duracion
        },
        "mensaje": "Conexión exitosa con el Backend"
    }