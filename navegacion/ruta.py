"""Resultado de rutas: Composite (segmentos y rutas multiparada) e Iterator (instrucciones)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator

from .grafo import Grafo


@dataclass
class ResultadoBusqueda:
    camino: list[int]
    costo_s: float
    nodos_expandidos: int
    tiempo_calculo_ms: float
    estrategia: str

    @property
    def encontrado(self) -> bool:
        return bool(self.camino)


class ComponenteRuta(ABC):
    """Componente del patrón Composite."""

    @abstractmethod
    def distancia_m(self) -> float: ...

    @abstractmethod
    def tiempo_s(self) -> float: ...

    @abstractmethod
    def __iter__(self) -> Iterator[int]: ...


class TramoRuta(ComponenteRuta):
    """Hoja: camino entre dos puntos. Recalcula sus métricas contra el grafo vivo."""

    def __init__(self, grafo: Grafo, camino: list[int]):
        self.grafo, self.camino = grafo, camino

    def _aristas(self):
        for a, b in zip(self.camino, self.camino[1:]):
            yield self.grafo.arista(a, b)

    def distancia_m(self) -> float:
        return sum(e.longitud_m for e in self._aristas())

    def tiempo_s(self) -> float:
        return sum(e.tiempo_s for e in self._aristas())

    def __iter__(self) -> Iterator[int]:
        return iter(self.camino)


class RutaMultiparada(ComponenteRuta):
    """Compuesto: agrupa tramos (o subrutas) y agrega sus métricas."""

    def __init__(self, nombre: str = "ruta"):
        self.nombre = nombre
        self.hijos: list[ComponenteRuta] = []

    def agregar(self, c: ComponenteRuta) -> None:
        self.hijos.append(c)

    def distancia_m(self) -> float:
        return sum(h.distancia_m() for h in self.hijos)

    def tiempo_s(self) -> float:
        return sum(h.tiempo_s() for h in self.hijos)

    def __iter__(self) -> Iterator[int]:
        previo = None
        for h in self.hijos:
            for n in h:
                if n != previo:          # evita duplicar el nodo de unión
                    yield n
                previo = n


class IteradorInstrucciones:
    """Iterator: recorre la ruta y entrega instrucciones de giro paso a paso."""

    def __init__(self, grafo: Grafo, nodos: list[int]):
        self.grafo, self.nodos = grafo, list(nodos)

    def __iter__(self) -> Iterator[str]:
        import math
        n = self.nodos
        if len(n) < 2:
            return
        acum, rumbo_prev = 0.0, None
        for i in range(len(n) - 1):
            (x1, y1), (x2, y2) = self.grafo.coords[n[i]], self.grafo.coords[n[i + 1]]
            rumbo = math.degrees(math.atan2(y2 - y1, x2 - x1))
            acum += self.grafo.arista(n[i], n[i + 1]).longitud_m
            if rumbo_prev is not None:
                giro = (rumbo - rumbo_prev + 180) % 360 - 180
                if abs(giro) > 35:
                    yield f"Siga {acum:.0f} m y gire a la {'izquierda' if giro > 0 else 'derecha'}"
                    acum = 0.0
            rumbo_prev = rumbo
        yield f"Siga {acum:.0f} m y llegará a su destino"
