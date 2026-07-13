import os
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


def obtener_servicio_calendar(usuario, db: Session):
    """
    Devuelve un cliente autenticado de Google Calendar.
    Si el access token expiró lo refresca automáticamente.
    """

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError(
            "No se encontraron GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en el archivo .env"
        )

    expiry = usuario.token_expiry

    if expiry:
        if expiry.tzinfo:
            expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

    creds = Credentials(
        token=usuario.access_token,
        refresh_token=usuario.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        expiry=expiry,
    )

    if creds.expired and creds.refresh_token:

        creds.refresh(Request())

        usuario.access_token = creds.token

        usuario.token_expiry = (
            creds.expiry.replace(tzinfo=timezone.utc)
            if creds.expiry
            else datetime.now(timezone.utc) + timedelta(hours=1)
        )

        db.commit()

    return build(
        "calendar",
        "v3",
        credentials=creds,
        cache_discovery=False
    )


def obtener_eventos_google(
    usuario,
    db: Session,
    calendarios_ids: list,
    desde: datetime,
    hasta: datetime
):
    """
    Obtiene todos los eventos de los calendarios seleccionados.

    Retorna:
        eventos -> list[dict]
        zona_horaria -> str
    """

    service = obtener_servicio_calendar(usuario, db)

    eventos = []

    zona_horaria = "America/Guayaquil"

    if calendarios_ids:
        try:
            calendario = (
                service.calendars()
                .get(calendarId=calendarios_ids[0])
                .execute()
            )

            zona_horaria = calendario.get(
                "timeZone",
                "America/Guayaquil"
            )

        except Exception:
            pass

    time_min = desde.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    time_max = hasta.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    for calendar_id in calendarios_ids:

        page_token = None

        while True:

            resultado = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    showDeleted=False,
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )

            for item in resultado.get("items", []):

                inicio = (
                    item.get("start", {}).get("dateTime")
                    or item.get("start", {}).get("date")
                )

                fin = (
                    item.get("end", {}).get("dateTime")
                    or item.get("end", {}).get("date")
                )

                if not inicio or not fin:
                    continue

                # Evento de día completo
                if "T" not in inicio:

                    inicio_dt = datetime.fromisoformat(
                        inicio
                    ).replace(tzinfo=timezone.utc)

                else:

                    inicio_dt = datetime.fromisoformat(
                        inicio.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)

                if "T" not in fin:

                    fin_dt = datetime.fromisoformat(
                        fin
                    ).replace(tzinfo=timezone.utc)

                else:

                    fin_dt = datetime.fromisoformat(
                        fin.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)

                eventos.append(
                    {
                        "id": item.get("id"),

                        "title": item.get(
                            "summary",
                            "Sin título"
                        ),

                        "description": item.get(
                            "description",
                            ""
                        ),

                        "calendar_id": calendar_id,

                        "start": inicio_dt,

                        "end": fin_dt,

                        "color": item.get("colorId")
                    }
                )

            page_token = resultado.get("nextPageToken")

            if not page_token:
                break

    print("=" * 60)
    print("Calendarios:", calendarios_ids)
    print("Zona horaria:", zona_horaria)
    print("Eventos encontrados:", len(eventos))

    for evento in eventos:
        print(
            evento["title"],
            evento["start"],
            evento["end"]
        )

    print("=" * 60)

    return eventos, zona_horaria