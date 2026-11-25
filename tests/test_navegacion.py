import math, random, sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from navegacion.grafo import generar_ciudad
from navegacion.estrategias import BFS, Dijkstra, AEstrella, Bidireccional
from navegacion.trafico import SensorTrafico
from navegacion.cache import CacheRutas
from navegacion.navegador import Navegador, SesionNavegacion
from navegacion.comandos import Invocador, CalcularRutaComando, ReportarIncidenteComando
from navegacion.ruta import IteradorInstrucciones


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.g = generar_ciudad(30, 30, seed=3)
        rnd = random.Random(1)
        n = self.g.n_nodos
        self.pares = [(rnd.randrange(n), rnd.randrange(n)) for _ in range(60)]

    def test_estrategias_optimas_coinciden_con_dijkstra(self):
        for o, d in self.pares:
            ref = Dijkstra().buscar(self.g, o, d).costo_s
            for E in (AEstrella, Bidireccional):
                self.assertAlmostEqual(E().buscar(self.g, o, d).costo_s, ref, places=6)

    def test_astar_expande_menos_nodos(self):
        dj = sum(Dijkstra().buscar(self.g, o, d).nodos_expandidos for o, d in self.pares)
        a = sum(AEstrella().buscar(self.g, o, d).nodos_expandidos for o, d in self.pares)
        self.assertLess(a, dj)

    def test_bfs_nunca_mejora_a_dijkstra(self):
        for o, d in self.pares:
            self.assertGreaterEqual(BFS().buscar(self.g, o, d).costo_s + 1e-9,
                                    Dijkstra().buscar(self.g, o, d).costo_s)

    def test_cache_aciertos_y_invalidacion(self):
        sensor, cache = SensorTrafico(self.g), CacheRutas()
        sensor.suscribir(cache)
        nav = Navegador(self.g, cache=cache)
        o, d = self.pares[0]
        r1 = nav.calcular(o, d); nav.calcular(o, d)
        self.assertEqual(cache.aciertos, 1)
        a, b = r1.camino[0], r1.camino[1]
        sensor.reportar(a, b, 10.0)             # empeora una vía de la ruta guardada
        self.assertEqual(len(cache), 0)
        r2 = nav.calcular(o, d)
        self.assertGreaterEqual(r2.costo_s, r1.costo_s - 1e-9)

    def test_sesion_recalcula_ante_incidente(self):
        sensor = SensorTrafico(self.g)
        nav = Navegador(self.g)
        o, d = max(self.pares, key=lambda p: math.dist(self.g.coords[p[0]], self.g.coords[p[1]]))
        s = SesionNavegacion(nav, o, d); sensor.suscribir(s)
        s.avanzar(2)
        a, b = s.camino[s.pos], s.camino[s.pos + 1]
        sensor.reportar(a, b, 50.0)
        self.assertEqual(s.reroutes, 1)
        self.assertNotIn((a, b), list(zip(s.camino, s.camino[1:])))

    def test_comando_deshacer_restaura_trafico(self):
        sensor, inv = SensorTrafico(self.g), Invocador()
        o, d = self.pares[1]
        nav = Navegador(self.g)
        base = inv.ejecutar(CalcularRutaComando(nav, o, d)).costo_s
        a, b = nav.calcular(o, d).camino[:2]
        inv.ejecutar(ReportarIncidenteComando(sensor, a, b, 20.0))
        self.assertGreaterEqual(nav.calcular(o, d).costo_s, base)
        inv.deshacer_ultimo()
        self.assertAlmostEqual(nav.calcular(o, d).costo_s, base, places=6)

    def test_composite_suma_tramos_e_iterador(self):
        nav = Navegador(self.g)
        p = [self.pares[0][0], self.pares[1][0], self.pares[2][0]]
        ruta = nav.ruta_multiparada(p)
        t = sum(nav.calcular(a, b).costo_s for a, b in zip(p, p[1:]))
        self.assertAlmostEqual(ruta.tiempo_s(), t, places=6)
        nodos = list(ruta)
        self.assertEqual(nodos[0], p[0]); self.assertEqual(nodos[-1], p[-1])
        self.assertTrue(len(list(IteradorInstrucciones(self.g, nodos))) >= 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
