import unittest

from metricas import (
    agregar,
    comparar,
    duraciones_episodios,
    metricas_sesion,
    reduccion_pct,
)

INICIO = "INICIO_MALA_POSTURA"
FIN = "FIN_MALA_POSTURA"
SESION = {"inicio": "2026-11-22T10:00:00", "fin": "2026-11-22T11:00:00"}


class PruebasMetricas(unittest.TestCase):
    def test_duraciones(self):
        eventos = [
            (INICIO, "2026-11-22T10:10:00"), (FIN, "2026-11-22T10:12:00"),
            (INICIO, "2026-11-22T10:30:00"), (FIN, "2026-11-22T10:30:30"),
        ]
        self.assertEqual(duraciones_episodios(eventos), [120.0, 30.0])

    def test_episodio_abierto_se_cierra_al_fin_de_sesion(self):
        eventos = [(INICIO, "2026-11-22T10:58:00")]
        self.assertEqual(
            duraciones_episodios(eventos, SESION["fin"]), [120.0])
        self.assertEqual(duraciones_episodios(eventos), [])

    def test_fin_sin_inicio_se_ignora(self):
        self.assertEqual(
            duraciones_episodios([(FIN, "2026-11-22T10:00:00")]), [])

    def test_metricas_sesion(self):
        eventos = [
            (INICIO, "2026-11-22T10:10:00"), (FIN, "2026-11-22T10:12:00"),
            (INICIO, "2026-11-22T10:30:00"), (FIN, "2026-11-22T10:30:30"),
        ]
        m = metricas_sesion(SESION, eventos)
        self.assertEqual(m["episodios"], 2)
        self.assertEqual(m["segundos_mala_postura"], 150.0)
        self.assertEqual(m["segundos_monitoreados"], 3600.0)
        self.assertAlmostEqual(m["pct_mala_postura"], 150 / 36)
        self.assertEqual(m["duracion_media_episodio"], 75.0)

    def test_sesion_sin_cerrar(self):
        m = metricas_sesion({"inicio": "2026-11-22T10:00:00", "fin": None},
                            [])
        self.assertEqual(m["segundos_monitoreados"], 0.0)
        self.assertEqual(m["pct_mala_postura"], 0.0)

    def test_agregar_pondera_por_tiempo(self):
        a = {"episodios": 2, "segundos_mala_postura": 100.0,
             "segundos_monitoreados": 1000.0}
        b = {"episodios": 1, "segundos_mala_postura": 50.0,
             "segundos_monitoreados": 3000.0}
        r = agregar([a, b])
        self.assertEqual(r["sesiones"], 2)
        self.assertAlmostEqual(r["pct_mala_postura"], 150 / 40)
        self.assertAlmostEqual(r["episodios_por_hora"], 3 * 3600 / 4000)

    def test_reduccion(self):
        self.assertEqual(reduccion_pct(10.0, 5.0), 50.0)
        self.assertIsNone(reduccion_pct(0.0, 5.0))

    def test_comparar_cumple_y_no_cumple(self):
        control = {"pct_mala_postura": 20.0, "episodios_por_hora": 10.0}
        mejor = {"pct_mala_postura": 10.0, "episodios_por_hora": 4.0}
        poco = {"pct_mala_postura": 18.0, "episodios_por_hora": 9.0}
        self.assertTrue(comparar(control, mejor)["cumple_hipotesis"])
        self.assertFalse(comparar(control, poco)["cumple_hipotesis"])
        exacto = {"pct_mala_postura": 16.0, "episodios_por_hora": 8.0}
        self.assertTrue(comparar(control, exacto)["cumple_hipotesis"])


if __name__ == "__main__":
    unittest.main()
