"""Calculo de metricas a partir de los eventos registrados (sin cámara).

Definiciones (ver MANUAL.md):
  - episodio: intervalo entre INICIO_MALA_POSTURA y FIN_MALA_POSTURA.
  - pct_mala_postura: segundos en mala postura / segundos monitoreados.
"""

from datetime import datetime

EVENTO_INICIO = "INICIO_MALA_POSTURA"
EVENTO_FIN = "FIN_MALA_POSTURA"
META_REDUCCION = 20.0  # hipotesis: reduccion de al menos 20 %


def _tiempo(texto):
    return datetime.fromisoformat(texto)


def duraciones_episodios(eventos, fin_sesion=None):
    """Devuelve la duracion (s) de cada episodio.

    eventos: lista ordenada de (estado, fecha_hora ISO). Si un episodio
    quedo abierto y se conoce el fin de la sesion, se cierra ahi.
    """
    duraciones = []
    inicio = None
    for estado, fecha in eventos:
        momento = _tiempo(fecha)
        if estado == EVENTO_INICIO:
            inicio = momento
        elif estado == EVENTO_FIN and inicio is not None:
            duraciones.append((momento - inicio).total_seconds())
            inicio = None
    if inicio is not None and fin_sesion:
        resto = (_tiempo(fin_sesion) - inicio).total_seconds()
        duraciones.append(max(0.0, resto))
    return duraciones


def metricas_sesion(sesion, eventos):
    """Metricas de una sesion (dict con inicio/fin) y sus eventos."""
    fin = sesion.get("fin")
    duraciones = duraciones_episodios(eventos, fin)
    monitoreado = 0.0
    if fin:
        monitoreado = (_tiempo(fin) - _tiempo(sesion["inicio"])
                       ).total_seconds()
    mala = sum(duraciones)
    return {
        "episodios": len(duraciones),
        "segundos_mala_postura": mala,
        "segundos_monitoreados": monitoreado,
        "pct_mala_postura": 100 * mala / monitoreado if monitoreado > 0
        else 0.0,
        "duracion_media_episodio": mala / len(duraciones) if duraciones
        else 0.0,
    }


def agregar(lista):
    """Combina varias sesiones ponderando por tiempo monitoreado."""
    mala = sum(m["segundos_mala_postura"] for m in lista)
    monitoreado = sum(m["segundos_monitoreados"] for m in lista)
    episodios = sum(m["episodios"] for m in lista)
    return {
        "sesiones": len(lista),
        "episodios": episodios,
        "segundos_mala_postura": mala,
        "segundos_monitoreados": monitoreado,
        "pct_mala_postura": 100 * mala / monitoreado if monitoreado > 0
        else 0.0,
        "episodios_por_hora": episodios * 3600 / monitoreado
        if monitoreado > 0 else 0.0,
        "duracion_media_episodio": mala / episodios if episodios else 0.0,
    }


def reduccion_pct(base, nuevo):
    """Reduccion porcentual de `nuevo` respecto a `base` (None si base=0)."""
    if base <= 0:
        return None
    return 100 * (base - nuevo) / base


def comparar(control, intervencion, meta=META_REDUCCION):
    """Compara los agregados de las fases CONTROL e INTERVENCION."""
    r_tiempo = reduccion_pct(control["pct_mala_postura"],
                             intervencion["pct_mala_postura"])
    r_frecuencia = reduccion_pct(control["episodios_por_hora"],
                                 intervencion["episodios_por_hora"])
    return {
        "reduccion_tiempo_pct": r_tiempo,
        "reduccion_frecuencia_pct": r_frecuencia,
        "cumple_hipotesis": r_tiempo is not None and r_tiempo >= meta,
    }
