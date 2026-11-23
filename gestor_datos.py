"""Gestion (CRUD) de sesiones de monitoreo desde la linea de comandos.

Ejemplos:
  python gestor_datos.py listar
  python gestor_datos.py crear --participante ana --modo control
  python gestor_datos.py ver 3
  python gestor_datos.py editar 3 --notas "luz baja"
  python gestor_datos.py eliminar 3
"""

import argparse

from metricas import metricas_sesion
from registro_db import MODOS, RegistroPostura


def _linea(sesion):
    fin = sesion["fin"] or "en curso"
    return (f"[{sesion['id_sesion']}] {sesion['participante']} | "
            f"{sesion['modo']} | {sesion['inicio']} -> {fin}")


def construir_parser():
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--db", default="registro_postura.db",
                       help="Archivo de base de datos")
    modos = [m.lower() for m in MODOS]

    parser = argparse.ArgumentParser(description="CRUD de sesiones")
    sub = parser.add_subparsers(dest="comando", required=True)

    crear = sub.add_parser("crear", parents=[comun],
                           help="Crear una sesion manualmente")
    crear.add_argument("--participante", required=True)
    crear.add_argument("--modo", required=True, choices=modos)
    crear.add_argument("--notas", default="")

    listar = sub.add_parser("listar", parents=[comun],
                            help="Listar sesiones")
    listar.add_argument("--participante")

    ver = sub.add_parser("ver", parents=[comun],
                         help="Ver una sesion, sus metricas y eventos")
    ver.add_argument("id", type=int)

    editar = sub.add_parser("editar", parents=[comun],
                            help="Editar participante, modo o notas")
    editar.add_argument("id", type=int)
    editar.add_argument("--participante")
    editar.add_argument("--modo", choices=modos)
    editar.add_argument("--notas")

    eliminar = sub.add_parser("eliminar", parents=[comun],
                              help="Eliminar una sesion y sus eventos")
    eliminar.add_argument("id", type=int)
    eliminar.add_argument("--si", action="store_true",
                          help="No pedir confirmacion")
    return parser


def ejecutar(args, db):
    if args.comando == "crear":
        id_sesion = db.crear_sesion(args.participante, args.modo,
                                    args.notas)
        print(f"Sesion creada con id {id_sesion}.")
        return 0

    if args.comando == "listar":
        sesiones = db.listar_sesiones(args.participante)
        if not sesiones:
            print("No hay sesiones registradas.")
        for sesion in sesiones:
            print(_linea(sesion))
        return 0

    sesion = db.obtener_sesion(args.id)
    if sesion is None:
        print(f"No existe la sesion {args.id}.")
        return 1

    if args.comando == "ver":
        eventos = db.listar_eventos(args.id)
        metricas = metricas_sesion(
            sesion, [(e["estado"], e["fecha_hora"]) for e in eventos])
        print(_linea(sesion))
        print(f"Notas: {sesion['notas'] or '-'}")
        print(f"FPS promedio: {sesion['fps_promedio']} | "
              f"cuadros: {sesion['cuadros']}")
        print(f"Episodios: {metricas['episodios']} | mala postura: "
              f"{metricas['pct_mala_postura']:.1f} %")
        for evento in eventos:
            print(f"  {evento['fecha_hora']}  {evento['estado']}")
        return 0

    if args.comando == "editar":
        campos = {c: getattr(args, c)
                  for c in ("participante", "modo", "notas")
                  if getattr(args, c) is not None}
        if not campos:
            print("Indica al menos --participante, --modo o --notas.")
            return 1
        db.actualizar_sesion(args.id, **campos)
        print(f"Sesion {args.id} actualizada.")
        return 0

    if args.comando == "eliminar":
        if not args.si:
            n = len(db.listar_eventos(args.id))
            respuesta = input(f"Eliminar la sesion {args.id} y sus {n} "
                              "eventos? (s/N): ")
            if respuesta.strip().lower() != "s":
                print("Cancelado.")
                return 0
        db.eliminar_sesion(args.id)
        print(f"Sesion {args.id} eliminada.")
        return 0
    return 1


def main(argv=None):
    args = construir_parser().parse_args(argv)
    db = RegistroPostura(args.db)
    try:
        return ejecutar(args, db)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    finally:
        db.cerrar()


if __name__ == "__main__":
    raise SystemExit(main())
