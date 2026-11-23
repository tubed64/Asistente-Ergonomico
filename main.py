"""Controlador del asistente ergonomico de escritorio (MVP).

Coordina camara, modelo de pose, logica de decision, base de datos y HUD.
Teclas: 'c' calibrar postura ideal, 'q' salir.
Todo el procesamiento es local: no se guardan imagenes ni se usa internet.

Ejemplos:
  python main.py --participante ana --modo control
  python main.py --participante ana --modo intervencion
"""

import argparse
import time

import cv2
import mediapipe as mp

import vista
from evaluador import EvaluadorPostura
from medicion import medir
from registro_db import MODOS, RegistroPostura

VENTANA = "Asistente Ergonomico"
ANCHO, ALTO = 640, 480  # resolucion baja: menos carga en equipos modestos
ESPERA_SIN_CAMARA_MS = 100
REINTENTAR_CADA = 20  # intentos fallidos entre reconexiones (~2 s)
MAX_FALLOS = 300  # ~30 s sin camara: se cierra de forma segura
SEGUNDOS_MENSAJE = 2.0


def abrir_camara(indice):
    cap = cv2.VideoCapture(indice)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
    return cap


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Asistente ergonomico con vision artificial")
    parser.add_argument("--participante", default="anonimo")
    parser.add_argument("--modo", default="intervencion",
                        choices=[m.lower() for m in MODOS],
                        help="control: monitorea sin alertas; "
                             "intervencion: muestra alertas")
    parser.add_argument("--db", default="registro_postura.db")
    parser.add_argument("--camara", type=int, default=0)
    parser.add_argument("--tolerancia", type=float, default=0.20)
    parser.add_argument("--holgura", type=float, default=5.0,
                        help="segundos de desviacion antes de alertar")
    parser.add_argument("--notas", default="")
    return parser.parse_args(argv)


def main(argv=None):
    args = leer_argumentos(argv)
    modo = args.modo.upper()

    cap = abrir_camara(args.camara)
    if not cap.isOpened():
        print("No se pudo abrir la camara. Revisa que este conectada y "
              "que ninguna otra aplicacion la use.")
        cap.release()
        return 1

    db = RegistroPostura(args.db)
    id_sesion = db.crear_sesion(args.participante, modo, args.notas)
    evaluador = EvaluadorPostura(args.tolerancia, args.holgura)

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    # model_complexity=0 es el modelo mas ligero de BlazePose
    pose = mp_pose.Pose(model_complexity=0,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)

    print(f"Sesion {id_sesion} | participante: {args.participante} | "
          f"modo: {modo}. 'c' calibra, 'q' sale.")

    cuadros = 0
    tiempo_activo = 0.0
    t_previo = None
    fps = 0.0
    fallos = 0
    mensaje = None  # (texto, color, vence)

    try:
        while True:
            ok, frame = cap.read() if cap.isOpened() else (False, None)
            if not ok:
                # RNF-03: sin camara se pausa la evaluacion y se reintenta
                fallos += 1
                t_previo = None
                _, evento = evaluador.actualizar(None)
                if evento:
                    db.registrar(evento, id_sesion)
                cv2.imshow(VENTANA, vista.pantalla_sin_camara(ANCHO, ALTO))
                tecla = cv2.waitKey(ESPERA_SIN_CAMARA_MS) & 0xFF
                if tecla == ord("q") or fallos > MAX_FALLOS:
                    break
                if fallos % REINTENTAR_CADA == 0:
                    cap.release()
                    cap = abrir_camara(args.camara)
                continue
            fallos = 0

            ahora = time.perf_counter()
            if t_previo is not None:
                dt = max(ahora - t_previo, 1e-6)
                tiempo_activo += dt
                fps = 1.0 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
            t_previo = ahora
            cuadros += 1

            frame = cv2.flip(frame, 1)  # efecto espejo
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            resultado = pose.process(rgb)

            medida = None
            if resultado.pose_landmarks:
                medida = medir(resultado.pose_landmarks.landmark)
                if modo == "INTERVENCION":
                    mp_drawing.draw_landmarks(
                        frame, resultado.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS)

            estado, evento = evaluador.actualizar(medida)
            if evento:
                db.registrar(evento, id_sesion)

            if mensaje and ahora > mensaje[2]:
                mensaje = None
            vista.dibujar_hud(frame, estado, modo, fps,
                              mensaje and mensaje[:2])
            cv2.imshow(VENTANA, frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("c"):
                if medida is not None:
                    evaluador.calibrar(medida)
                    mensaje = ("Calibracion guardada", vista.VERDE,
                               ahora + SEGUNDOS_MENSAJE)
                else:
                    mensaje = ("No te detecto: acomodate e intenta otra vez",
                               vista.NARANJA, ahora + SEGUNDOS_MENSAJE)
            elif tecla == ord("q"):
                break
    finally:
        evento = evaluador.cerrar()
        if evento:
            db.registrar(evento, id_sesion)
        fps_promedio = None
        if tiempo_activo > 0:
            fps_promedio = round((cuadros - 1) / tiempo_activo, 2)
        db.finalizar_sesion(id_sesion, fps_promedio, cuadros)
        pose.close()
        cap.release()
        cv2.destroyAllWindows()
        db.cerrar()
        print(f"Sesion {id_sesion} cerrada: {cuadros} cuadros, "
              f"FPS promedio: {fps_promedio}. Usa reporte.py para ver "
              "las metricas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
