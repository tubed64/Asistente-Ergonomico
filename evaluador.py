"""Lógica de decisión postural (sin cámara ni base de datos).

Se mantiene separada del resto para poder probarla con valores simulados.
"""

import time

ESTADO_CALIBRANDO = "CALIBRANDO"
ESTADO_SIN_DETECCION = "SIN_DETECCION"
ESTADO_OK = "POSTURA_OK"
ESTADO_VIGILANDO = "VIGILANDO"
ESTADO_MALA = "MALA_POSTURA"

EVENTO_INICIO = "INICIO_MALA_POSTURA"
EVENTO_FIN = "FIN_MALA_POSTURA"


class EvaluadorPostura:
    """Compara la medida actual contra la calibrada y detecta episodios.

    La medida es una proporción (distancia vertical ojos-hombros dividida
    entre el ancho de hombros), por lo que no cambia si el usuario se acerca
    o se aleja de la cámara.
    """

    def __init__(self, tolerancia=0.20, holgura_seg=5.0, reloj=time.monotonic):
        self.tolerancia = tolerancia
        self.holgura_seg = holgura_seg
        self._reloj = reloj
        self.referencia = None
        self._inicio_desviacion = None
        self._en_episodio = False

    @property
    def calibrado(self):
        return self.referencia is not None

    def calibrar(self, medida):
        """Fija la postura ideal y reinicia el temporizador."""
        self.referencia = medida
        self._inicio_desviacion = None
        self._en_episodio = False

    def actualizar(self, medida):
        """Procesa una medida (o None si no hay detección).

        Devuelve (estado, evento). El evento es EVENTO_INICIO, EVENTO_FIN
        o None, y es el que debe registrarse en la base de datos.
        """
        if medida is None:
            self._inicio_desviacion = None
            return ESTADO_SIN_DETECCION, self._cerrar_episodio()

        if self.referencia is None:
            return ESTADO_CALIBRANDO, None

        limite = self.referencia * (1 - self.tolerancia)
        if medida < limite:
            ahora = self._reloj()
            if self._inicio_desviacion is None:
                self._inicio_desviacion = ahora
            if ahora - self._inicio_desviacion > self.holgura_seg:
                evento = None
                if not self._en_episodio:
                    self._en_episodio = True
                    evento = EVENTO_INICIO
                return ESTADO_MALA, evento
            return ESTADO_VIGILANDO, None

        self._inicio_desviacion = None
        return ESTADO_OK, self._cerrar_episodio()

    def cerrar(self):
        """Cierra un episodio abierto (útil al salir del programa)."""
        return self._cerrar_episodio()

    def _cerrar_episodio(self):
        if self._en_episodio:
            self._en_episodio = False
            return EVENTO_FIN
        return None
