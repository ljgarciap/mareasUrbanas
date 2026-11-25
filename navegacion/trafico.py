"""Patrón Observer: el sensor de tráfico notifica incidentes a la caché y a las sesiones activas."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .grafo import Grafo


@dataclass(frozen=True)
class EventoTrafico:
    a: int
    b: int
    factor_previo: float
    factor_nuevo: float


class Observador(ABC):
    @abstractmethod
    def actualizar(self, evento: EventoTrafico) -> None: ...


class SensorTrafico:
    """Sujeto observable. Modifica la congestión del grafo y notifica."""

    def __init__(self, grafo: Grafo):
        self.grafo = grafo
        self._observadores: list[Observador] = []

    def suscribir(self, o: Observador) -> None:
        self._observadores.append(o)

    def desuscribir(self, o: Observador) -> None:
        if o in self._observadores:
            self._observadores.remove(o)

    def reportar(self, a: int, b: int, factor: float) -> EventoTrafico:
        """Fija el factor de congestión de la vía a<->b (1.0 = libre)."""
        previo = self.grafo.arista(a, b).congestion
        self.grafo.arista(a, b).congestion = factor
        self.grafo.arista(b, a).congestion = factor
        self.grafo.version_trafico += 1
        ev = EventoTrafico(a, b, previo, factor)
        for o in list(self._observadores):
            o.actualizar(ev)
        return ev
