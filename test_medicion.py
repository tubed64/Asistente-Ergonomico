import unittest

from medicion import (
    HOMBRO_DER,
    HOMBRO_IZQ,
    OJO_DER,
    OJO_IZQ,
    medir,
)


class Punto:
    def __init__(self, x=0.5, y=0.5, visibility=1.0):
        self.x = x
        self.y = y
        self.visibility = visibility


def landmarks(ojo_y, hombro_y, x_izq, x_der, visibilidad=1.0):
    puntos = [Punto(visibility=visibilidad) for _ in range(33)]
    puntos[OJO_IZQ] = Punto(0.45, ojo_y, visibilidad)
    puntos[OJO_DER] = Punto(0.55, ojo_y, visibilidad)
    puntos[HOMBRO_IZQ] = Punto(x_izq, hombro_y, visibilidad)
    puntos[HOMBRO_DER] = Punto(x_der, hombro_y, visibilidad)
    return puntos


class PruebasMedicion(unittest.TestCase):
    def test_proporcion_ojos_hombros(self):
        # distancia vertical 0.3, ancho de hombros 0.2 -> 1.5
        puntos = landmarks(0.4, 0.7, 0.4, 0.6)
        self.assertAlmostEqual(medir(puntos), 1.5)

    def test_invariante_a_la_distancia_de_la_camara(self):
        cerca = landmarks(0.4, 0.7, 0.4, 0.6)
        # misma postura, el doble de tamano aparente
        mas_cerca = landmarks(0.3, 0.9, 0.3, 0.7)
        self.assertAlmostEqual(medir(cerca), medir(mas_cerca))

    def test_encorvarse_reduce_la_medida(self):
        derecho = medir(landmarks(0.40, 0.70, 0.4, 0.6))
        encorvado = medir(landmarks(0.50, 0.70, 0.4, 0.6))
        self.assertLess(encorvado, derecho)

    def test_visibilidad_baja(self):
        puntos = landmarks(0.4, 0.7, 0.4, 0.6, visibilidad=0.3)
        self.assertIsNone(medir(puntos))

    def test_hombros_sin_ancho(self):
        puntos = landmarks(0.4, 0.7, 0.5, 0.5)
        self.assertIsNone(medir(puntos))

    def test_lista_incompleta(self):
        self.assertIsNone(medir([Punto(), Punto()]))


if __name__ == "__main__":
    unittest.main()
