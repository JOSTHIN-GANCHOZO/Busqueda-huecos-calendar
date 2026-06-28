import os
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

# --- CONFIGURACIÓN DE ENTORNO ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def obtener_servicio_calendar(usuario_db_record, db_session: Session):
    """
    Construye un cliente autenticado para la API de Google Calendar.
    Si el access_token del usuario ha expirado, utiliza el refresh_token 
    para renovarlo automáticamente y actualiza la base de datos.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("Las credenciales de Google Client ID/Secret no están configuradas en el .env")

    # 1. Normalizar la fecha de expiración para compatibilidad (Google espera UTC naive o consciente)
    expiry_date = usuario_db_record.token_expiry
    if expiry_date and expiry_date.tzinfo is not None:
        expiry_date = expiry_date.astimezone(timezone.utc).replace(tzinfo=None)

    # 2. Reconstruir el objeto de credenciales OAuth2
    creds = Credentials(
        token=usuario_db_record.access_token,
        refresh_token=usuario_db_record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        expiry=expiry_date
    )

    # 3. Guardián de Expiración: Refresco automático y transparente
    if creds and creds.expired and creds.refresh_token:
        print(f"🔄 Token expirado para {usuario_db_record.email}. Solicitando renovación...")
        try:
            creds.refresh(Request())
            
            # Actualizar el registro en caliente
            usuario_db_record.access_token = creds.token
            if creds.expiry:
                usuario_db_record.token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
            else:
                usuario_db_record.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=3600)
            
            db_session.commit()
            print(f"✅ tokens.db sincronizada exitosamente para {usuario_db_record.email}.")
            
        except Exception as e:
            db_session.rollback()
            print(f"❌ Falló el refresco automático de Google OAuth: {str(e)}")
            raise e

    # 4. Retornar el cliente listo para interactuar con los recursos
    return build("calendar", "v3", credentials=creds)