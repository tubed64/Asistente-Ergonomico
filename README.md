# Asistente Ergonómico de Escritorio (MVP)

Prototipo que vigila la postura con la cámara web y avisa cuando el usuario
se encorva de forma sostenida. Todo se procesa en local: no se guardan
imágenes ni se usa internet.

Proyecto Integrador Dual (UNITEC, Ingeniería en Sistemas Computacionales).
Hipótesis: recibir alertas visuales reduce al menos 20 % el tiempo
acumulado en mala postura frente a no recibirlas.

## Instalación

Requiere Python 3.10, 3.11 o 3.12 (MediaPipe aún no soporta 3.13).

```bash
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
# Fase CON alertas (modo por defecto)
python main.py --participante ana --modo intervencion

# Fase de CONTROL: monitorea y registra, pero no muestra alertas
python main.py --participante ana --modo control
```

Teclas: `c` calibra la postura ideal (sentado derecho), `q` sale.

Otras herramientas:

```bash
python reporte.py                      # métricas por sesión y comparación A/B
python reporte.py --csv metricas.csv   # exportar para análisis estadístico
python gestor_datos.py listar          # CRUD de sesiones (crear, ver, editar, eliminar)
python -m unittest -v                  # pruebas unitarias (no necesitan cámara)
```

## Estructura (MVC + capas)

| Archivo | Rol |
|---|---|
| `main.py` | Controlador: ciclo de captura, teclas, coordina todo |
| `vista.py` | Vista: HUD, alerta grande, FPS, mensajes |
| `evaluador.py` | Modelo: calibración, umbral del 20 %, temporizador de 5 s |
| `medicion.py` | Modelo: medida ojos-hombros normalizada |
| `registro_db.py` | Modelo: SQLite (sesiones y eventos, CRUD) |
| `metricas.py` | Cálculo de métricas y comparación control/intervención |
| `reporte.py` | Reporte en consola y exportación a CSV |
| `gestor_datos.py` | CRUD de sesiones por línea de comandos |
| `MANUAL.md` | Manual de usuario y técnico, trazabilidad requisitos → pruebas |

## Base de datos (`registro_postura.db`)

- `sesiones`: `id_sesion`, `participante`, `modo` (CONTROL o INTERVENCION),
  `inicio`, `fin`, `fps_promedio`, `cuadros`, `notas`.
- `logs_postura`: `id_evento`, `estado` (`INICIO_MALA_POSTURA` o
  `FIN_MALA_POSTURA`), `fecha_hora` (ISO 8601), `id_sesion`.

Las bases creadas con la versión anterior se migran solas al abrirlas.

Más detalle en [MANUAL.md](MANUAL.md).
