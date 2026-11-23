"""Medida postural a partir de los landmarks de MediaPipe Pose.

No importa mediapipe, asi que se puede probar con puntos simulados.
"""

# Indices de BlazePose (MediaPipe Pose, 33 puntos)
OJO_IZQ, OJO_DER = 2, 5
HOMBRO_IZQ, HOMBRO_DER = 11, 12
MIN_VISIBILIDAD = 0.5


def medir(landmarks, min_visibilidad=MIN_VISIBILIDAD):
    """Distancia vertical ojos-hombros dividida entre el ancho de hombros.

    Al ser una proporcion, no cambia si el usuario se acerca o se aleja
    de la camara. Devuelve None si algun punto necesario no es confiable.
    """
    try:
        ojo_i, ojo_d, hombro_i, hombro_d = (
            landmarks[i]
            for i in (OJO_IZQ, OJO_DER, HOMBRO_IZQ, HOMBRO_DER)
        )
    except (IndexError, KeyError):
        return None
    puntos = (ojo_i, ojo_d, hombro_i, hombro_d)
    if any(p.visibility < min_visibilidad for p in puntos):
        return None
    ancho_hombros = abs(hombro_i.x - hombro_d.x)
    if ancho_hombros < 1e-6:
        return None
    y_ojos = (ojo_i.y + ojo_d.y) / 2
    y_hombros = (hombro_i.y + hombro_d.y) / 2
    return (y_hombros - y_ojos) / ancho_hombros
