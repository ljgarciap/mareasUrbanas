"""Pruebas de desempeño del motor de navegación. Genera resultados/*.json y *.csv."""
import csv, json, random, statistics, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from navegacion.grafo import generar_ciudad
from navegacion.estrategias import BFS, Dijkstra, AEstrella, Bidireccional
from navegacion.trafico import SensorTrafico
from navegacion.cache import CacheRutas
from navegacion.navegador import Navegador, SesionNavegacion

OUT = pathlib.Path(__file__).resolve().parent / "resultados"
OUT.mkdir(exist_ok=True)
ESTR = [BFS(), Dijkstra(), AEstrella(), Bidireccional()]


def pares_lejanos(g, n, rnd):
    """Pares origen-destino separados al menos 1/3 del lado del mapa."""
    xs = [c[0] for c in g.coords.values()]
    minimo = (max(xs) - min(xs)) / 3
    import math
    out = []
    while len(out) < n:
        o, d = rnd.randrange(g.n_nodos), rnd.randrange(g.n_nodos)
        if math.dist(g.coords[o], g.coords[d]) >= minimo:
            out.append((o, d))
    return out


def p95(v):
    v = sorted(v); return v[int(0.95 * (len(v) - 1))]


def e1_escala():
    filas = []
    for lado in (20, 40, 80, 120):
        g = generar_ciudad(lado, lado, seed=11)
        rnd = random.Random(100 + lado)
        pares = pares_lejanos(g, 100, rnd)
        ref = [Dijkstra().buscar(g, o, d).costo_s for o, d in pares]
        for e in ESTR:
            ms, exp, gap = [], [], []
            for (o, d), c0 in zip(pares, ref):
                r = e.buscar(g, o, d)
                ms.append(r.tiempo_calculo_ms); exp.append(r.nodos_expandidos)
                gap.append((r.costo_s - c0) / c0 * 100 if c0 > 0 else 0)
            filas.append(dict(nodos=g.n_nodos, aristas=g.n_aristas, estrategia=e.nombre,
                              ms_media=round(statistics.mean(ms), 3), ms_p95=round(p95(ms), 3),
                              expandidos_media=round(statistics.mean(exp), 1),
                              brecha_optimalidad_pct=round(abs(statistics.mean(gap)) if abs(statistics.mean(gap))<1e-6 else statistics.mean(gap), 2) + 0.0))
            print(filas[-1], flush=True)
    return filas


def e2_cache(lado=80, solicitudes=3000):
    res = {}
    for con_cache in (False, True):
        g = generar_ciudad(lado, lado, seed=11)
        rnd = random.Random(2026)
        calientes = pares_lejanos(g, 60, rnd)      # trayectos populares
        frios = pares_lejanos(g, 400, rnd)
        sensor = SensorTrafico(g)
        cache = CacheRutas() if con_cache else None
        if cache is not None:
            sensor.suscribir(cache)
        nav = Navegador(g, AEstrella(), cache)
        vias = [(a, e.destino) for a in list(g.coords)[::7] for e in g.vecinos(a)]
        incidentes = []
        t0 = time.perf_counter()
        for i in range(solicitudes):
            if i and i % 250 == 0:                  # incidente nuevo o recuperación
                if incidentes and rnd.random() < 0.3:
                    a, b = incidentes.pop(); sensor.reportar(a, b, 1.0)
                else:
                    a, b = rnd.choice(vias); sensor.reportar(a, b, rnd.choice((3.0, 5.0, 8.0))); incidentes.append((a, b))
            o, d = rnd.choice(calientes) if rnd.random() < 0.8 else rnd.choice(frios)
            nav.calcular(o, d)
        seg = time.perf_counter() - t0
        res["con_cache" if con_cache else "sin_cache"] = dict(
            segundos=round(seg, 3), solicitudes_por_s=round(solicitudes / seg, 1),
            tasa_aciertos=round(cache.tasa_aciertos, 3) if cache is not None else None,
            invalidaciones=cache.invalidaciones if cache is not None else None)
        if cache is not None:     # validar que las rutas servidas desde caché siguen siendo óptimas
            malas = 0
            for (o, d, _), r in list(cache._datos.items()):
                ref = Dijkstra().buscar(g, o, d).costo_s
                if abs(ref - TramoCosto(g, r.camino)) > 1e-6 * max(1, ref):
                    malas += 1
            res["con_cache"]["entradas_validadas"] = len(cache)
            res["con_cache"]["entradas_no_optimas"] = malas
    res["mejora_x"] = round(res["con_cache"]["solicitudes_por_s"] / res["sin_cache"]["solicitudes_por_s"], 2)
    print(res, flush=True)
    return res


def TramoCosto(g, camino):
    return sum(g.arista(a, b).tiempo_s for a, b in zip(camino, camino[1:]))


def e3_reroute(lado=80, sesiones=100):
    g = generar_ciudad(lado, lado, seed=11)
    rnd = random.Random(55)
    pares = pares_lejanos(g, sesiones, rnd)
    sensor = SensorTrafico(g)
    nav = Navegador(g, AEstrella())
    ms, ganancia = [], []
    for o, d in pares:
        s = SesionNavegacion(nav, o, d); sensor.suscribir(s)
        if len(s.camino) < 6:
            sensor.desuscribir(s); continue
        s.avanzar(len(s.camino) // 3)
        a, b = s.camino[s.pos], s.camino[s.pos + 1]
        antiguo = s.restante
        sensor.reportar(a, b, 10.0)                       # incidente justo adelante
        costo_si_sigue = TramoCosto(g, antiguo)           # lo que costaría no reaccionar
        costo_nuevo = TramoCosto(g, s.restante)
        ms.extend(s.ms_reroute); ganancia.append((costo_si_sigue - costo_nuevo))
        sensor.reportar(a, b, 1.0)                        # restablece para la siguiente sesión
        sensor.desuscribir(s)
    r = dict(sesiones=len(ganancia), ms_recalculo_media=round(statistics.mean(ms), 2),
             ms_recalculo_p95=round(p95(ms), 2),
             ahorro_s_medio=round(statistics.mean(ganancia), 1),
             ahorro_s_max=round(max(ganancia), 1))
    print(r, flush=True)
    return r


if __name__ == "__main__":
    e1 = e1_escala(); e2 = e2_cache(); e3 = e3_reroute()
    (OUT / "resultados.json").write_text(json.dumps(dict(escala=e1, cache=e2, reroute=e3), indent=2, ensure_ascii=False))
    with open(OUT / "escala.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(e1[0])); w.writeheader(); w.writerows(e1)
