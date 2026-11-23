import os
import shutil
import sqlite3
import tempfile
import unittest

from registro_db import RegistroPostura


class BaseConDb(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.ruta = os.path.join(self.carpeta, "prueba.db")
        self.db = RegistroPostura(self.ruta)

    def tearDown(self):
        self.db.cerrar()
        shutil.rmtree(self.carpeta, ignore_errors=True)


class PruebasCrudSesiones(BaseConDb):
    def test_crear_y_obtener_sesion(self):
        id_sesion = self.db.crear_sesion("ana", "control", "luz baja")
        sesion = self.db.obtener_sesion(id_sesion)
        self.assertEqual(sesion["participante"], "ana")
        self.assertEqual(sesion["modo"], "CONTROL")
        self.assertEqual(sesion["notas"], "luz baja")
        self.assertIsNone(sesion["fin"])

    def test_obtener_sesion_inexistente(self):
        self.assertIsNone(self.db.obtener_sesion(99))

    def test_modo_invalido(self):
        with self.assertRaises(ValueError):
            self.db.crear_sesion("ana", "otro")

    def test_participante_vacio(self):
        with self.assertRaises(ValueError):
            self.db.crear_sesion("   ", "control")

    def test_listar_por_participante(self):
        self.db.crear_sesion("ana", "control")
        self.db.crear_sesion("beto", "intervencion")
        self.db.crear_sesion("ana", "intervencion")
        self.assertEqual(len(self.db.listar_sesiones()), 3)
        self.assertEqual(len(self.db.listar_sesiones("ana")), 2)

    def test_actualizar_sesion(self):
        id_sesion = self.db.crear_sesion("ana", "control")
        ok = self.db.actualizar_sesion(id_sesion, modo="intervencion",
                                       notas="repetida")
        self.assertTrue(ok)
        sesion = self.db.obtener_sesion(id_sesion)
        self.assertEqual(sesion["modo"], "INTERVENCION")
        self.assertEqual(sesion["notas"], "repetida")

    def test_actualizar_sesion_inexistente(self):
        self.assertFalse(self.db.actualizar_sesion(99, notas="x"))

    def test_actualizar_campo_no_editable(self):
        id_sesion = self.db.crear_sesion("ana", "control")
        with self.assertRaises(ValueError):
            self.db.actualizar_sesion(id_sesion, inicio="2020-01-01")
        with self.assertRaises(ValueError):
            self.db.actualizar_sesion(id_sesion)

    def test_finalizar_sesion(self):
        id_sesion = self.db.crear_sesion("ana", "control")
        self.db.finalizar_sesion(id_sesion, 24.5, 1200)
        sesion = self.db.obtener_sesion(id_sesion)
        self.assertIsNotNone(sesion["fin"])
        self.assertEqual(sesion["fps_promedio"], 24.5)
        self.assertEqual(sesion["cuadros"], 1200)

    def test_eliminar_sesion_borra_sus_eventos(self):
        id_a = self.db.crear_sesion("ana", "control")
        id_b = self.db.crear_sesion("ana", "intervencion")
        self.db.registrar("INICIO_MALA_POSTURA", id_a)
        self.db.registrar("FIN_MALA_POSTURA", id_a)
        self.db.registrar("INICIO_MALA_POSTURA", id_b)
        self.assertTrue(self.db.eliminar_sesion(id_a))
        self.assertIsNone(self.db.obtener_sesion(id_a))
        self.assertEqual(self.db.listar_eventos(id_a), [])
        self.assertEqual(len(self.db.listar_eventos()), 1)
        self.assertFalse(self.db.eliminar_sesion(id_a))


class PruebasEventos(BaseConDb):
    def test_registrar_sin_sesion(self):
        self.db.registrar("INICIO_MALA_POSTURA")
        eventos = self.db.listar_eventos()
        self.assertEqual(len(eventos), 1)
        self.assertIsNone(eventos[0]["id_sesion"])

    def test_evento_con_sesion_inexistente(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.registrar("INICIO_MALA_POSTURA", id_sesion=999)

    def test_timestamp_iso(self):
        self.db.registrar("FIN_MALA_POSTURA")
        self.assertIn("T", self.db.listar_eventos()[0]["fecha_hora"])


class PruebasMigracion(unittest.TestCase):
    def test_migracion_de_base_antigua(self):
        carpeta = tempfile.mkdtemp()
        try:
            ruta = os.path.join(carpeta, "vieja.db")
            conn = sqlite3.connect(ruta)
            conn.execute("""CREATE TABLE logs_postura (
                id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
                estado TEXT NOT NULL, fecha_hora TEXT NOT NULL)""")
            conn.execute("INSERT INTO logs_postura (estado, fecha_hora) "
                         "VALUES ('INICIO_MALA_POSTURA', "
                         "'2026-11-01T10:00:00')")
            conn.commit()
            conn.close()

            db = RegistroPostura(ruta)
            eventos = db.listar_eventos()
            self.assertEqual(len(eventos), 1)
            self.assertIsNone(eventos[0]["id_sesion"])
            id_sesion = db.crear_sesion("ana", "control")
            db.registrar("FIN_MALA_POSTURA", id_sesion)
            self.assertEqual(len(db.listar_eventos(id_sesion)), 1)
            db.cerrar()
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
