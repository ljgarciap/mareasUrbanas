"""Modelo del mapa: grafo dirigido con tiempos de viaje que varían con el tráfico."""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field


@dataclass
class Arista:
    origen: int
    destino: int
    longitud_m: float          # distancia física
    velocidad_kmh: float       # velocidad libre de tráfico
    congestion: float = 1.0    # factor >= 1.0 (1.0 = vía libre)

    @property
    def tiempo_s(self) -> float:
        """Tiempo de viaje actual en segundos."""
        return (self.longitud_m / (self.velocidad_kmh / 3.6)) * self.congestion


@dataclass
class Grafo:
    coords: dict[int, tuple[float, float]] = field(default_factory=dict)  # metros
    adyacencia: dict[int, list[Arista]] = field(default_factory=dict)
    version_trafico: int = 0       # se incrementa con cada cambio de tráfico
    vel_max_kmh: float = 60.0      # cota para la heurística admisible de A*
    _inv: dict | None = None
    _inv_aristas: int = -1

    def agregar_nodo(self, nid: int, x: float, y: float) -> None:
        self.coords[nid] = (x, y)
        self.adyacencia.setdefault(nid, [])

    def agregar_via(self, a: int, b: int, vel_kmh: float) -> None:
        """Vía de doble sentido (dos aristas dirigidas)."""
        d = math.dist(self.coords[a], self.coords[b])
        self.adyacencia[a].append(Arista(a, b, d, vel_kmh))
        self.adyacencia[b].append(Arista(b, a, d, vel_kmh))

    def vecinos(self, nid: int) -> list[Arista]:
        return self.adyacencia[nid]

    def arista(self, a: int, b: int) -> Arista:
        for e in self.adyacencia[a]:
            if e.destino == b:
                return e
        raise KeyError((a, b))

    @property
    def n_nodos(self) -> int:
        return len(self.coords)

    @property
    def n_aristas(self) -> int:
        return sum(len(v) for v in self.adyacencia.values())

    def inversa(self) -> "dict[int, list[Arista]]":
        """Adyacencia invertida (para la búsqueda bidireccional). Se calcula una vez:
        la topología es estática y las aristas son los mismos objetos, así que la
        congestión actualizada se refleja sola."""
        if self._inv is None or self._inv_aristas != self.n_aristas:
            inv: dict[int, list[Arista]] = {n: [] for n in self.coords}
            for lista in self.adyacencia.values():
                for e in lista:
                    inv[e.destino].append(e)
            self._inv, self._inv_aristas = inv, self.n_aristas
        return self._inv


def generar_ciudad(filas: int, cols: int, bloque_m: float = 100.0, seed: int = 7) -> Grafo:
    """Ciudad sintética: malla ortogonal con avenidas rápidas cada 8 cuadras
    y algunas diagonales. Es una red simulada, no datos reales de OpenStreetMap."""
    rnd = random.Random(seed)
    g = Grafo()
    nid = lambda r, c: r * cols + c
    for r in range(filas):
        for c in range(cols):
            jx, jy = rnd.uniform(-8, 8), rnd.uniform(-8, 8)
            g.agregar_nodo(nid(r, c), c * bloque_m + jx, r * bloque_m + jy)
    for r in range(filas):
        for c in range(cols):
            avenida_h = r % 8 == 0
            avenida_v = c % 8 == 0
            if c + 1 < cols:
                g.agregar_via(nid(r, c), nid(r, c + 1), 60.0 if avenida_h else 30.0)
            if r + 1 < filas:
                g.agregar_via(nid(r, c), nid(r + 1, c), 60.0 if avenida_v else 30.0)
            if r + 1 < filas and c + 1 < cols and rnd.random() < 0.04:
                g.agregar_via(nid(r, c), nid(r + 1, c + 1), 40.0)
    return g
