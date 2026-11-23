import os
import tempfile
import unittest

from evaluador import (
    EvaluadorPostura,
    ESTADO_CALIBRANDO,
    ESTADO_MALA,
    ESTADO_OK,
    ESTADO_SIN_DETECCION,
    ESTADO_VIGILANDO,
    EVENTO_FIN,
    EVENTO_INICIO,
)
from registro_db import RegistroPostura


class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class PruebasEvaluador(unittest.TestCase):
    def setUp(self):
        self.reloj = RelojFalso()
        self.ev = EvaluadorPostura(0.20, 5, reloj=self.reloj)

    def test_sin_calibrar(self):
        self.assertEqual(self.ev.actualizar(1.0), (ESTADO_CALIBRANDO, None))

    def test_postura_ok(self):
        self.ev.calibrar(1.0)
        self.assertEqual(self.ev.actualizar(0.9), (ESTADO_OK, None))

    def test_alerta_solo_tras_holgura(self):
        self.ev.calibrar(1.0)
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_VIGILANDO, None))
        self.reloj.t = 4.9
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_VIGILANDO, None))
        self.reloj.t = 5.1
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_MALA, EVENTO_INICIO))
        self.reloj.t = 6.0
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_MALA, None))

    def test_correccion_antes_de_holgura_reinicia(self):
        self.ev.calibrar(1.0)
        self.ev.actualizar(0.5)
        self.reloj.t = 3.0
        self.assertEqual(self.ev.actualizar(1.0), (ESTADO_OK, None))
        self.reloj.t = 6.0
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_VIGILANDO, None))

    def test_fin_de_episodio(self):
        self.ev.calibrar(1.0)
        self.ev.actualizar(0.5)
        self.reloj.t = 6.0
        self.ev.actualizar(0.5)
        self.assertEqual(self.ev.actualizar(1.0), (ESTADO_OK, EVENTO_FIN))

    def test_perder_deteccion_cierra_episodio_y_reinicia_timer(self):
        self.ev.calibrar(1.0)
        self.ev.actualizar(0.5)
        self.reloj.t = 6.0
        self.ev.actualizar(0.5)
        self.assertEqual(self.ev.actualizar(None),
                         (ESTADO_SIN_DETECCION, EVENTO_FIN))
        self.reloj.t = 7.0
        self.assertEqual(self.ev.actualizar(0.5), (ESTADO_VIGILANDO, None))

    def test_cerrar_al_salir(self):
        self.ev.calibrar(1.0)
        self.ev.actualizar(0.5)
        self.reloj.t = 6.0
        self.ev.actualizar(0.5)
        self.assertEqual(self.ev.cerrar(), EVENTO_FIN)
        self.assertIsNone(self.ev.cerrar())


class PruebasBaseDeDatos(unittest.TestCase):
    def test_registro(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "prueba.db")
            db = RegistroPostura(ruta)
            db.registrar(EVENTO_INICIO)
            db.registrar(EVENTO_FIN)
            filas = db.conn.execute(
                "SELECT id_evento, estado, fecha_hora FROM logs_postura"
            ).fetchall()
            db.cerrar()
        self.assertEqual([f[1] for f in filas], [EVENTO_INICIO, EVENTO_FIN])
        self.assertEqual([f[0] for f in filas], [1, 2])
        self.assertIn("T", filas[0][2])


if __name__ == "__main__":
    unittest.main()
