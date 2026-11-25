"""Patrón Strategy: algoritmos de búsqueda de rutas intercambiables."""
from __future__ import annotations
import heapq
import math
import time
from abc import ABC, abstractmethod
from collections import deque

from .grafo import Grafo
from .ruta import ResultadoBusqueda

INF = float("inf")


class EstrategiaRuta(ABC):
    nombre = "abstracta"

    def buscar(self, g: Grafo, origen: int, destino: int) -> ResultadoBusqueda:
        t0 = time.perf_counter()
        camino, costo, expandidos = self._resolver(g, origen, destino)
        ms = (time.perf_counter() - t0) * 1000
        return ResultadoBusqueda(camino, costo, expandidos, ms, self.nombre)

    @abstractmethod
    def _resolver(self, g: Grafo, o: int, d: int) -> tuple[list[int], float, int]: ...

    @staticmethod
    def _reconstruir(padre: dict[int, int], d: int) -> list[int]:
        cam = [d]
        while cam[-1] in padre:
            cam.append(padre[cam[-1]])
        return cam[::-1]

    @staticmethod
    def _costo(g: Grafo, camino: list[int]) -> float:
        return sum(g.arista(a, b).tiempo_s for a, b in zip(camino, camino[1:]))


class BFS(EstrategiaRuta):
    """Menos intersecciones (línea base): ignora distancias y tráfico."""
    nombre = "BFS (menos giros)"

    def _resolver(self, g, o, d):
        padre, visto, cola, exp = {}, {o}, deque([o]), 0
        while cola:
            u = cola.popleft(); exp += 1
            if u == d:
                cam = self._reconstruir(padre, d)
                return cam, self._costo(g, cam), exp
            for e in g.vecinos(u):
                if e.destino not in visto:
                    visto.add(e.destino); padre[e.destino] = u; cola.append(e.destino)
        return [], INF, exp


class Dijkstra(EstrategiaRuta):
    """Ruta de menor tiempo; referencia de optimalidad."""
    nombre = "Dijkstra"

    def _resolver(self, g, o, d):
        dist, padre, pq, exp = {o: 0.0}, {}, [(0.0, o)], 0
        hecho = set()
        while pq:
            c, u = heapq.heappop(pq)
            if u in hecho:
                continue
            hecho.add(u); exp += 1
            if u == d:
                return self._reconstruir(padre, d), c, exp
            for e in g.vecinos(u):
                nc = c + e.tiempo_s
                if nc < dist.get(e.destino, INF):
                    dist[e.destino] = nc; padre[e.destino] = u
                    heapq.heappush(pq, (nc, e.destino))
        return [], INF, exp


class AEstrella(EstrategiaRuta):
    """A*: Dijkstra guiado por heurística (distancia euclídea / velocidad máxima)."""
    nombre = "A*"

    def _resolver(self, g, o, d):
        xd, yd = g.coords[d]
        vmax = g.vel_max_kmh / 3.6
        h = lambda n: math.dist(g.coords[n], (xd, yd)) / vmax   # admisible: nunca sobrestima
        dist, padre, pq, exp = {o: 0.0}, {}, [(h(o), 0.0, o)], 0
        hecho = set()
        while pq:
            _, c, u = heapq.heappop(pq)
            if u in hecho:
                continue
            hecho.add(u); exp += 1
            if u == d:
                return self._reconstruir(padre, d), c, exp
            for e in g.vecinos(u):
                nc = c + e.tiempo_s
                if nc < dist.get(e.destino, INF):
                    dist[e.destino] = nc; padre[e.destino] = u
                    heapq.heappush(pq, (nc + h(e.destino), nc, e.destino))
        return [], INF, exp


class Bidireccional(EstrategiaRuta):
    """Dijkstra desde origen y destino a la vez; se detiene al cruzarse."""
    nombre = "Dijkstra bidireccional"

    def _resolver(self, g, o, d):
        if o == d:
            return [o], 0.0, 1
        inv = g.inversa()
        dist = ({o: 0.0}, {d: 0.0})
        padre = ({}, {})
        pq = ([(0.0, o)], [(0.0, d)])
        hecho = (set(), set())
        mejor, medio, exp = INF, None, 0
        while pq[0] and pq[1]:
            if pq[0][0][0] + pq[1][0][0] >= mejor:
                break
            lado = 0 if pq[0][0][0] <= pq[1][0][0] else 1
            c, u = heapq.heappop(pq[lado])
            if u in hecho[lado]:
                continue
            hecho[lado].add(u); exp += 1
            aristas = g.vecinos(u) if lado == 0 else inv[u]
            for e in aristas:
                v = e.destino if lado == 0 else e.origen
                nc = c + e.tiempo_s
                if nc < dist[lado].get(v, INF):
                    dist[lado][v] = nc; padre[lado][v] = u
                    heapq.heappush(pq[lado], (nc, v))
                if v in dist[1 - lado] and nc + dist[1 - lado][v] < mejor:
                    mejor, medio = nc + dist[1 - lado][v], v
        if medio is None:
            return [], INF, exp
        ida = [medio]
        while ida[-1] in padre[0]:
            ida.append(padre[0][ida[-1]])
        ida = ida[::-1]
        vuelta = []
        n = medio
        while n in padre[1]:
            n = padre[1][n]; vuelta.append(n)
        return ida + vuelta, mejor, exp


ESTRATEGIAS = {"bfs": BFS, "dijkstra": Dijkstra, "astar": AEstrella, "bidireccional": Bidireccional}
