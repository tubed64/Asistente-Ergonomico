"""Vista: dibuja el HUD sobre el video.

OpenCV no renderiza acentos, por eso los textos van sin ellos.
"""

import cv2
import numpy as np

from evaluador import (
    ESTADO_CALIBRANDO,
    ESTADO_MALA,
    ESTADO_OK,
    ESTADO_SIN_DETECCION,
    ESTADO_VIGILANDO,
)

# Colores en BGR
VERDE = (0, 200, 80)
NARANJA = (0, 150, 255)
AMARILLO = (0, 200, 255)
ROJO = (0, 0, 255)
GRIS = (200, 200, 200)
BLANCO = (255, 255, 255)

FUENTE = cv2.FONT_HERSHEY_SIMPLEX

TEXTOS = {
    ESTADO_CALIBRANDO: ("Calibrando: sientate derecho y presiona 'c'",
                        NARANJA),
    ESTADO_SIN_DETECCION: ("Seguimiento no disponible", GRIS),
    ESTADO_OK: ("Postura optima", VERDE),
    ESTADO_VIGILANDO: ("Desviacion detectada...", AMARILLO),
    ESTADO_MALA: ("Peligro inminente", ROJO),
}


def _texto(img, texto, color, pos, escala=0.65, grosor=2):
    cv2.putText(img, texto, pos, FUENTE, escala, color, grosor,
                cv2.LINE_AA)


def _banner(img, texto):
    """Alerta grande: franja roja translucida con texto centrado."""
    alto, ancho = img.shape[:2]
    capa = img.copy()
    cv2.rectangle(capa, (0, alto // 2 - 45), (ancho, alto // 2 + 45),
                  ROJO, -1)
    cv2.addWeighted(capa, 0.6, img, 0.4, 0, img)
    (w, _), _ = cv2.getTextSize(texto, FUENTE, 1.0, 3)
    escala = min(1.4, (ancho - 30) / w)
    (w, h), _ = cv2.getTextSize(texto, FUENTE, escala, 3)
    _texto(img, texto, BLANCO, ((ancho - w) // 2, alto // 2 + h // 2),
           escala, 3)


def dibujar_hud(img, estado, modo, fps, mensaje=None):
    """Superpone estado, alertas, FPS y mensajes temporales.

    En modo CONTROL no se muestran alertas ni estado postural: el
    participante no recibe retroalimentacion (fase de control).
    """
    alto = img.shape[0]
    if modo == "CONTROL":
        if estado == ESTADO_CALIBRANDO:
            texto, color = TEXTOS[ESTADO_CALIBRANDO]
        else:
            texto, color = "Modo control: monitoreo sin alertas", GRIS
        _texto(img, texto, color, (15, 35))
    else:
        texto, color = TEXTOS[estado]
        _texto(img, texto, color, (15, 35))
        if estado == ESTADO_MALA:
            _banner(img, "CORRIGE TU POSTURA")
    _texto(img, f"FPS: {fps:.0f}", GRIS, (15, alto - 15), 0.5, 1)
    if mensaje:
        _texto(img, mensaje[0], mensaje[1], (15, alto - 45), 0.55, 1)


def pantalla_sin_camara(ancho, alto):
    """Imagen mostrada mientras se intenta recuperar la camara."""
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    _texto(img, "Camara no disponible. Reintentando...", ROJO,
           (15, alto // 2 - 10))
    _texto(img, "Presiona 'q' para salir", GRIS, (15, alto // 2 + 25),
           0.55, 1)
    return img
