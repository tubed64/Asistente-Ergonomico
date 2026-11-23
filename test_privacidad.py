"""RNF-02: el codigo no guarda imagenes ni abre conexiones de red."""

import glob
import os
import unittest

PROHIBIDO = (
    "imwrite", "VideoWriter", "import socket", "import requests",
    "urllib", "http.client", "import ftplib", "import smtplib",
)


class PruebasPrivacidad(unittest.TestCase):
    def test_sin_guardado_de_imagenes_ni_red(self):
        carpeta = os.path.dirname(os.path.abspath(__file__))
        archivos = [
            ruta for ruta in glob.glob(os.path.join(carpeta, "*.py"))
            if not os.path.basename(ruta).startswith("test_")
        ]
        self.assertGreater(len(archivos), 0)
        for ruta in archivos:
            with open(ruta, encoding="utf-8") as f:
                codigo = f.read()
            for texto in PROHIBIDO:
                self.assertNotIn(
                    texto, codigo,
                    f"{os.path.basename(ruta)} contiene {texto!r}")


if __name__ == "__main__":
    unittest.main()
