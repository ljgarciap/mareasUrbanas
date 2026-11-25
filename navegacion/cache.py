"""Caché LRU de rutas, invalidada selectivamente por eventos de tráfico (Observer)."""
from __future__ import annotations
from collections import OrderedDict

from .ruta import ResultadoBusqueda
from .trafico import EventoTrafico, Observador


class CacheRutas(Observador):
    def __init__(self, capacidad: int = 4096):
        self.capacidad = capacidad
        self._datos: "OrderedDict[tuple, ResultadoBusqueda]" = OrderedDict()
        self.aciertos = 0
        self.fallos = 0
        self.invalidaciones = 0

    def obtener(self, clave: tuple) -> ResultadoBusqueda | None:
        r = self._datos.get(clave)
        if r is None:
            self.fallos += 1
            return None
        self._datos.move_to_end(clave)
        self.aciertos += 1
        return r

    def guardar(self, clave: tuple, r: ResultadoBusqueda) -> None:
        self._datos[clave] = r
        self._datos.move_to_end(clave)
        if len(self._datos) > self.capacidad:
            self._datos.popitem(last=False)

    def actualizar(self, ev: EventoTrafico) -> None:
        """Si la vía empeora, sólo caen las rutas que la usan. Si mejora, cualquier
        ruta guardada podría dejar de ser óptima, así que se vacía la caché."""
        if ev.factor_nuevo < ev.factor_previo:
            self.invalidaciones += len(self._datos)
            self._datos.clear()
            return
        afectadas = [k for k, r in self._datos.items() if self._usa(r.camino, ev)]
        for k in afectadas:
            del self._datos[k]
        self.invalidaciones += len(afectadas)

    @staticmethod
    def _usa(camino: list[int], ev: EventoTrafico) -> bool:
        par = {(ev.a, ev.b), (ev.b, ev.a)}
        return any((x, y) in par for x, y in zip(camino, camino[1:]))

    @property
    def tasa_aciertos(self) -> float:
        t = self.aciertos + self.fallos
        return self.aciertos / t if t else 0.0

    def __len__(self) -> int:
        return len(self._datos)
