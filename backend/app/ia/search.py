from datetime import datetime, timedelta, timezone
import pytz

# =====================================================
# ALGORITMO GREEDY PARA BÚSQUEDA DE HUECOS LIBRES
# =====================================================
def calcular_hueco_greedy(
    eventos_ocupados:list,
    inicio_rango:datetime,
    fin_rango:datetime,
    duracion_minutos:int,
    zona_usuario:str,
    max_resultados:int=5
):
    HORA_APERTURA=8
    HORA_CIERRE=18
    DIAS_ENTRE_SEMANA=(0,1,2,3,4)

    tz=pytz.timezone(zona_usuario)

    if inicio_rango.tzinfo is None:
        inicio_rango=inicio_rango.replace(tzinfo=timezone.utc)

    if fin_rango.tzinfo is None:
        fin_rango=fin_rango.replace(tzinfo=timezone.utc)

    duracion_cita=timedelta(minutes=duracion_minutos)
    agenda=sorted(eventos_ocupados,key=lambda e:e["start"])
    huecos_encontrados=[]

    dia=inicio_rango.date()

    # =====================================================
    # RECORRER CADA DÍA DEL RANGO
    # =====================================================
    while dia<=fin_rango.date() and len(huecos_encontrados)<max_resultados:

        if dia.weekday() not in DIAS_ENTRE_SEMANA:
            dia+=timedelta(days=1)
            continue

        apertura=datetime.combine(
            dia,
            datetime.strptime(f"{HORA_APERTURA}:00","%H:%M").time()
        )

        cierre=datetime.combine(
            dia,
            datetime.strptime(f"{HORA_CIERRE}:00","%H:%M").time()
        )

        apertura_utc=tz.localize(apertura).astimezone(pytz.utc)
        cierre_utc=tz.localize(cierre).astimezone(pytz.utc)

        apertura_utc=max(apertura_utc,inicio_rango)
        cierre_utc=min(cierre_utc,fin_rango)

        if apertura_utc>=cierre_utc:
            dia+=timedelta(days=1)
            continue

        puntero=apertura_utc

        # =====================================================
        # RECORRER LOS EVENTOS DEL DÍA
        # =====================================================
        for cita in agenda:

            inicio_cita=cita["start"]
            fin_cita=cita["end"]

            if inicio_cita.tzinfo is None:
                inicio_cita=inicio_cita.replace(tzinfo=timezone.utc)

            if fin_cita.tzinfo is None:
                fin_cita=fin_cita.replace(tzinfo=timezone.utc)

            if fin_cita<=puntero:
                continue

            if inicio_cita>=cierre_utc:
                break

            # =====================================================
            # GENERAR HUECOS ANTES DEL EVENTO
            # =====================================================
            while inicio_cita-puntero>=duracion_cita and len(huecos_encontrados)<max_resultados:

                inicio_local=puntero.astimezone(tz)
                fin_local=(puntero+duracion_cita).astimezone(tz)

                huecos_encontrados.append({
                    "title":"⭐ Hueco IA",
                    "start":inicio_local.isoformat(),
                    "end":fin_local.isoformat(),
                    "fecha":inicio_local.strftime("%Y-%m-%d"),
                    "hora_inicio":inicio_local.strftime("%H:%M"),
                    "hora_fin":fin_local.strftime("%H:%M"),
                    "duracion":duracion_minutos
                })

                puntero+=duracion_cita

            puntero=max(puntero,fin_cita)

        # =====================================================
        # GENERAR HUECOS DESPUÉS DEL ÚLTIMO EVENTO
        # =====================================================
        while cierre_utc-puntero>=duracion_cita and len(huecos_encontrados)<max_resultados:

            inicio_local=puntero.astimezone(tz)
            fin_local=(puntero+duracion_cita).astimezone(tz)

            huecos_encontrados.append({
                "title":"⭐ Hueco IA",
                "start":inicio_local.isoformat(),
                "end":fin_local.isoformat(),
                "fecha":inicio_local.strftime("%Y-%m-%d"),
                "hora_inicio":inicio_local.strftime("%H:%M"),
                "hora_fin":fin_local.strftime("%H:%M"),
                "duracion":duracion_minutos
            })

            puntero+=duracion_cita

        dia+=timedelta(days=1)

    # =====================================================
    # DEPURACIÓN
    # =====================================================
    print("="*60)
    print(f"Huecos encontrados: {len(huecos_encontrados)}")
    print(huecos_encontrados)
    print("="*60)

    return huecos_encontrados if huecos_encontrados else None