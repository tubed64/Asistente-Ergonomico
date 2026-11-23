"""Persistencia en SQLite: sesiones de monitoreo y eventos posturales."""

import sqlite3
from datetime import datetime

MODOS = ("CONTROL", "INTERVENCION")
CAMPOS_EDITABLES = ("participante", "modo", "notas")


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _validar_modo(modo):
    modo = str(modo).strip().upper()
    if modo not in MODOS:
        raise ValueError(f"Modo invalido: {modo!r}. Usa {' o '.join(MODOS)}.")
    return modo


def _validar_participante(participante):
    participante = str(participante).strip()
    if not participante:
        raise ValueError("El participante no puede estar vacio.")
    return participante


class RegistroPostura:
    """Acceso a la base de datos local.

    Tablas:
      sesiones     -> una fila por ejecucion del programa (CRUD completo).
      logs_postura -> eventos INICIO/FIN de mala postura de cada sesion.
    """

    def __init__(self, ruta="registro_postura.db"):
        self.conn = sqlite3.connect(ruta)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._crear_esquema()

    def _crear_esquema(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS sesiones (
                   id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
                   participante TEXT NOT NULL,
                   modo TEXT NOT NULL
                       CHECK (modo IN ('CONTROL', 'INTERVENCION')),
                   inicio TEXT NOT NULL,
                   fin TEXT,
                   fps_promedio REAL,
                   cuadros INTEGER,
                   notas TEXT NOT NULL DEFAULT '')"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS logs_postura (
                   id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
                   estado TEXT NOT NULL,
                   fecha_hora TEXT NOT NULL,
                   id_sesion INTEGER
                       REFERENCES sesiones(id_sesion) ON DELETE CASCADE)"""
        )
        # Migracion: bases creadas con la version anterior (3 columnas)
        columnas = [f[1] for f in
                    self.conn.execute("PRAGMA table_info(logs_postura)")]
        if "id_sesion" not in columnas:
            self.conn.execute(
                "ALTER TABLE logs_postura ADD COLUMN id_sesion INTEGER "
                "REFERENCES sesiones(id_sesion) ON DELETE CASCADE"
            )
        self.conn.commit()

    # ---------------------------------------------------------- eventos
    def registrar(self, estado, id_sesion=None):
        """Inserta un evento postural con la fecha y hora actuales."""
        self.conn.execute(
            "INSERT INTO logs_postura (estado, fecha_hora, id_sesion) "
            "VALUES (?, ?, ?)",
            (estado, _ahora(), id_sesion),
        )
        self.conn.commit()

    def listar_eventos(self, id_sesion=None):
        if id_sesion is None:
            consulta = ("SELECT id_evento, estado, fecha_hora, id_sesion "
                        "FROM logs_postura ORDER BY id_evento")
            return self.conn.execute(consulta).fetchall()
        consulta = ("SELECT id_evento, estado, fecha_hora, id_sesion "
                    "FROM logs_postura WHERE id_sesion = ? "
                    "ORDER BY id_evento")
        return self.conn.execute(consulta, (id_sesion,)).fetchall()

    # ---------------------------------------------------------- sesiones
    def crear_sesion(self, participante, modo, notas=""):
        """CREATE: abre una sesion y devuelve su id."""
        cursor = self.conn.execute(
            "INSERT INTO sesiones (participante, modo, inicio, notas) "
            "VALUES (?, ?, ?, ?)",
            (_validar_participante(participante), _validar_modo(modo),
             _ahora(), notas),
        )
        self.conn.commit()
        return cursor.lastrowid

    def obtener_sesion(self, id_sesion):
        """READ: devuelve un diccionario o None si no existe."""
        fila = self.conn.execute(
            "SELECT * FROM sesiones WHERE id_sesion = ?", (id_sesion,)
        ).fetchone()
        return dict(fila) if fila else None

    def listar_sesiones(self, participante=None):
        """READ: todas las sesiones, o solo las de un participante."""
        if participante is None:
            filas = self.conn.execute(
                "SELECT * FROM sesiones ORDER BY id_sesion").fetchall()
        else:
            filas = self.conn.execute(
                "SELECT * FROM sesiones WHERE participante = ? "
                "ORDER BY id_sesion", (participante,)).fetchall()
        return [dict(f) for f in filas]

    def actualizar_sesion(self, id_sesion, **campos):
        """UPDATE: modifica participante, modo y/o notas.

        Devuelve True si la sesion existia.
        """
        if not campos:
            raise ValueError("No hay campos para actualizar.")
        invalidos = set(campos) - set(CAMPOS_EDITABLES)
        if invalidos:
            raise ValueError(f"Campos no editables: {sorted(invalidos)}")
        if "modo" in campos:
            campos["modo"] = _validar_modo(campos["modo"])
        if "participante" in campos:
            campos["participante"] = _validar_participante(
                campos["participante"])
        # Los nombres de columna salen de la lista blanca de arriba;
        # los valores siempre viajan como parametros (?).
        asignaciones = ", ".join(f"{c} = ?" for c in campos)
        cursor = self.conn.execute(
            f"UPDATE sesiones SET {asignaciones} WHERE id_sesion = ?",
            (*campos.values(), id_sesion),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def finalizar_sesion(self, id_sesion, fps_promedio=None, cuadros=None):
        """Cierra la sesion guardando fin, FPS promedio y cuadros."""
        self.conn.execute(
            "UPDATE sesiones SET fin = ?, fps_promedio = ?, cuadros = ? "
            "WHERE id_sesion = ?",
            (_ahora(), fps_promedio, cuadros, id_sesion),
        )
        self.conn.commit()

    def eliminar_sesion(self, id_sesion):
        """DELETE: borra la sesion y, en cascada, sus eventos."""
        cursor = self.conn.execute(
            "DELETE FROM sesiones WHERE id_sesion = ?", (id_sesion,))
        self.conn.commit()
        return cursor.rowcount > 0

    def cerrar(self):
        self.conn.close()
