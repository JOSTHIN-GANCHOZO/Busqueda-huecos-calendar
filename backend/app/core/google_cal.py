import os
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def obtener_servicio_calendar(usuario, db: Session):
    """Cliente autenticado de Google Calendar con refresco automático de token."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("Credenciales de Google no configuradas en .env")

    expiry = usuario.token_expiry
    if expiry and expiry.tzinfo:
        expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

    creds = Credentials(
        token=usuario.access_token,
        refresh_token=usuario.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        expiry=expiry
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        usuario.access_token = creds.token
        usuario.token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else datetime.now(timezone.utc) + timedelta(seconds=3600)
        db.commit()

    return build("calendar", "v3", credentials=creds)


def obtener_eventos_google(usuario, db: Session, calendarios_ids: list, desde: datetime, hasta: datetime):
    """Devuelve (eventos_en_utc, zona_horaria) de los calendarios indicados con paginación."""
    service = obtener_servicio_calendar(usuario, db)
    eventos = []
    
    # Detectar zona horaria del usuario
    zona = "America/Guayaquil"
    if calendarios_ids:
        try:
            zona = service.calendars().get(calendarId=calendarios_ids[0]).execute().get('timeZone', zona)
        except:
            pass

    # Formato UTC explícito para Google
    time_min = desde.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = hasta.strftime("%Y-%m-%dT%H:%M:%SZ")

    for cal_id in calendarios_ids:
        page_token = None
        while True:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()

            for item in result.get('items', []):
                inicio = item.get('start', {}).get('dateTime') or item.get('start', {}).get('date')
                fin = item.get('end', {}).get('dateTime') or item.get('end', {}).get('date')
                
                if inicio and fin:
                    eventos.append({
                        "start": datetime.fromisoformat(inicio).astimezone(timezone.utc),
                        "end": datetime.fromisoformat(fin).astimezone(timezone.utc)
                    })

            page_token = result.get('nextPageToken')
            if not page_token:
                break

    return eventos, zona