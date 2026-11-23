# Manual del Asistente Ergonómico (versión inicial, semana 10)

## Parte 1. Manual de usuario

### 1.1 Qué hace
Usa la cámara web para ubicar ojos y hombros, compara tu postura con la que
calibraste y, si te encorvas más de 5 segundos seguidos, muestra una alerta
roja. Registra cada episodio en una base de datos local.

### 1.2 Antes de empezar
- Cámara conectada y sin que otra aplicación la esté usando.
- Buena iluminación y la parte superior del torso visible (ojos y ambos
  hombros).
- Instalación: ver `README.md`.

### 1.3 Usar el programa
1. Ejecuta `python main.py --participante TU_NOMBRE --modo intervencion`.
2. Siéntate derecho, como te recomendaría un fisioterapeuta, y presiona `c`.
   Verás el mensaje "Calibracion guardada". Puedes recalibrar cuando
   quieras.
3. Trabaja con normalidad. El texto superior muestra el estado:
   "Postura optima", "Desviacion detectada..." (aún no alerta) o "Peligro
   inminente" (alerta grande tras 5 s).
4. Presiona `q` para salir. La sesión queda guardada.

Si la cámara se desconecta, aparece "Camara no disponible. Reintentando..."
y el programa intenta reconectarse unos 30 segundos antes de cerrar.

### 1.4 Protocolo recomendado para el experimento (A/B intrapersonal)
- Mismo participante, misma tarea, misma hora y duración similar
  (por ejemplo 30 a 60 minutos) en cada sesión.
- Alterna el orden: unas veces `--modo control` primero y otras
  `--modo intervencion` primero, para no confundir el efecto con el orden.
- En `control` el programa registra igual, pero no muestra alertas ni
  esqueleto, así que no hay retroalimentación.
- Calibra siempre al inicio de cada sesión.
- Repite varias sesiones por modo; una sola sesión por modo no alcanza para
  concluir.

### 1.5 Ver resultados
```bash
python reporte.py                       # tabla por sesión y comparación
python reporte.py --participante ana    # solo un participante
python reporte.py --csv metricas.csv    # exportar (abre bien en Excel)
```

### 1.6 Gestionar sesiones (CRUD)
```bash
python gestor_datos.py listar
python gestor_datos.py ver 3                      # detalle, métricas y eventos
python gestor_datos.py crear --participante ana --modo control
python gestor_datos.py editar 3 --notas "luz baja" --modo intervencion
python gestor_datos.py eliminar 3                 # pide confirmación; --si la omite
```
Eliminar una sesión borra también sus eventos.

### 1.7 Problemas frecuentes
| Síntoma | Qué hacer |
|---|---|
| "No se pudo abrir la camara" | Cierra otras apps que la usen; prueba `--camara 1` |
| Siempre "Seguimiento no disponible" | Más luz; que se vean ojos y ambos hombros |
| Alerta demasiado sensible | Recalibra sentado derecho; ajusta `--tolerancia 0.25` |
| FPS bajos | Cierra otras aplicaciones; el FPS se ve en la esquina inferior |

## Parte 2. Manual técnico

### 2.1 Arquitectura
Se mantiene la arquitectura por capas del documento (sensor, inferencia,
control y análisis, presentación y persistencia). Dentro del código se
organiza con el patrón MVC:

- **Modelo:** `evaluador.py`, `medicion.py`, `registro_db.py`, `metricas.py`.
- **Vista:** `vista.py`.
- **Controlador:** `main.py` (captura con OpenCV, inferencia con MediaPipe
  como servicio, teclado, y coordinación).

### 2.2 Medida postural
`medida = (y_medio_hombros - y_medio_ojos) / ancho_de_hombros`, con
coordenadas normalizadas de MediaPipe. Dividir entre el ancho de hombros
hace que la medida no dependa de la distancia a la cámara. Si algún punto
tiene visibilidad menor a 0.5, la medida es `None` (sin detección).

### 2.3 Máquina de estados (`evaluador.py`)
| Estado | Condición |
|---|---|
| CALIBRANDO | Aún no hay referencia |
| SIN_DETECCION | Medida `None`; reinicia el temporizador y cierra el episodio |
| POSTURA_OK | Medida >= 80 % de la referencia |
| VIGILANDO | Medida < 80 % de la referencia, pero aún dentro de los 5 s |
| MALA_POSTURA | Desviación sostenida más de 5 s; emite `INICIO_MALA_POSTURA` |

Al volver a POSTURA_OK se emite `FIN_MALA_POSTURA`. El temporizador compara
marcas de tiempo en cada fotograma (`time.monotonic`); no usa hilos.

### 2.4 Base de datos (SQLite)
- `sesiones`: una fila por ejecución. `modo` solo admite `CONTROL` o
  `INTERVENCION` (restricción CHECK).
- `logs_postura`: eventos con `id_sesion` (clave foránea con borrado en
  cascada). Consultas siempre parametrizadas con `?`.
- CRUD de sesiones en `registro_db.py`: `crear_sesion`, `obtener_sesion`,
  `listar_sesiones`, `actualizar_sesion` (solo participante, modo y notas) y
  `eliminar_sesion`.

### 2.5 Métricas (instrumentación)
| Métrica | Definición |
|---|---|
| Episodio | Intervalo entre `INICIO_MALA_POSTURA` y `FIN_MALA_POSTURA` |
| % en mala postura | Segundos en episodios / segundos monitoreados |
| Episodios por hora | Episodios / horas monitoreadas |
| Duración media | Segundos en mala postura / número de episodios |
| FPS promedio | Cuadros procesados / tiempo activo (excluye cámara caída) |

Las agregaciones por modo se ponderan por tiempo monitoreado. La reducción
es `(CONTROL - INTERVENCION) / CONTROL`. La hipótesis se considera
cumplida si la reducción del % en mala postura es de al menos 20 %. Un
episodio abierto al cerrar la sesión se cierra al momento de `fin`.

### 2.6 Limitaciones conocidas
- Con cámara frontal, la distancia ojos-hombros puede no bajar al
  inclinarse hacia la pantalla. Hay que validar con pruebas reales que la
  medida reacciona al encorvarse; si no, usar profundidad (`z`) o vista
  lateral.
- Los 5 s de holgura se descuentan del registro: el episodio empieza a
  contarse cuando se emite la alerta, no cuando empezó la desviación.
- En modo control el participante sabe que lo están monitoreando; puede
  modificar su conducta (efecto de observación).
- Los resultados dependen de la iluminación, la calibración y la tarea.

## Parte 3. Trazabilidad requisitos → implementación → pruebas

| Requisito | Implementación | Prueba o verificación |
|---|---|---|
| RF-01 Captura a >= 30 FPS | `main.py` (`abrir_camara`, contador de FPS) | Manual: FPS visible en pantalla y guardado en `sesiones` |
| RF-02 Extracción de ojos y hombros | `medicion.py` | `test_medicion.py` |
| RF-03 Calibración con `c` | `evaluador.calibrar`, `main.py` | `test_evaluador.py::test_sin_calibrar`; mensaje manual |
| RF-04 Desviación continua | `evaluador.actualizar` | `test_evaluador.py::test_postura_ok`, `test_alerta_solo_tras_holgura` |
| RF-05 Temporizador de holgura | `evaluador.actualizar` | `test_evaluador.py::test_alerta_solo_tras_holgura`, `test_correccion_antes_de_holgura_reinicia` |
| RF-06 Alerta visual grande | `vista._banner` | Manual: banner rojo; modo control sin alerta |
| RF-07 Registro en SQLite | `registro_db.py` | `test_registro.py`, `test_evaluador.py::PruebasBaseDeDatos` |
| RF-08 HUD de estatus | `vista.dibujar_hud` | Manual (probado el dibujo en todos los estados) |
| RF-09 Salida limpia con `q` | `main.py` (bloque `finally`) | `test_evaluador.py::test_cerrar_al_salir`; manual |
| RNF-02 Privacidad | Sin guardado de imágenes ni red | `test_privacidad.py` |
| RNF-03 Tolerancia a fallos de cámara | `main.py` (reintentos) | Manual: desconectar y reconectar la cámara |
| HU-01 Calibración personalizada | `evaluador`, `vista` | Manual: mensaje "Calibracion guardada" |
| HU-02 Mitigación de falsos positivos | `evaluador` | `test_evaluador.py` |
| HU-03 Log automático | `registro_db.py` | `test_registro.py` |
| CRUD completo (semana 10) | `registro_db.py`, `gestor_datos.py` | `test_registro.py`, `test_reporte.py::PruebasGestor` |
| Instrumentación de métricas | `metricas.py`, `reporte.py` | `test_metricas.py`, `test_reporte.py` |
