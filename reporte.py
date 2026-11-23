"""Reporte de metricas: sesiones, resumen por modo y comparacion A/B.

Ejemplos:
  python reporte.py
  python reporte.py --participante ana --csv metricas.csv
"""

import argparse
import csv

from metricas import agregar, comparar, metricas_sesion
from registro_db import MODOS, RegistroPostura

COLUMNAS_CSV = [
    "id_sesion", "participante", "modo", "inicio", "fin",
    "segundos_monitoreados", "episodios", "segundos_mala_postura",
    "pct_mala_postura", "duracion_media_episodio", "fps_promedio",
    "cuadros", "notas",
]


def recolectar(db, participante=None):
    """Devuelve una fila (dict) con datos y metricas por cada sesion."""
    filas = []
    for sesion in db.listar_sesiones(participante):
        eventos = [(e["estado"], e["fecha_hora"])
                   for e in db.listar_eventos(sesion["id_sesion"])]
        filas.append({**sesion, **metricas_sesion(sesion, eventos)})
    return filas


def resumen_por_modo(filas):
    """Agrega las sesiones cerradas de cada modo (None si no hay)."""
    resumen = {}
    for modo in MODOS:
        cerradas = [f for f in filas if f["modo"] == modo and f["fin"]]
        resumen[modo] = agregar(cerradas) if cerradas else None
    return resumen


def exportar_csv(filas, ruta):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_CSV,
                                  extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)


def _formato(valor, decimales=1):
    return "-" if valor is None else f"{valor:.{decimales}f}"


def imprimir(filas, resumen):
    print("ID  Participante  Modo          Min  Epis.  %Mala   FPS")
    for f in filas:
        minutos = f["segundos_monitoreados"] / 60
        print(f"{f['id_sesion']:>2}  {f['participante'][:12]:<12}  "
              f"{f['modo']:<12} {minutos:>5.1f} {f['episodios']:>5} "
              f"{f['pct_mala_postura']:>6.1f}  "
              f"{_formato(f['fps_promedio'])}")
    abiertas = [f["id_sesion"] for f in filas if not f["fin"]]
    if abiertas:
        print(f"\nSesiones sin cerrar (excluidas del resumen): {abiertas}")

    print("\nResumen por modo")
    for modo in MODOS:
        r = resumen[modo]
        if r is None:
            print(f"  {modo:<12} sin sesiones cerradas")
            continue
        print(f"  {modo:<12} sesiones: {r['sesiones']} | "
              f"{r['segundos_monitoreados'] / 60:.1f} min | "
              f"mala postura: {r['pct_mala_postura']:.1f} % | "
              f"{r['episodios_por_hora']:.1f} episodios/h | "
              f"duracion media: {r['duracion_media_episodio']:.0f} s")

    if resumen["CONTROL"] and resumen["INTERVENCION"]:
        c = comparar(resumen["CONTROL"], resumen["INTERVENCION"])
        print("\nComparacion (INTERVENCION frente a CONTROL)")
        print(f"  Reduccion del tiempo en mala postura: "
              f"{_formato(c['reduccion_tiempo_pct'])} %")
        print(f"  Reduccion de la frecuencia de episodios: "
              f"{_formato(c['reduccion_frecuencia_pct'])} %")
        veredicto = "SI" if c["cumple_hipotesis"] else "NO"
        print(f"  Cumple la meta de al menos 20 %: {veredicto}")
    else:
        print("\nPara comparar hacen falta sesiones cerradas de CONTROL "
              "y de INTERVENCION.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reporte de metricas")
    parser.add_argument("--db", default="registro_postura.db")
    parser.add_argument("--participante")
    parser.add_argument("--csv", help="Exportar metricas por sesion a CSV")
    args = parser.parse_args(argv)

    db = RegistroPostura(args.db)
    try:
        filas = recolectar(db, args.participante)
    finally:
        db.cerrar()

    if not filas:
        print("No hay sesiones registradas.")
        return 0
    imprimir(filas, resumen_por_modo(filas))
    if args.csv:
        exportar_csv(filas, args.csv)
        print(f"\nCSV exportado en {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
