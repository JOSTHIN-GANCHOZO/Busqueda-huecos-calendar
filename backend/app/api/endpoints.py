import os
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database.database import get_db, UsuarioToken
from app.core.google_cal import obtener_servicio_calendar

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# --- CONFIGURACIÓN DE ENTORNO ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# --- MODELOS DE VALIDACIÓN (PYDANTIC) ---
class RequestCalendario(BaseModel):
    email: EmailStr
    calendarios_ids: List[str] = Field(..., min_items=1, description="Lista de IDs de calendarios a evaluar")
    duracion: int = Field(..., gt=0, description="Duración del evento en minutos")
    rango_dias: int = Field(30, gt=0, le=90, description="Rango máximo de días de búsqueda")
    titulo: str = Field("Reunión de Trabajo", min_length=3, max_length=100, description="Título o asunto de la reunión")
class CalendarioResponse(BaseModel):
    id: str
    nombre: str


# =========================================================================
# 1. GENERAR URL DE AUTENTICACIÓN
# =========================================================================
@router.get("/login", summary="Genera la URL de consentimiento de Google OAuth2")
def login() -> Dict[str, str]:
    scopes = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events"
    ]
    
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={' '.join(scopes)}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {"auth_url": google_auth_url}


# =========================================================================
# 2. CALLBACK OAUTH2: PROCESAMIENTO E INSERCIÓN
# =========================================================================
@router.get("/callback", summary="Procesa el código de autorización e intercambia tokens")
def callback(code: str = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de autorización no provisto.")

    # Intercambio de Code por Tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        token_res = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_res.json()
        
        if token_res.status_code != 200 or "error" in token_json:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?status=error")

        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")
        expires_in = token_json.get("expires_in", 3600)
        expiry_date = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Obtener información del perfil del usuario (Email)
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_res = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        user_json = user_res.json()
        
        email = user_json.get("email")
        google_id = user_json.get("id")

        if not email:
            raise ValueError("No se pudo obtener el email desde la respuesta de Google")

        # Persistencia Atómica en base de datos
        usuario = db.query(UsuarioToken).filter(UsuarioToken.email == email).first()

        if usuario:
            usuario.access_token = access_token
            usuario.token_expiry = expiry_date
            if refresh_token:  # Conservar el original si Google no envía uno nuevo
                usuario.refresh_token = refresh_token
        else:
            usuario = UsuarioToken(
                google_id=google_id,
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=expiry_date
            )
            db.add(usuario)
            
        db.commit()
        return RedirectResponse(url=f"{FRONTEND_URL}/calendarios?status=success&email={email}")

    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"{FRONTEND_URL}/login?status=server_error&detail={str(e)}")


# =========================================================================
# 3. CONSUMO: LISTAR CALENDARIOS DISPONIBLES
# =========================================================================
@router.get("/lista-calendarios", response_model=List[CalendarioResponse], summary="Obtiene los calendarios de la cuenta del alumno")
def obtener_calendarios(email: EmailStr, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioToken).filter(UsuarioToken.email == email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado. Por favor, inicie sesión nuevamente."
        )

    try:
        # Invocar el cliente inteligente de core
        service = obtener_servicio_calendar(usuario, db)
        
        # Consumir el listado mediante la librería oficial de Google
        calendar_list = service.calendarList().list().execute()
        items = calendar_list.get("items", [])
        
        return [
            CalendarioResponse(id=item["id"], nombre=item.get("summary", "Calendario sin título"))
            for item in items
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al conectar con Google API: {str(e)}"
        )


# =========================================================================
# 4. ALGORITMO: ENTRADA PRE-PROCESAMIENTO DE IA
# =========================================================================
@router.post("/buscar-huecos", summary="Punto de control inicial para el motor de búsqueda de IA")
def buscar_huecos(datos: RequestCalendario, db: Session = Depends(get_db)) -> Dict[str, Any]:
    usuario = db.query(UsuarioToken).filter(UsuarioToken.email == datos.email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tokens de sesión ausentes. Autentíquese con Google."
        )
    
    return {
        "status": "success",
        "mensaje": f"Configuración y credenciales validadas para {datos.email}.",
        "payload": {
            "targets": datos.calendarios_ids,
            "duration_minutes": datos.duracion,
            "horizon_days": datos.rango_dias,
            "title": datos.titulo
        }
    }