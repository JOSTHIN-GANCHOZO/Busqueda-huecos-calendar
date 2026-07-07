import os
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import pytz

from app.database.database import get_db, UsuarioToken
from app.core.google_cal import obtener_servicio_calendar
from app.ia.search import calcular_hueco_greedy
from app.core.google_cal import obtener_eventos_google

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
def callback(code: str = None, error: str = None, db: Session = Depends(get_db)):
    # Si el usuario canceló la autenticación en Google
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?status=cancelled")
    
    # Si no hay código ni error (caso inesperado)
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?status=error")
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
        print(f"Error en callback: {str(e)}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?status=server_error")


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
    # 1. Validar el usuario en SQLite
    usuario = db.query(UsuarioToken).filter(UsuarioToken.email == datos.email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tokens de sesión ausentes. Autentíquese con Google."
        )

    # 2. DEFINIR UN RANGO INICIAL AMPLIO (luego ajustaremos el inicio exacto)
    #    Usamos UTC ahora como referencia, pero luego refinaremos con la zona del usuario.
    ahora_utc = datetime.now(timezone.utc)
    # Rango preliminar amplio: desde este momento hasta N días después
    fin_busqueda_preliminar = ahora_utc + timedelta(days=datos.rango_dias)

    try:
        # 3. CONSUMO REAL DE GOOGLE CALENDAR (nos devuelve también la zona horaria)
        eventos_real_google, zona_str = obtener_eventos_google(
            usuario=usuario,
            db=db,
            calendarios_ids=datos.calendarios_ids,
            desde=ahora_utc,
            hasta=fin_busqueda_preliminar
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error crítico al conectar con Google Calendar: {str(e)}"
        )
    
    # 4. AJUSTAR EL INICIO DE BÚSQUEDA USANDO LA ZONA HORARIA DEL USUARIO
    tz_usuario = pytz.timezone(zona_str)
    ahora_local = datetime.now(tz_usuario)

    if ahora_local.hour >= 18:
        inicio_local = (ahora_local + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    elif ahora_local.hour < 8:
        inicio_local = ahora_local.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        inicio_local = ahora_local

    inicio_busqueda = inicio_local.astimezone(timezone.utc)
    fin_busqueda = inicio_busqueda + timedelta(days=datos.rango_dias)

    # 5. EJECUCIÓN DEL MOTOR DE IA (ALGORITMO GREEDY)
    resultado_optimo = calcular_hueco_greedy(
        eventos_ocupados=eventos_real_google,
        inicio_rango=inicio_busqueda,
        fin_rango=fin_busqueda,
        duracion_minutos=datos.duracion,
        zona_usuario=zona_str
    )

    # 6. RESPUESTA
    if resultado_optimo:
        return {
            "status": "success",
            "algoritmo_aplicado": "Greedy Interval Scheduling",
            "mensaje": f"Horario óptimo calculado con éxito para {datos.email}.",
            "titulo_reunion": datos.titulo,
            "horario_principal_recomendado": resultado_optimo
        }

    return {
        "status": "error",
        "mensaje": "No se encontraron huecos libres que cumplan con los requisitos en el rango de días seleccionado."
    }