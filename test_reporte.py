import contextlib
import csv
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

import gestor_datos
import reporte
from registro_db import RegistroPostura


class BaseConDb(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.ruta = os.path.join(self.carpeta, "prueba.db")
        self.db = RegistroPostura(self.ruta)

    def tearDown(self):
        self.db.cerrar()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def sesion_con_tiempos(self, modo, segundos_mala, participante="ana"):
        """Sesion de 1 hora con un episodio de `segundos_mala`."""
        id_sesion = self.db.crear_sesion(participante, modo)
        self.db.conn.execute(
            "UPDATE sesiones SET inicio = ?, fin = ? WHERE id_sesion = ?",
            ("2026-11-22T10:00:00", "2026-11-22T11:00:00", id_sesion))
        fin_ep = f"2026-11-22T10:{segundos_mala // 60:02d}:" \
                 f"{segundos_mala % 60:02d}"
        for estado, fecha in (("INICIO_MALA_POSTURA",
                               "2026-11-22T10:00:00"),
                              ("FIN_MALA_POSTURA", fin_ep)):
            self.db.conn.execute(
                "INSERT INTO logs_postura (estado, fecha_hora, id_sesion) "
                "VALUES (?, ?, ?)", (estado, fecha, id_sesion))
        self.db.conn.commit()
        return id_sesion


class PruebasReporte(BaseConDb):
    def test_recolectar_y_resumen(self):
        self.sesion_con_tiempos("CONTROL", 600)
        self.sesion_con_tiempos("INTERVENCION", 300)
        filas = reporte.recolectar(self.db)
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["segundos_mala_postura"], 600.0)
        resumen = reporte.resumen_por_modo(filas)
        self.assertAlmostEqual(resumen["CONTROL"]["pct_mala_postura"],
                               600 / 36)
        self.assertAlmostEqual(
            resumen["INTERVENCION"]["pct_mala_postura"], 300 / 36)

    def test_resumen_excluye_sesiones_sin_cerrar(self):
        self.db.crear_sesion("ana", "control")
        filas = reporte.recolectar(self.db)
        self.assertIsNone(reporte.resumen_por_modo(filas)["CONTROL"])

    def test_exportar_csv(self):
        self.sesion_con_tiempos("CONTROL", 600)
        self.sesion_con_tiempos("INTERVENCION", 300)
        ruta_csv = os.path.join(self.carpeta, "salida.csv")
        reporte.exportar_csv(reporte.recolectar(self.db), ruta_csv)
        with open(ruta_csv, newline="", encoding="utf-8-sig") as f:
            filas = list(csv.DictReader(f))
        self.assertEqual(len(filas), 2)
        self.assertEqual(list(filas[0].keys()), reporte.COLUMNAS_CSV)
        self.assertEqual(filas[1]["modo"], "INTERVENCION")

    def test_main_imprime_comparacion(self):
        self.sesion_con_tiempos("CONTROL", 600)
        self.sesion_con_tiempos("INTERVENCION", 300)
        self.db.cerrar()
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = reporte.main(["--db", self.ruta])
        self.assertEqual(codigo, 0)
        self.assertIn("Cumple la meta de al menos 20 %: SI",
                      salida.getvalue())
        self.db = RegistroPostura(self.ruta)


class PruebasGestor(BaseConDb):
    def ejecutar(self, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = gestor_datos.main([*argumentos, "--db", self.ruta])
        return codigo, salida.getvalue()

    def test_ciclo_crud_completo(self):
        codigo, texto = self.ejecutar("crear", "--participante", "ana",
                                      "--modo", "control")
        self.assertEqual(codigo, 0)
        self.assertIn("id 1", texto)

        _, texto = self.ejecutar("listar")
        self.assertIn("ana", texto)

        codigo, _ = self.ejecutar("editar", "1", "--notas", "luz baja")
        self.assertEqual(codigo, 0)
        _, texto = self.ejecutar("ver", "1")
        self.assertIn("luz baja", texto)

        codigo, _ = self.ejecutar("eliminar", "1", "--si")
        self.assertEqual(codigo, 0)
        _, texto = self.ejecutar("listar")
        self.assertIn("No hay sesiones", texto)

    def test_sesion_inexistente(self):
        codigo, texto = self.ejecutar("ver", "99")
        self.assertEqual(codigo, 1)
        self.assertIn("No existe", texto)

    def test_editar_sin_campos(self):
        self.db.crear_sesion("ana", "control")
        codigo, _ = self.ejecutar("editar", "1")
        self.assertEqual(codigo, 1)

    def test_eliminar_cancelado(self):
        self.db.crear_sesion("ana", "control")
        with mock.patch("builtins.input", return_value="n"):
            codigo, texto = self.ejecutar("eliminar", "1")
        self.assertEqual(codigo, 0)
        self.assertIn("Cancelado", texto)
        self.assertIsNotNone(self.db.obtener_sesion(1))


if __name__ == "__main__":
    unittest.main()
