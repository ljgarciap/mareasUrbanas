# Mareas Urbanas — motor de navegación con patrones de diseño

Prototipo de la Actividad 6 (Arquitectura de software, Unidad 3). Calcula rutas de menor tiempo
sobre un mapa con tráfico variable y las recalcula cuando ocurre un incidente.

## Patrones aplicados
Strategy (BFS, Dijkstra, A*, bidireccional), Observer (sensor de tráfico, caché, sesiones),
Command (solicitudes con historial y deshacer), Composite (rutas multiparada) e Iterator (instrucciones de giro).

## Cómo ejecutarlo
Requiere Python 3.10+. El núcleo no tiene dependencias; `demo.py` usa matplotlib para las figuras.

    python3 tests/test_navegacion.py   # 7 pruebas unitarias
    python3 demo.py                    # demostración y figuras en resultados/
    python3 benchmark.py               # pruebas de desempeño (resultados/resultados.json)
    python3 server.py                  # interfaz web: abrir http://localhost:8000

## Estructura
- `navegacion/`: grafo, estrategias, tráfico (Observer), caché, navegador, rutas, comandos.
- `server.py` y `web/index.html`: interfaz web local (mapa interactivo, sin dependencias).
- `resultados/`: salidas de las pruebas (JSON, CSV, figuras).

El mapa es una ciudad sintética generada con semilla fija, no datos reales; las cifras sirven para comparar estrategias.
