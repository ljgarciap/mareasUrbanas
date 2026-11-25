"""Contexto del patrón Strategy + fachada del motor (caché, sesiones, comandos)."""
from __future__ import annotations
from typing import Optional

from .cache import CacheRutas
from .estrategias import AEstrella, EstrategiaRuta
from .grafo import Grafo
from .ruta import ResultadoBusqueda, RutaMultiparada, TramoRuta
from .trafico import EventoTrafico, Observador, SensorTrafico


class Navegador:
    def __init__(self, grafo: Grafo, estrategia: Optional[EstrategiaRuta] = None,
                 cache: Optional[CacheRutas] = None):
        self.grafo = grafo
        self.estrategia = estrategia or AEstrella()
        self.cache = cache

    def cambiar_estrategia(self, e: EstrategiaRuta) -> None:
        self.estrategia = e

    def calcular(self, origen: int, destino: int) -> ResultadoBusqueda:
        clave = (origen, destino, self.estrategia.nombre)
        if self.cache is not None:
            hit = self.cache.obtener(clave)
            if hit is not None:
                return hit
        r = self.estrategia.buscar(self.grafo, origen, destino)
        if self.cache is not None and r.encontrado:
            self.cache.guardar(clave, r)
        return r

    def ruta_multiparada(self, paradas: list[int]) -> RutaMultiparada:
        """Composite: una subruta por par de paradas consecutivas."""
        ruta = RutaMultiparada(f"{len(paradas)} paradas")
        for a, b in zip(paradas, paradas[1:]):
            r = self.calcular(a, b)
            if not r.encontrado:
                raise ValueError(f"Sin ruta entre {a} y {b}")
            ruta.agregar(TramoRuta(self.grafo, r.camino))
        return ruta


class SesionNavegacion(Observador):
    """Viaje en curso. Observa el tráfico y recalcula si el tramo restante se ve afectado."""

    def __init__(self, navegador: Navegador, origen: int, destino: int, resultado=None):
        self.nav, self.destino = navegador, destino
        self.actual = origen
        self.camino = (resultado or navegador.calcular(origen, destino)).camino
        self.pos = 0
        self.reroutes = 0
        self.ms_reroute: list[float] = []

    @property
    def restante(self) -> list[int]:
        return self.camino[self.pos:]

    def avanzar(self, pasos: int = 1) -> int:
        self.pos = min(self.pos + pasos, len(self.camino) - 1)
        self.actual = self.camino[self.pos]
        return self.actual

    def actualizar(self, ev: EventoTrafico) -> None:
        par = {(ev.a, ev.b), (ev.b, ev.a)}
        r = self.restante
        if ev.factor_nuevo > ev.factor_previo and any((x, y) in par for x, y in zip(r, r[1:])):
            res = self.nav.estrategia.buscar(self.nav.grafo, self.actual, self.destino)  # sin caché
            self.ms_reroute.append(res.tiempo_calculo_ms)
            self.camino, self.pos = res.camino, 0
            self.reroutes += 1
