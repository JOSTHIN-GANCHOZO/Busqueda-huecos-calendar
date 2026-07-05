from datetime import datetime, timedelta, timezone
import pytz

def calcular_hueco_greedy(
    eventos_ocupados: list,
    inicio_rango: datetime,
    fin_rango: datetime,
    duracion_minutos: int,
    zona_usuario: str,
    max_resultados: int = 5
):
    HORA_APERTURA = 8
    HORA_CIERRE = 18
    DIAS_ENTRE_SEMANA = (0, 1, 2, 3, 4)
    
    tz = pytz.timezone(zona_usuario)
    
    if inicio_rango.tzinfo is None:
        inicio_rango = inicio_rango.replace(tzinfo=timezone.utc)
    if fin_rango.tzinfo is None:
        fin_rango = fin_rango.replace(tzinfo=timezone.utc)

    duracion_cita = timedelta(minutes=duracion_minutos)
    agenda = sorted(eventos_ocupados, key=lambda e: e['start'])
    huecos_encontrados = []

    dia = inicio_rango.date()
    while dia <= fin_rango.date() and len(huecos_encontrados) < max_resultados:
        if dia.weekday() not in DIAS_ENTRE_SEMANA:
            dia += timedelta(days=1)
            continue
        
        apertura = datetime.combine(dia, datetime.strptime(f"{HORA_APERTURA}:00", "%H:%M").time())
        cierre = datetime.combine(dia, datetime.strptime(f"{HORA_CIERRE}:00", "%H:%M").time())
        apertura_utc = tz.localize(apertura).astimezone(pytz.utc)
        cierre_utc = tz.localize(cierre).astimezone(pytz.utc)
        
        apertura_utc = max(apertura_utc, inicio_rango)
        cierre_utc = min(cierre_utc, fin_rango)
        
        if apertura_utc >= cierre_utc:
            dia += timedelta(days=1)
            continue

        puntero = apertura_utc
        for cita in agenda:
            inicio_cita = cita['start'] if cita['start'].tzinfo else cita['start'].replace(tzinfo=timezone.utc)
            fin_cita = cita['end'] if cita['end'].tzinfo else cita['end'].replace(tzinfo=timezone.utc)
            
            if fin_cita <= puntero:
                continue
            if inicio_cita >= cierre_utc:
                break

            while inicio_cita - puntero >= duracion_cita and len(huecos_encontrados) < max_resultados:
                huecos_encontrados.append({
                    "fecha": puntero.astimezone(tz).strftime("%Y-%m-%d"),
                    "inicio": puntero.astimezone(tz).strftime("%H:%M"),
                    "fin": (puntero + duracion_cita).astimezone(tz).strftime("%H:%M")
                })
                puntero += duracion_cita
            
            puntero = max(puntero, fin_cita)

        while cierre_utc - puntero >= duracion_cita and len(huecos_encontrados) < max_resultados:
            huecos_encontrados.append({
                "fecha": puntero.astimezone(tz).strftime("%Y-%m-%d"),
                "inicio": puntero.astimezone(tz).strftime("%H:%M"),
                "fin": (puntero + duracion_cita).astimezone(tz).strftime("%H:%M")
            })
            puntero += duracion_cita

        dia += timedelta(days=1)

    return huecos_encontrados if huecos_encontrados else None