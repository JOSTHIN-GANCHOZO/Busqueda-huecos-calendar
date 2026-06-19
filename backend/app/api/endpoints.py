import os
import requests
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database.database import get_db, UsuarioToken

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# --- TRAEMOS LAS VARIABLES DEL .ENV ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# --- ESQUEMA DE VALIDACIÓN PARA REACT ---
class RequestCalendario(BaseModel):
    email: EmailStr
    calendarios_ids: List[str] = Field(..., min_items=1)
    duracion: int = Field(..., gt=0)
    rango_dias: int = Field(30, gt=0, le=90)


# ==========================================
# 1. RUTA LOGIN: PARA TU BOTÓN DE REACT
# ==========================================
@router.get("/login", summary="Genera la URL de inicio de sesión de Google")
def login():
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


# ==========================================
# 2. CALLBACK: PROCESA Y GUARDA EN BD
# ==========================================
@router.get("/callback", summary="Procesa el código de Google y guarda tokens")
def callback(code: str, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Código no proporcionado")

    # Intercambio de tokens (Tradicional con requests)
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    token_res = requests.post(token_url, data=token_data)
    token_json = token_res.json()
    
    if token_res.status_code != 200 or "error" in token_json:
        return RedirectResponse(url="http://localhost:5173/login?status=error")

    access_token = token_json.get("access_token")
    refresh_token = token_json.get("refresh_token")
    expires_in = token_json.get("expires_in", 3600)
    expiry_date = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Consultar el email del alumno
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_res = requests.get(userinfo_url, headers=headers)
    user_json = user_res.json()
    
    email = user_json.get("email")
    google_id = user_json.get("id")

    # Guardar o actualizar en Base de Datos
    usuario = db.query(UsuarioToken).filter(UsuarioToken.email == email).first()

    if usuario:
        usuario.access_token = access_token
        usuario.token_expiry = expiry_date
        if refresh_token:
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

    return RedirectResponse(url=f"http://localhost:5173/calendarios?status=success&email={email}")


# ==========================================
# 3. ENTRADA AL ALGORITMO (BUSCAR HUECOS)
# ==========================================
@router.post("/buscar-huecos", summary="Valida el usuario para la IA")
def buscar_huecos(datos: RequestCalendario, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioToken).filter(UsuarioToken.email == datos.email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no registrado. Inicie sesión con Google."
        )
    
    return {
        "status": "success",
        "mensaje": f"Tokens validados para {datos.email}.",
        "configuracion": {
            "calendarios_seleccionados": datos.calendarios_ids,
            "duracion_minutos": datos.duracion,
            "rango_busqueda_dias": datos.rango_dias
        }
    }