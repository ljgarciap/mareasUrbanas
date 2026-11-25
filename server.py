"""Interfaz web local de Mareas Urbanas (solo biblioteca estándar).
Uso: python3 server.py [puerto]  ->  http://localhost:8000"""
import json, pathlib, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from navegacion.grafo import generar_ciudad
from navegacion.estrategias import ESTRATEGIAS
from navegacion.trafico import SensorTrafico
from navegacion.cache import CacheRutas
from navegacion.navegador import Navegador, SesionNavegacion
from navegacion.comandos import Invocador, ReportarIncidenteComando
from navegacion.ruta import IteradorInstrucciones

WEB = pathlib.Path(__file__).resolve().parent / "web"
LOCK = threading.Lock()


class Estado:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.g = generar_ciudad(40, 40, seed=11)
        self.sensor = SensorTrafico(self.g)
        self.cache = CacheRutas()
        self.sensor.suscribir(self.cache)
        self.nav = Navegador(self.g, cache=self.cache)
        self.inv = Invocador()
        self.sesion = None


E_ = Estado()


def congestionadas():
    out = []
    for a, lst in E_.g.adyacencia.items():
        for e in lst:
            if a < e.destino and e.congestion > 1.0:
                out.append([a, e.destino, e.congestion])
    return out


def resumen_sesion():
    s = E_.sesion
    base = {"congestion": congestionadas(),
            "cache": {"aciertos": E_.cache.aciertos, "fallos": E_.cache.fallos,
                      "invalidaciones": E_.cache.invalidaciones, "tamano": len(E_.cache)}}
    if s:
        base.update(camino=s.restante, actual=s.actual, recalculos=s.reroutes,
                    minutos=round(sum(E_.g.arista(a, b).tiempo_s for a, b in zip(s.restante, s.restante[1:])) / 60, 2),
                    llegó=s.actual == s.destino,
                    instrucciones=list(IteradorInstrucciones(E_.g, s.restante)))
    return base


def api(path, d):
    if path == "/api/mapa":
        g = E_.g
        return {"coords": [g.coords[i] for i in range(g.n_nodos)],
                "aristas": [[a, e.destino, e.velocidad_kmh] for a, l in g.adyacencia.items() for e in l if a < e.destino]}
    if path == "/api/estado":
        return resumen_sesion()
    if path == "/api/ruta":
        o, dst = int(d["o"]), int(d["d"])
        E_.nav.cambiar_estrategia(ESTRATEGIAS[d.get("estrategia", "astar")]())
        antes = E_.cache.aciertos
        r = E_.nav.calcular(o, dst)
        acierto = E_.cache.aciertos > antes
        if E_.sesion:
            E_.sensor.desuscribir(E_.sesion)
        E_.sesion = SesionNavegacion(E_.nav, o, dst, resultado=r)
        E_.sensor.suscribir(E_.sesion)
        out = resumen_sesion()
        out.update(encontrado=r.encontrado, expandidos=r.nodos_expandidos, ms=round(r.tiempo_calculo_ms, 3),
                   desde_cache=acierto, estrategia=r.estrategia)
        return out
    if path == "/api/comparar":
        o, dst = int(d["o"]), int(d["d"])
        res = []
        for k, cls in ESTRATEGIAS.items():
            r = cls().buscar(E_.g, o, dst)
            res.append({"clave": k, "estrategia": r.estrategia, "camino": r.camino, "minutos": round(r.costo_s / 60, 2),
                        "expandidos": r.nodos_expandidos, "ms": round(r.tiempo_calculo_ms, 3)})
        return {"resultados": res}
    if path == "/api/avanzar":
        if E_.sesion:
            E_.sesion.avanzar(int(d.get("pasos", 1)))
        return resumen_sesion()
    if path == "/api/incidente":
        E_.inv.ejecutar(ReportarIncidenteComando(E_.sensor, int(d["a"]), int(d["b"]), float(d.get("factor", 10))))
        return resumen_sesion()
    if path == "/api/deshacer":
        E_.inv.deshacer_ultimo()
        return resumen_sesion()
    if path == "/api/reiniciar":
        E_.reiniciar()
        return resumen_sesion()
    raise KeyError(path)


class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            b = (WEB / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif self.path.startswith("/api/"):
            self._run({})
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self._run(json.loads(self.rfile.read(n) or b"{}"))

    def _run(self, d):
        try:
            with LOCK:
                self._json(api(self.path, d))
        except Exception as ex:
            self._json({"error": str(ex)}, 400)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Mareas Urbanas en http://localhost:{puerto}  (Ctrl+C para salir)")
    ThreadingHTTPServer(("127.0.0.1", puerto), H).serve_forever()
