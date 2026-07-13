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

class EventosCalendarioRequest(BaseModel):
    email: EmailStr
    calendarios_ids: List[str] = Field(..., min_items=1, description="IDs de los calendarios a consultar")
    fecha_inicio: datetime = Field(..., description="Inicio del rango (puede incluir zona horaria o UTC)")
    fecha_fin: datetime = Field(..., description="Fin del rango (puede incluir zona horaria o UTC)")


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
@router.get(
    "/lista-calendarios",
    response_model=List[CalendarioResponse],
    summary="Obtiene todos los calendarios disponibles del usuario"
)
def obtener_calendarios(
    email: EmailStr,
    db: Session = Depends(get_db)
):

    # ============================
    # Buscar usuario
    # ============================
    usuario = db.query(UsuarioToken).filter(
        UsuarioToken.email == email
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no autenticado. Inicie sesión nuevamente."
        )

    try:

        service = obtener_servicio_calendar(usuario, db)

        respuesta = service.calendarList().list().execute()

        calendarios = respuesta.get("items", [])

        resultado = []

        for calendario in calendarios:

            resultado.append(
                CalendarioResponse(
                    id=calendario["id"],
                    nombre=calendario.get(
                        "summary",
                        "Calendario sin nombre"
                    )
                )
            )

        print("=" * 60)
        print("Usuario:", email)
        print("Calendarios encontrados:", len(resultado))

        for cal in resultado:
            print(cal.id, "-", cal.nombre)

        print("=" * 60)

        return resultado

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible obtener los calendarios: {str(e)}"
        )
    
# =========================================================================
# 4. OBTENER EVENTOS PARA LA VISTA DE CALENDARIO
# =========================================================================
@router.post(
    "/eventos-calendario",
    summary="Obtiene los eventos ocupados de los calendarios seleccionados"
)
def obtener_eventos_calendario(
    datos: EventosCalendarioRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    # ===========================
    # Validar usuario
    # ===========================
    usuario = db.query(UsuarioToken).filter(
        UsuarioToken.email == datos.email
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no autenticado. Inicie sesión nuevamente."
        )

    # ===========================
    # Normalizar fechas a UTC
    # ===========================
    fecha_inicio = datos.fecha_inicio
    fecha_fin = datos.fecha_fin

    if fecha_inicio.tzinfo is None:
        fecha_inicio = fecha_inicio.replace(tzinfo=timezone.utc)
    else:
        fecha_inicio = fecha_inicio.astimezone(timezone.utc)

    if fecha_fin.tzinfo is None:
        fecha_fin = fecha_fin.replace(tzinfo=timezone.utc)
    else:
        fecha_fin = fecha_fin.astimezone(timezone.utc)

    # ===========================
    # Consultar Google Calendar
    # ===========================
    try:

        eventos, zona_str = obtener_eventos_google(
            usuario=usuario,
            db=db,
            calendarios_ids=datos.calendarios_ids,
            desde=fecha_inicio,
            hasta=fecha_fin
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al consultar Google Calendar: {str(e)}"
        )

    # ===========================
    # Zona horaria del usuario
    # ===========================
    try:
        tz_usuario = pytz.timezone(zona_str)
    except Exception:
        tz_usuario = pytz.UTC

    eventos_serializados = []

    # ===========================
    # Convertir eventos
    # ===========================
    for evento in eventos:

        try:

            inicio = evento["start"]
            fin = evento["end"]

            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=timezone.utc)

            if fin.tzinfo is None:
                fin = fin.replace(tzinfo=timezone.utc)

            eventos_serializados.append({
                "id": evento.get("id"),
                "title": evento.get("title", "Sin título"),
                "description": evento.get("description", ""),
                "calendar_id": evento.get("calendar_id"),
                "color": evento.get("color"),
                "start": inicio.astimezone(tz_usuario).isoformat(),
                "end": fin.astimezone(tz_usuario).isoformat()
            })

        except Exception as e:
            print("Error procesando evento:", e)

    # ===========================
    # Logs de depuración
    # ===========================
    print("=" * 60)
    print("Usuario:", datos.email)
    print("Calendarios:", datos.calendarios_ids)
    print("Zona:", zona_str)
    print("Eventos enviados:", len(eventos_serializados))
    print("=" * 60)

    return {
        "status": "success",
        "zona_horaria": zona_str,
        "total": len(eventos_serializados),
        "eventos": eventos_serializados
    }
# =========================================================================
# 4. ALGORITMO: ENTRADA PRE-PROCESAMIENTO DE IA
# =========================================================================
@router.post(
    "/buscar-huecos",
    summary="Busca los mejores huecos disponibles utilizando el algoritmo Greedy"
)
def buscar_huecos(
    datos: RequestCalendario,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    # ==========================================
    # Validar usuario
    # ==========================================
    usuario = db.query(UsuarioToken).filter(
        UsuarioToken.email == datos.email
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no autenticado. Inicie sesión nuevamente."
        )

    # ==========================================
    # Definir rango preliminar
    # ==========================================
    ahora_utc = datetime.now(timezone.utc)

    fin_preliminar = ahora_utc + timedelta(days=datos.rango_dias)

    # ==========================================
    # Obtener eventos desde Google
    # ==========================================
    try:

        eventos_google, zona_str = obtener_eventos_google(
            usuario=usuario,
            db=db,
            calendarios_ids=datos.calendarios_ids,
            desde=ahora_utc,
            hasta=fin_preliminar
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No fue posible consultar Google Calendar: {str(e)}"
        )

    # ==========================================
    # Calcular inicio de búsqueda
    # ==========================================
    try:
        tz_usuario = pytz.timezone(zona_str)
    except Exception:
        tz_usuario = pytz.UTC

    ahora_local = datetime.now(tz_usuario)

    if ahora_local.hour >= 18:

        inicio_local = (
            ahora_local + timedelta(days=1)
        ).replace(
            hour=8,
            minute=0,
            second=0,
            microsecond=0
        )

    elif ahora_local.hour < 8:

        inicio_local = ahora_local.replace(
            hour=8,
            minute=0,
            second=0,
            microsecond=0
        )

    else:

        inicio_local = ahora_local

    inicio_busqueda = inicio_local.astimezone(timezone.utc)

    fin_busqueda = inicio_busqueda + timedelta(
        days=datos.rango_dias
    )

    # ==========================================
    # Ejecutar algoritmo Greedy
    # ==========================================
    resultado = calcular_hueco_greedy(
        eventos_ocupados=eventos_google,
        inicio_rango=inicio_busqueda,
        fin_rango=fin_busqueda,
        duracion_minutos=datos.duracion,
        zona_usuario=zona_str
    )

    if not resultado:

        return {
            "status": "success",
            "mensaje": "No se encontraron huecos disponibles.",
            "titulo_reunion": datos.titulo,
            "huecos_recomendados": []
        }

    print("=" * 60)
    print("Huecos encontrados:", len(resultado))
    print(resultado)
    print("=" * 60)

    return {
        "status": "success",
        "mensaje": f"Se encontraron {len(resultado)} horarios disponibles.",
        "algoritmo_aplicado": "Greedy Interval Scheduling",
        "titulo_reunion": datos.titulo,
        "huecos_recomendados": resultado,
        "total": len(resultado)
    }